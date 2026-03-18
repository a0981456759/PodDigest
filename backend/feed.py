import os
from xml.etree import ElementTree as ET
from email.utils import formatdate
from datetime import datetime


def _seconds_to_hms(seconds: int) -> str:
    if not seconds:
        return "00:00:00"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _get_file_size(audio_storage: str, audio_path: str) -> int:
    full_path = os.path.join(audio_storage, audio_path)
    try:
        return os.path.getsize(full_path)
    except OSError:
        return 0


def generate_feed_xml(digests: list, base_url: str, audio_storage: str = "./digests") -> str:
    """Generate RSS 2.0 + iTunes namespace XML for private podcast feed."""
    ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

    root = ET.Element("rss", {
        "version": "2.0",
        "xmlns:itunes": ITUNES_NS,
    })
    channel = ET.SubElement(root, "channel")

    ET.SubElement(channel, "title").text = "Your PodDigest Feed"
    ET.SubElement(channel, "link").text = base_url
    ET.SubElement(channel, "description").text = "Personalized podcast digest"
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, f"{{{ITUNES_NS}}}image", {"href": f"{base_url}/static/cover.png"})
    ET.SubElement(channel, f"{{{ITUNES_NS}}}category", {"text": "Technology"})
    ET.SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "false"

    for digest in digests:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = digest.title
        description = (digest.script or "")[:500] + ("..." if len(digest.script or "") > 500 else "")
        ET.SubElement(item, "description").text = description
        pub_dt = digest.published_at or datetime.utcnow()
        ET.SubElement(item, "pubDate").text = formatdate(pub_dt.timestamp(), usegmt=True)
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = str(digest.id)

        audio_url = f"{base_url}/digests/{digest.id}/audio"
        file_size = _get_file_size(audio_storage, digest.audio_path or "") if digest.audio_path else 0
        ET.SubElement(item, "enclosure", {
            "url": audio_url,
            "length": str(file_size),
            "type": "audio/mpeg",
        })
        ET.SubElement(item, f"{{{ITUNES_NS}}}duration").text = _seconds_to_hms(digest.duration_sec)

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
