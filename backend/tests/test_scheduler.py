import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Show, Episode, UserPreference, DigestJob


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add(UserPreference(id=1, topic_tags='[]', interest_description="",
                         output_language="en", schedule_type="weekly",
                         schedule_day=0, schedule_hour=8, feed_token="tok"))
    show = Show(title="Lex", rss_url="https://lex.com/feed.xml")
    s.add(show)
    s.commit()
    yield s
    s.close()


@pytest.mark.asyncio
async def test_poll_rss_feeds_adds_new_episodes():
    from scheduler import poll_rss_feeds
    mock_eps = [{"guid": "new-ep-1", "title": "New EP", "description": "",
                 "pub_date": None, "duration_sec": 0, "audio_url": "https://x.com/1.mp3"}]
    with patch("scheduler.SessionLocal") as mock_sl, \
         patch("scheduler.parse_feed", return_value=({"title":"Lex","author":"","description":"","artwork_url":""}, mock_eps)):
        mock_db = MagicMock()
        mock_sl.return_value = mock_db
        mock_db.query.return_value.all.return_value = [MagicMock(rss_url="https://lex.com/feed.xml")]
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        await poll_rss_feeds()
    mock_db.add.assert_called()
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_scheduled_digest_skips_when_no_episodes():
    from scheduler import scheduled_digest
    with patch("scheduler.SessionLocal") as mock_sl:
        mock_db = MagicMock()
        mock_sl.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        await scheduled_digest()
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_scheduled_digest_creates_job_when_episodes_exist():
    from scheduler import scheduled_digest
    mock_ep = MagicMock()
    mock_ep.id = 1
    with patch("scheduler.SessionLocal") as mock_sl, \
         patch("scheduler.asyncio.create_task"):
        mock_db = MagicMock()
        mock_sl.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_ep]
        await scheduled_digest()
    mock_db.add.assert_called_once()
    added = mock_db.add.call_args[0][0]
    assert isinstance(added, DigestJob)
    assert added.triggered_by == "schedule"
