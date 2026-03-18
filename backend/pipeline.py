import os
import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.orm import Session
from database import SessionLocal, DigestJob, Digest, Episode, UserPreference
from transcriber import download_audio, transcribe_with_retry
from summarizer import summarize_episode, generate_digest_script
from tts import synthesize_script

# In-memory SSE event queues: job_id -> list of asyncio.Queue
_sse_queues: dict[int, list[asyncio.Queue]] = {}

AUDIO_STORAGE = os.getenv("AUDIO_STORAGE_PATH", "./digests")


def _push_event(job_id: int, event: dict):
    for q in _sse_queues.get(job_id, []):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


def subscribe_to_job(job_id: int) -> asyncio.Queue:
    q = asyncio.Queue(maxsize=100)
    _sse_queues.setdefault(job_id, []).append(q)
    return q


def unsubscribe_from_job(job_id: int, q: asyncio.Queue):
    queues = _sse_queues.get(job_id, [])
    if q in queues:
        queues.remove(q)


async def run_pipeline(job_id: int, db: Session):
    """Main pipeline: transcribe → summarize → script → tts → publish.

    Note: caller must pass a dedicated SessionLocal() — this function closes it on exit.
    """
    try:
        return await _run_pipeline_inner(job_id, db)
    finally:
        db.close()


async def _run_pipeline_inner(job_id: int, db: Session):
    job = db.query(DigestJob).filter_by(id=job_id).first()
    if not job:
        return

    pref = db.query(UserPreference).filter_by(id=1).first()
    topic_tags = json.loads(pref.topic_tags or "[]")
    episode_ids = json.loads(job.episode_ids or "[]")
    episodes = db.query(Episode).filter(Episode.id.in_(episode_ids)).all()

    def update_job(status=None, step=None, pct=None):
        if status:
            job.status = status
        if step:
            job.current_step = step
        if pct is not None:
            job.progress_pct = pct
        db.commit()

    update_job(status="running", step="transcribing", pct=0)

    summaries = []
    total = len(episodes)

    for i, episode in enumerate(episodes):
        try:
            # Transcription
            if not episode.transcript and not episode.transcript_failed:
                _push_event(job_id, {"step": "transcribing", "episode": episode.title,
                                     "pct": int(i / total * 40)})
                if episode.audio_url:
                    local_path = download_audio(episode.audio_url, AUDIO_STORAGE)
                    episode.audio_local_path = local_path
                    db.commit()
                    try:
                        transcript = transcribe_with_retry(local_path)
                        episode.transcript = transcript
                        try:
                            os.remove(local_path)
                        except OSError:
                            pass
                        episode.audio_local_path = None
                    except Exception as e:
                        episode.transcript_failed = True
                        db.commit()
                        _push_event(job_id, {"step": "error", "message": f"Transcription failed: {episode.title}", "pct": -1})
                        # Use RSS description as fallback
                        episode.transcript = episode.description or ""
                else:
                    episode.transcript = episode.description or ""
                db.commit()

            # Summarization
            if episode.transcript and not episode.summary:
                _push_event(job_id, {"step": "summarizing", "episode": episode.title,
                                     "pct": int(40 + i / total * 20)})
                summary_data = summarize_episode(
                    transcript=episode.transcript,
                    interest_description=pref.interest_description or "",
                    topic_tags=topic_tags,
                )
                episode.summary = json.dumps(summary_data)
                episode.processed_at = datetime.utcnow()
                db.commit()

            if episode.summary:
                from database import Show
                show = db.query(Show).filter_by(id=episode.show_id).first()
                summaries.append({
                    "episode_title": episode.title,
                    "show_title": show.title if show else "Unknown",
                    "summary_data": json.loads(episode.summary),
                })

        except Exception as e:
            _push_event(job_id, {"step": "error", "message": str(e), "pct": -1})

    if not summaries:
        update_job(status="failed", step=None, pct=100)
        job.error_message = "No episodes could be processed"
        db.commit()
        return

    # Generate digest script
    update_job(step="generating_script", pct=65)
    _push_event(job_id, {"step": "generating_script", "pct": 65})
    script = generate_digest_script(
        summaries=summaries,
        output_language=pref.output_language or "en",
        interest_description=pref.interest_description or "",
        topic_tags=topic_tags,
    )

    # TTS synthesis
    update_job(step="tts", pct=80)
    _push_event(job_id, {"step": "tts", "pct": 80})

    # Placeholder ID for filename; we'll rename after insert
    tmp_audio_path = os.path.join(AUDIO_STORAGE, f"job_{job_id}.mp3")
    os.makedirs(AUDIO_STORAGE, exist_ok=True)
    audio_path = synthesize_script(script, tmp_audio_path)

    # Get audio duration
    duration_sec = None
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(audio_path)
        duration_sec = int(len(audio) / 1000)
    except Exception:
        pass

    # Count existing digests for title numbering
    digest_count = db.query(Digest).count() + 1
    digest = Digest(
        job_id=job_id,
        title=f"Your Podcast Digest #{digest_count}",
        script=script,
        audio_path=os.path.basename(audio_path),
        duration_sec=duration_sec,
        episode_ids=job.episode_ids,
    )
    db.add(digest)
    db.flush()

    # Rename file to use digest ID
    final_path = os.path.join(AUDIO_STORAGE, f"{digest.id}.mp3")
    try:
        os.rename(audio_path, final_path)
        digest.audio_path = f"{digest.id}.mp3"
    except OSError:
        pass

    update_job(status="done", pct=100)
    db.commit()

    _push_event(job_id, {"step": "done", "digest_id": digest.id, "pct": 100})
