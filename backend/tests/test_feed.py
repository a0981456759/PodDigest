from feed import generate_feed_xml
from xml.etree import ElementTree as ET
from datetime import datetime

def _make_digest(id, title, script, audio_path, duration_sec, published_at):
    from unittest.mock import MagicMock
    d = MagicMock()
    d.id = id; d.title = title; d.script = script
    d.audio_path = audio_path; d.duration_sec = duration_sec
    d.published_at = published_at
    return d

def test_feed_is_valid_rss():
    digests = [_make_digest(1, "Digest #1", "Hello world script", "1.mp3", 600, datetime(2026,3,17))]
    xml = generate_feed_xml(digests, "http://localhost:8000")
    root = ET.fromstring(xml)
    assert root.tag == "rss"
    assert root.get("version") == "2.0"

def test_feed_has_itunes_namespace():
    digests = []
    xml = generate_feed_xml(digests, "http://localhost:8000")
    assert "itunes" in xml

def test_feed_item_has_enclosure():
    digests = [_make_digest(1, "D1", "Script", "1.mp3", 300, datetime(2026,3,17))]
    xml = generate_feed_xml(digests, "http://localhost:8000")
    root = ET.fromstring(xml)
    channel = root.find("channel")
    item = channel.find("item")
    enclosure = item.find("enclosure")
    assert enclosure is not None
    assert "audio/mpeg" in enclosure.get("type", "")
    assert "http://localhost:8000/digests/1/audio" in enclosure.get("url", "")

def test_feed_duration_format():
    digests = [_make_digest(1, "D1", "Script", "1.mp3", 3661, datetime(2026,3,17))]
    xml = generate_feed_xml(digests, "http://localhost:8000")
    assert "01:01:01" in xml
