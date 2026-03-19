import os
import json
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy.orm import Session
from database import SessionLocal, DigestJob, Digest, Episode, UserPreference
from transcriber import download_audio, transcribe_with_retry
from summarizer import summarize_episode, generate_digest_script
from tts import synthesize_script

_sse_queues: dict[int, list[asyncio.Queue]] = {}
AUDIO_STORAGE = os.getenv("AUDIO_STORAGE_PATH", "./digests")

# Cost estimates for non-Claude services
_WHISPER_COST_PER_MIN = 0.006   # $ per minute of audio
_TTS_COST_PER_1K_CHARS = 0.015  # $ per 1000 chars (tts-1)


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
    try:
        return await _run_pipeline_inner(job_id, db)
    except Exception as e:
        try:
            job = db.query(DigestJob).filter_by(id=job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                db.commit()
            _push_event(job_id, {"step": "failed", "message": str(e), "pct": 100})
        except Exception:
            pass
    finally:
        db.close()


async def _run_pipeline_inner(job_id: int, db: Session):
    job = db.query(DigestJob).filter_by(id=job_id).first()
    if not job:
        return

    # Resynthesize job: skip transcribe/summarize, go straight to TTS
    if job.triggered_by == "resynthesize" and job.custom_script:
        await _run_resynthesize(job, db)
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
    total_cost = 0.0

    for i, episode in enumerate(episodes):
        try:
            base_pct = int(i / total * 60)

            # Download + Transcription
            if not episode.transcript and not episode.transcript_failed:
                if episode.audio_url:
                    # Download with progress
                    def make_progress(ep_title, ep_idx):
                        def progress_cb(downloaded, total_bytes):
                            if total_bytes > 0:
                                pct = int(downloaded / total_bytes * 100)
                                mb = downloaded / 1024 / 1024
                                total_mb = total_bytes / 1024 / 1024
                                _push_event(job_id, {
                                    "step": "downloading",
                                    "episode": ep_title,
                                    "message": f"{mb:.1f}/{total_mb:.1f} MB",
                                    "pct": base_pct
                                })
                        return progress_cb

                    _push_event(job_id, {"step": "downloading", "episode": episode.title, "pct": base_pct})
                    loop = asyncio.get_event_loop()
                    local_path = await loop.run_in_executor(
                        None,
                        lambda: download_audio(episode.audio_url, AUDIO_STORAGE, make_progress(episode.title, i))
                    )
                    episode.audio_local_path = local_path
                    db.commit()

                    # Transcription with retry
                    _push_event(job_id, {"step": "transcribing", "episode": episode.title, "pct": base_pct + 5})
                    try:
                        transcript = await loop.run_in_executor(None, lambda: transcribe_with_retry(local_path))
                        episode.transcript = transcript
                        # Estimate Whisper cost: ~150 words/min, avg 5 chars/word
                        estimated_mins = len(transcript) / (150 * 5)
                        total_cost += estimated_mins * _WHISPER_COST_PER_MIN
                        try:
                            os.remove(local_path)
                        except OSError:
                            pass
                        episode.audio_local_path = None
                    except Exception as e:
                        episode.transcript_failed = True
                        db.commit()
                        _push_event(job_id, {"step": "error", "episode": episode.title,
                                             "message": f"Transcription failed: {e}", "pct": base_pct})
                        episode.transcript = episode.description or ""
                else:
                    episode.transcript = episode.description or ""
                db.commit()

            # Summarization
            if episode.transcript and not episode.summary:
                _push_event(job_id, {"step": "summarizing", "episode": episode.title,
                                     "pct": base_pct + 10})
                loop = asyncio.get_event_loop()
                summary_data, cost = await loop.run_in_executor(
                    None,
                    lambda: summarize_episode(
                        transcript=episode.transcript,
                        interest_description=pref.interest_description or "",
                        topic_tags=topic_tags,
                    )
                )
                total_cost += cost
                episode.summary = json.dumps(summary_data)
                episode.processed_at = datetime.now(timezone.utc)
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
            _push_event(job_id, {"step": "error", "episode": episode.title,
                                 "message": str(e), "pct": base_pct})

    if not summaries:
        update_job(status="failed", step=None, pct=100)
        job.error_message = "No episodes could be processed"
        db.commit()
        _push_event(job_id, {"step": "failed", "message": "No episodes could be processed", "pct": 100})
        return

    # Generate digest script
    update_job(step="generating_script", pct=65)
    _push_event(job_id, {"step": "generating_script", "pct": 65})
    loop = asyncio.get_event_loop()
    script, script_cost = await loop.run_in_executor(
        None,
        lambda: generate_digest_script(
            summaries=summaries,
            output_language=pref.output_language or "en",
            interest_description=pref.interest_description or "",
            topic_tags=topic_tags,
        )
    )
    total_cost += script_cost

    await _finish_with_tts(job, db, script, total_cost)


async def _run_resynthesize(job: DigestJob, db: Session):
    """Run TTS only, using job.custom_script."""
    def update_job(status=None, step=None, pct=None):
        if status:
            job.status = status
        if step:
            job.current_step = step
        if pct is not None:
            job.progress_pct = pct
        db.commit()

    update_job(status="running", step="tts", pct=80)
    _push_event(job.id, {"step": "tts", "pct": 80})
    await _finish_with_tts(job, db, job.custom_script, 0.0)


async def _finish_with_tts(job: DigestJob, db: Session, script: str, accumulated_cost: float):
    """Run TTS synthesis and save digest."""
    def update_job(status=None, step=None, pct=None):
        if status:
            job.status = status
        if step:
            job.current_step = step
        if pct is not None:
            job.progress_pct = pct
        db.commit()

    update_job(step="tts", pct=80)
    _push_event(job.id, {"step": "tts", "pct": 80})

    tmp_audio_path = os.path.join(AUDIO_STORAGE, f"job_{job.id}.mp3")
    os.makedirs(AUDIO_STORAGE, exist_ok=True)
    loop = asyncio.get_event_loop()
    audio_path = await loop.run_in_executor(None, lambda: synthesize_script(script, tmp_audio_path))

    tts_cost = len(script) / 1000 * 0.015
    total_cost = accumulated_cost + tts_cost

    duration_sec = None
    try:
        size_bytes = os.path.getsize(audio_path)
        duration_sec = int(size_bytes / (128 * 1024 / 8))  # estimate from 128kbps
    except Exception:
        pass

    digest_count = db.query(Digest).count() + 1
    digest = Digest(
        job_id=job.id,
        title=f"Your Podcast Digest #{digest_count}",
        script=script,
        audio_path=os.path.basename(audio_path),
        duration_sec=duration_sec,
        cost_usd=round(total_cost, 4),
        episode_ids=job.episode_ids,
    )
    db.add(digest)
    db.flush()

    final_path = os.path.join(AUDIO_STORAGE, f"{digest.id}.mp3")
    try:
        os.rename(audio_path, final_path)
        digest.audio_path = f"{digest.id}.mp3"
    except OSError:
        pass

    update_job(status="done", pct=100)
    db.commit()
    _push_event(job.id, {"step": "done", "digest_id": digest.id, "pct": 100,
                          "cost_usd": round(total_cost, 4)})
