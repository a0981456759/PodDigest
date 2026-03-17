from database import Show, Episode, DigestJob, Digest, UserPreference
from datetime import datetime

def test_create_show(db):
    show = Show(title="Lex Fridman", rss_url="https://example.com/feed.xml")
    db.add(show)
    db.commit()
    assert db.query(Show).count() == 1
    assert db.query(Show).first().title == "Lex Fridman"

def test_episode_guid_unique(db):
    show = Show(title="Test", rss_url="https://a.com/feed.xml")
    db.add(show)
    db.commit()
    ep1 = Episode(show_id=show.id, guid="abc123", title="EP1", audio_url="https://a.com/1.mp3")
    ep2 = Episode(show_id=show.id, guid="abc123", title="EP2", audio_url="https://a.com/2.mp3")
    db.add(ep1)
    db.commit()
    db.add(ep2)
    import pytest
    with pytest.raises(Exception):
        db.commit()

def test_user_preference_defaults(db):
    pref = UserPreference()
    db.add(pref)
    db.commit()
    result = db.query(UserPreference).first()
    assert result.output_language == "en"
    assert result.schedule_hour == 8
