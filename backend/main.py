import os
import json
import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import get_db, init_db, SessionLocal, Show, Episode, DigestJob, Digest, UserPreference
from rss import parse_feed, search_itunes, parse_opml
from pipeline import run_pipeline, subscribe_to_job, unsubscribe_from_job
from scheduler import start_scheduler, scheduler

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    try:
        scheduler.shutdown()
    except RuntimeError:
        # Handle scheduler already shut down or event loop closed
        pass

app = FastAPI(title="Podcast Digest", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Shows ─────────────────────────────────────────────────────────────────────

class AddShowRequest(BaseModel):
    rss_url: str

class SearchRequest(BaseModel):
    query: str

@app.post("/shows/search")
def search_shows(req: SearchRequest):
    return search_itunes(req.query)

@app.post("/shows", status_code=201)
def add_show(req: AddShowRequest, db: Session = Depends(get_db)):
    if db.query(Show).filter_by(rss_url=req.rss_url).first():
        raise HTTPException(status_code=409, detail="Show already subscribed")
    try:
        show_data, episodes = parse_feed(req.rss_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    show = Show(rss_url=req.rss_url, **show_data)
    db.add(show)
    db.flush()
    for ep in episodes:
        if db.query(Episode).filter_by(guid=ep["guid"]).first():
            continue
        db.add(Episode(show_id=show.id, **ep))
    db.commit()
    db.refresh(show)
    return _show_to_dict(show)

@app.post("/shows/import-opml", status_code=200)
async def import_opml(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    urls = parse_opml(content)
    results = {"imported": [], "failed": [], "skipped": []}
    for url in urls:
        if db.query(Show).filter_by(rss_url=url).first():
            results["skipped"].append(url)
            continue
        try:
            show_data, episodes = parse_feed(url)
            show = Show(rss_url=url, **show_data)
            db.add(show)
            db.flush()
            for ep in episodes:
                if not db.query(Episode).filter_by(guid=ep["guid"]).first():
                    db.add(Episode(show_id=show.id, **ep))
            db.commit()
            results["imported"].append(url)
        except Exception as e:
            db.rollback()
            results["failed"].append({"url": url, "error": str(e)})
    return results

@app.get("/shows")
def list_shows(db: Session = Depends(get_db)):
    shows = db.query(Show).all()
    # Count unprocessed episodes per show in one query
    from sqlalchemy import func
    counts = dict(
        db.query(Episode.show_id, func.count(Episode.id))
        .filter(Episode.transcript == None, Episode.summary == None, Episode.transcript_failed == False)
        .group_by(Episode.show_id)
        .all()
    )
    return [_show_to_dict(s, counts.get(s.id, 0)) for s in shows]

@app.delete("/shows/{show_id}", status_code=204)
def delete_show(show_id: int, db: Session = Depends(get_db)):
    show = db.query(Show).filter_by(id=show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    db.delete(show)
    db.commit()

@app.get("/shows/{show_id}/episodes")
def list_episodes(show_id: int, db: Session = Depends(get_db)):
    show = db.query(Show).filter_by(id=show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    return [_episode_to_dict(e) for e in show.episodes]


@app.get("/episodes/{episode_id}/transcript")
def get_episode_transcript(episode_id: int, db: Session = Depends(get_db)):
    ep = db.query(Episode).filter_by(id=episode_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return {"transcript": ep.transcript or ""}

class ReprocessRequest(BaseModel):
    force: bool = False

@app.post("/episodes/{episode_id}/reprocess", status_code=202)
async def reprocess_episode(episode_id: int, req: ReprocessRequest = ReprocessRequest(), db: Session = Depends(get_db)):
    ep = db.query(Episode).filter_by(id=episode_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    # Reset episode state
    ep.transcript = None
    ep.summary = None
    ep.transcript_failed = False
    ep.processed_at = None
    db.commit()
    job = DigestJob(
        status="pending",
        triggered_by="manual",
        episode_ids=json.dumps([episode_id]),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    pipeline_db = SessionLocal()
    asyncio.create_task(run_pipeline(job.id, pipeline_db))
    return {"job_id": job.id}


# ── Preferences ───────────────────────────────────────────────────────────────

class PreferenceUpdate(BaseModel):
    topic_tags: list[str] | None = None
    interest_description: str | None = None
    output_language: str | None = None
    schedule_type: str | None = None
    schedule_day: int | None = None
    schedule_hour: int | None = None

@app.get("/preferences")
def get_preferences(db: Session = Depends(get_db)):
    pref = db.query(UserPreference).filter_by(id=1).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return _pref_to_dict(pref)

@app.put("/preferences")
def update_preferences(req: PreferenceUpdate, db: Session = Depends(get_db)):
    pref = db.query(UserPreference).filter_by(id=1).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not found")
    if req.topic_tags is not None:
        pref.topic_tags = json.dumps(req.topic_tags)
    if req.interest_description is not None:
        pref.interest_description = req.interest_description
    if req.output_language is not None:
        pref.output_language = req.output_language
    if req.schedule_type is not None:
        pref.schedule_type = req.schedule_type
    if req.schedule_day is not None:
        pref.schedule_day = req.schedule_day
    if req.schedule_hour is not None:
        pref.schedule_hour = req.schedule_hour
    db.commit()
    db.refresh(pref)
    # Reload scheduler with new settings
    from scheduler import setup_scheduler
    setup_scheduler(pref)
    return _pref_to_dict(pref)


# ── Digests (stubs) ───────────────────────────────────────────────────────────

@app.get("/digests")
def list_digests(db: Session = Depends(get_db)):
    return [_digest_to_dict(d) for d in db.query(Digest).order_by(Digest.published_at.desc()).all()]

@app.get("/digests/{digest_id}")
def get_digest(digest_id: int, db: Session = Depends(get_db)):
    d = db.query(Digest).filter_by(id=digest_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Digest not found")
    return _digest_to_dict(d)

@app.get("/digests/{digest_id}/audio")
def get_digest_audio(digest_id: int, db: Session = Depends(get_db)):
    d = db.query(Digest).filter_by(id=digest_id).first()
    if not d or not d.audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    audio_storage = os.getenv("AUDIO_STORAGE_PATH", "./digests")
    path = os.path.join(audio_storage, d.audio_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio file missing")
    return FileResponse(path, media_type="audio/mpeg")


class ResynthesizeRequest(BaseModel):
    script: str | None = None

@app.post("/digests/{digest_id}/resynthesize", status_code=202)
async def resynthesize_digest(digest_id: int, req: ResynthesizeRequest = ResynthesizeRequest(), db: Session = Depends(get_db)):
    d = db.query(Digest).filter_by(id=digest_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Digest not found")
    script = req.script or d.script
    job = DigestJob(
        status="pending",
        triggered_by="resynthesize",
        episode_ids=d.episode_ids,
        custom_script=script,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    pipeline_db = SessionLocal()
    asyncio.create_task(run_pipeline(job.id, pipeline_db))
    return {"job_id": job.id}


# ── Digest jobs (stubs — filled in Task 9) ───────────────────────────────────

class TriggerRequest(BaseModel):
    episode_ids: list[int] | None = None

@app.post("/digest/trigger", status_code=202)
async def trigger_digest(req: TriggerRequest = TriggerRequest(), db: Session = Depends(get_db)):
    if req.episode_ids:
        # Use explicitly selected episodes (any status — pipeline skips already-done steps)
        episodes = db.query(Episode).filter(Episode.id.in_(req.episode_ids)).all()
        if not episodes:
            raise HTTPException(status_code=400, detail="No matching episodes found")
    else:
        # Default: all unprocessed episodes
        episodes = db.query(Episode).filter(
            Episode.transcript_failed == False,
            (Episode.transcript == None) | (Episode.summary == None),
        ).all()
        if not episodes:
            raise HTTPException(status_code=400, detail="No unprocessed episodes found")

    job = DigestJob(
        status="pending",
        triggered_by="manual",
        episode_ids=json.dumps([ep.id for ep in episodes]),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Launch pipeline as background task with its own session (closed inside run_pipeline)
    pipeline_db = SessionLocal()
    asyncio.create_task(run_pipeline(job.id, pipeline_db))
    return {"job_id": job.id}

@app.get("/digest/jobs")
def list_jobs(db: Session = Depends(get_db)):
    return [_job_to_dict(j) for j in db.query(DigestJob).order_by(DigestJob.created_at.desc()).all()]

@app.get("/digest/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    j = db.query(DigestJob).filter_by(id=job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_dict(j)


# ── SSE stream ────────────────────────────────────────────────────────────────

@app.get("/digest/jobs/{job_id}/stream")
async def stream_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(DigestJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    queue = subscribe_to_job(job_id)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("step") in ("done", "failed"):
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            unsubscribe_from_job(job_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Private RSS feed (calls feed.py — implemented in Task 8) ─────────────────

@app.get("/feed/{token}")
def get_feed(token: str, db: Session = Depends(get_db)):
    from feed import generate_feed_xml
    from fastapi.responses import Response
    pref = db.query(UserPreference).filter_by(id=1).first()
    if not pref or pref.feed_token != token:
        raise HTTPException(status_code=404, detail="Feed not found")
    digests = db.query(Digest).order_by(Digest.published_at.desc()).all()
    xml_content = generate_feed_xml(digests, os.getenv("BASE_URL", "http://localhost:8000"))
    return Response(content=xml_content, media_type="application/rss+xml")


# ── Serializers ───────────────────────────────────────────────────────────────

def _show_to_dict(show: Show, unprocessed_count: int = 0) -> dict:
    return {
        "id": show.id, "title": show.title, "author": show.author,
        "description": show.description, "rss_url": show.rss_url,
        "artwork_url": show.artwork_url,
        "unprocessed_count": unprocessed_count,
        "last_checked": show.last_checked.isoformat() if show.last_checked else None,
        "created_at": show.created_at.isoformat() if show.created_at else None,
    }

def _episode_to_dict(ep: Episode) -> dict:
    return {
        "id": ep.id, "show_id": ep.show_id, "guid": ep.guid,
        "title": ep.title, "description": ep.description,
        "pub_date": ep.pub_date.isoformat() if ep.pub_date else None,
        "duration_sec": ep.duration_sec, "audio_url": ep.audio_url,
        "has_transcript": ep.transcript is not None,
        "has_summary": ep.summary is not None,
        "transcript_failed": ep.transcript_failed,
        "processed_at": ep.processed_at.isoformat() if ep.processed_at else None,
    }

def _pref_to_dict(pref: UserPreference) -> dict:
    return {
        "topic_tags": json.loads(pref.topic_tags or "[]"),
        "interest_description": pref.interest_description,
        "output_language": pref.output_language,
        "schedule_type": pref.schedule_type,
        "schedule_day": pref.schedule_day,
        "schedule_hour": pref.schedule_hour,
        "feed_token": pref.feed_token,
    }

def _job_to_dict(job: DigestJob) -> dict:
    return {
        "id": job.id, "status": job.status, "triggered_by": job.triggered_by,
        "episode_ids": json.loads(job.episode_ids or "[]"),
        "progress_pct": job.progress_pct, "current_step": job.current_step,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }

def _digest_to_dict(d: Digest) -> dict:
    return {
        "id": d.id, "job_id": d.job_id, "title": d.title,
        "script": d.script, "audio_path": d.audio_path,
        "duration_sec": d.duration_sec,
        "cost_usd": d.cost_usd,
        "episode_ids": json.loads(d.episode_ids or "[]"),
        "published_at": d.published_at.isoformat() if d.published_at else None,
    }
