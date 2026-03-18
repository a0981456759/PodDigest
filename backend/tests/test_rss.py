import pytest
from unittest.mock import patch, MagicMock
from rss import parse_feed, search_itunes, parse_opml

MOCK_FEED = {
    "feed": {
        "title": "Test Show",
        "author": "Test Author",
        "subtitle": "A test podcast",
        "image": {"href": "https://example.com/art.jpg"},
    },
    "entries": [
        {
            "id": "guid-001",
            "title": "Episode 1",
            "summary": "Great episode",
            "published_parsed": (2026, 3, 1, 8, 0, 0, 0, 0, 0),
            "itunes_duration": "3600",
            "enclosures": [{"href": "https://example.com/ep1.mp3", "type": "audio/mpeg"}],
        }
    ],
}

def test_parse_feed_returns_show_and_episodes():
    with patch("rss.feedparser.parse", return_value=MOCK_FEED):
        show_data, episodes = parse_feed("https://example.com/feed.xml")
    assert show_data["title"] == "Test Show"
    assert len(episodes) == 1
    assert episodes[0]["guid"] == "guid-001"
    assert episodes[0]["audio_url"] == "https://example.com/ep1.mp3"

def test_parse_feed_raises_on_empty():
    with patch("rss.feedparser.parse", return_value={"feed": {}, "entries": []}):
        with pytest.raises(ValueError, match="Invalid or empty RSS feed"):
            parse_feed("https://bad.com/feed.xml")

def test_search_itunes_returns_results():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"collectionName": "My Podcast", "feedUrl": "https://x.com/feed.xml",
             "artistName": "Author", "artworkUrl600": "https://x.com/art.jpg"}
        ]
    }
    mock_response.raise_for_status = MagicMock()
    with patch("rss.httpx.get", return_value=mock_response):
        results = search_itunes("my podcast")
    assert len(results) == 1
    assert results[0]["title"] == "My Podcast"

def test_parse_opml_extracts_rss_urls():
    opml_xml = b"""<?xml version="1.0"?>
    <opml version="2.0">
      <body>
        <outline text="Lex" type="rss" xmlUrl="https://lex.com/feed.xml"/>
        <outline text="a16z" type="rss" xmlUrl="https://a16z.com/feed.xml"/>
      </body>
    </opml>"""
    urls = parse_opml(opml_xml)
    assert urls == ["https://lex.com/feed.xml", "https://a16z.com/feed.xml"]
