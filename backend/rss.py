import feedparser
import httpx
from xml.etree import ElementTree as ET
from datetime import datetime


def parse_feed(rss_url: str) -> tuple[dict, list[dict]]:
    """Parse RSS feed. Returns (show_data, episodes_list)."""
    parsed = feedparser.parse(rss_url)
    feed = parsed.get("feed", {})
    if not feed.get("title") and not parsed.get("entries"):
        raise ValueError("Invalid or empty RSS feed")

    show_data = {
        "title": feed.get("title", "Unknown Show"),
        "author": feed.get("author", feed.get("itunes_author", "")),
        "description": feed.get("subtitle", feed.get("summary", "")),
        "artwork_url": (feed.get("image") or {}).get("href", ""),
    }

    episodes = []
    for entry in parsed.get("entries", []):
        audio_url = ""
        for enc in entry.get("enclosures", []):
            if enc.get("type", "").startswith("audio"):
                audio_url = enc.get("href", "")
                break

        pub_date = None
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            pub_date = datetime(*published_parsed[:6])

        duration_sec = 0
        raw_dur = entry.get("itunes_duration", "0")
        parts = str(raw_dur).split(":")
        try:
            if len(parts) == 3:
                duration_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                duration_sec = int(parts[0]) * 60 + int(parts[1])
            else:
                duration_sec = int(parts[0])
        except (ValueError, IndexError):
            duration_sec = 0

        episodes.append({
            "guid": entry.get("id", entry.get("link", "")),
            "title": entry.get("title", ""),
            "description": entry.get("summary", ""),
            "pub_date": pub_date,
            "duration_sec": duration_sec,
            "audio_url": audio_url,
        })

    return show_data, episodes


def search_itunes(query: str, limit: int = 10) -> list[dict]:
    """Search iTunes Search API for podcasts."""
    response = httpx.get(
        "https://itunes.apple.com/search",
        params={"term": query, "entity": "podcast", "limit": limit},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    results = []
    for item in data.get("results", []):
        if not item.get("feedUrl"):
            continue
        results.append({
            "title": item.get("collectionName", ""),
            "author": item.get("artistName", ""),
            "rss_url": item.get("feedUrl", ""),
            "artwork_url": item.get("artworkUrl600", ""),
        })
    return results


def parse_opml(content: bytes) -> list[str]:
    """Extract RSS URLs from OPML file content."""
    root = ET.fromstring(content)
    urls = []
    for outline in root.iter("outline"):
        xml_url = outline.get("xmlUrl") or outline.get("url")
        if xml_url and outline.get("type") in ("rss", "podcast", None):
            if xml_url not in urls:
                urls.append(xml_url)
    return urls
