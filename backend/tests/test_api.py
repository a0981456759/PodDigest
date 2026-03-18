import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch
from database import Base, get_db, UserPreference
from main import app

@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        if not db.query(UserPreference).first():
            db.add(UserPreference(id=1))
            db.commit()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_add_show_by_rss_url(client):
    mock_show = {"title": "Lex", "author": "Lex Fridman", "description": "", "artwork_url": ""}
    mock_eps = [{"guid": "ep1", "title": "EP1", "description": "", "pub_date": None,
                 "duration_sec": 3600, "audio_url": "https://example.com/ep1.mp3"}]
    with patch("main.parse_feed", return_value=(mock_show, mock_eps)):
        r = client.post("/shows", json={"rss_url": "https://example.com/feed.xml"})
    assert r.status_code == 201
    assert r.json()["title"] == "Lex"

def test_add_show_duplicate_returns_409(client):
    mock_show = {"title": "Lex", "author": "", "description": "", "artwork_url": ""}
    with patch("main.parse_feed", return_value=(mock_show, [])):
        client.post("/shows", json={"rss_url": "https://example.com/feed.xml"})
        r = client.post("/shows", json={"rss_url": "https://example.com/feed.xml"})
    assert r.status_code == 409

def test_list_shows(client):
    mock_show = {"title": "Show1", "author": "", "description": "", "artwork_url": ""}
    with patch("main.parse_feed", return_value=(mock_show, [])):
        client.post("/shows", json={"rss_url": "https://example.com/feed.xml"})
    r = client.get("/shows")
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_delete_show(client):
    mock_show = {"title": "Show1", "author": "", "description": "", "artwork_url": ""}
    with patch("main.parse_feed", return_value=(mock_show, [])):
        resp = client.post("/shows", json={"rss_url": "https://example.com/feed.xml"})
    show_id = resp.json()["id"]
    r = client.delete(f"/shows/{show_id}")
    assert r.status_code == 204
    assert client.get("/shows").json() == []

def test_search_shows(client):
    mock_results = [{"title": "Lex", "author": "Lex", "rss_url": "https://x.com", "artwork_url": ""}]
    with patch("main.search_itunes", return_value=mock_results):
        r = client.post("/shows/search", json={"query": "lex fridman"})
    assert r.status_code == 200
    assert r.json()[0]["title"] == "Lex"

def test_get_preferences(client):
    r = client.get("/preferences")
    assert r.status_code == 200
    data = r.json()
    assert "topic_tags" in data
    assert "feed_token" in data

def test_update_preferences(client):
    r = client.put("/preferences", json={"topic_tags": ["AI", "tech"], "output_language": "zh"})
    assert r.status_code == 200
    data = r.json()
    assert data["topic_tags"] == ["AI", "tech"]
    assert data["output_language"] == "zh"
