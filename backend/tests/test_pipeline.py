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

def test_run_pipeline_creates_digest(db):
    from pipeline import run_pipeline

    with patch("pipeline.download_audio", return_value="/tmp/ep1.mp3"), \
         patch("pipeline.transcribe_with_retry", return_value="transcript text"), \
         patch("pipeline.summarize_episode", return_value=({
             "relevance_score": 0.9, "key_topics": ["AI"],
             "highlights": ["Great"], "summary": "Good ep"}, 0.0)), \
         patch("pipeline.generate_digest_script", return_value=("Welcome to your digest...", 0.0)), \
         patch("pipeline.synthesize_script", return_value="/digests/1.mp3"), \
         patch("pipeline.os.path.getsize", return_value=1000), \
         patch("pipeline.os.remove"):
        import asyncio
        asyncio.run(run_pipeline(job_id=1, db=db))

    digest = db.query(Digest).first()
    assert digest is not None
    assert "digest" in digest.title.lower() or len(digest.title) > 0
    job = db.query(DigestJob).filter_by(id=1).first()
    assert job.status == "done"
