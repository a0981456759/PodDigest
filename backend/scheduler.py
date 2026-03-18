import os
import json
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import SessionLocal, Show, Episode, UserPreference, DigestJob
from rss import parse_feed
from pipeline import run_pipeline

scheduler = AsyncIOScheduler()


async def poll_rss_feeds():
    """Check all subscribed shows for new episodes."""
    db = SessionLocal()
    try:
        shows = db.query(Show).all()
        for show in shows:
            try:
                _, episodes = parse_feed(show.rss_url)
                new_count = 0
                for ep in episodes:
                    if not db.query(Episode).filter_by(guid=ep["guid"]).first():
                        db.add(Episode(show_id=show.id, **ep))
                        new_count += 1
                show.last_checked = datetime.utcnow()
                db.commit()
            except Exception as e:
                print(f"[scheduler] Failed to poll {show.rss_url}: {e}")
    finally:
        db.close()


async def scheduled_digest():
    """Trigger a digest job if there are unprocessed episodes."""
    db = SessionLocal()
    try:
        unprocessed = db.query(Episode).filter(
            Episode.transcript_failed == False,
            (Episode.transcript == None) | (Episode.summary == None),
        ).all()
        if not unprocessed:
            print("[scheduler] No new episodes to digest")
            return
        job = DigestJob(
            status="pending",
            triggered_by="schedule",
            episode_ids=json.dumps([ep.id for ep in unprocessed]),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        asyncio.create_task(run_pipeline(job.id, SessionLocal()))
    finally:
        db.close()


def setup_scheduler(pref):
    """Configure scheduler based on UserPreference."""
    try:
        if not scheduler.running:
            return  # Scheduler not running (e.g., in tests), skip setup

        scheduler.remove_all_jobs()

        # Always poll RSS every hour
        scheduler.add_job(poll_rss_feeds, "interval", hours=1, id="rss_poll")

        if pref.schedule_type == "new_episode":
            # Poll every 30 min and trigger digest on new episodes
            scheduler.add_job(scheduled_digest, "interval", minutes=30, id="digest_trigger")
        elif pref.schedule_type == "weekly":
            scheduler.add_job(
                scheduled_digest,
                CronTrigger(day_of_week=pref.schedule_day, hour=pref.schedule_hour),
                id="digest_trigger",
            )
        elif pref.schedule_type == "biweekly":
            # Every 2 weeks on the configured day/hour using CronTrigger week='*/2'
            scheduler.add_job(
                scheduled_digest,
                CronTrigger(week="*/2", day_of_week=pref.schedule_day, hour=pref.schedule_hour),
                id="digest_trigger",
            )
    except RuntimeError as e:
        # Handle event loop issues in testing or shutdown scenarios
        if "event loop is closed" not in str(e).lower():
            raise
        # Silently ignore if event loop is closed (e.g., during test cleanup)


def start_scheduler():
    # Check if scheduler is already running (avoid starting twice)
    if scheduler.running:
        return

    db = SessionLocal()
    try:
        pref = db.query(UserPreference).filter_by(id=1).first()
        if pref:
            setup_scheduler(pref)
    finally:
        db.close()

    try:
        scheduler.start()
    except RuntimeError as e:
        # Handle event loop issues in testing environments
        if "event loop is closed" not in str(e).lower():
            raise
        # Silently ignore if event loop is closed (e.g., in tests)
