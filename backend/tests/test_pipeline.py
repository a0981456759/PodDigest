import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Show, Episode, DigestJob, Digest, UserPreference

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add(UserPreference(id=1, topic_tags='["AI"]', interest_description="I love AI",
                         output_language="en", feed_token="tok"))
    show = Show(title="Lex", rss_url="https://lex.com/feed.xml")
    s.add(show)
    s.flush()
    ep = Episode(show_id=show.id, guid="ep1", title="EP1",
                 audio_url="https://lex.com/ep1.mp3", transcript="AI is amazing. " * 100)
    s.add(ep)
    s.flush()
    job = DigestJob(id=1, status="pending", triggered_by="manual",
                    episode_ids=f"[{ep.id}]")
    s.add(job)
    s.commit()
    yield s
    s.close()

def test_run_pipeline_creates_digest(db, tmp_path):
    from pipeline import _run_pipeline_inner

    def fake_synthesize(script, destination):
        from pathlib import Path
        Path(destination).write_bytes(b"offline test audio bytes")
        return destination

    with patch("pipeline.AUDIO_STORAGE", str(tmp_path)), \
         patch("pipeline.download_audio", return_value="/tmp/ep1.mp3"), \
         patch("pipeline.transcribe_with_retry", return_value="transcript text"), \
         patch("pipeline.summarize_episode", return_value=({
             "relevance_score": 0.9, "key_topics": ["AI"],
             "highlights": ["Great"], "summary": "Good ep"}, 0.0)), \
         patch("pipeline.generate_digest_script", return_value=("Welcome to your digest...", 0.0)), \
         patch("pipeline.synthesize_script", side_effect=fake_synthesize):
        import asyncio
        asyncio.run(_run_pipeline_inner(job_id=1, db=db))

    digest = db.query(Digest).first()
    job = db.query(DigestJob).filter_by(id=1).first()
    assert digest is not None, f"Pipeline failed: status={job.status}, error={job.error_message}"
    assert "digest" in digest.title.lower() or len(digest.title) > 0
    job = db.query(DigestJob).filter_by(id=1).first()
    assert job.status == "done"
