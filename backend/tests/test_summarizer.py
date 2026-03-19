import json
import pytest
from unittest.mock import MagicMock, patch
from summarizer import summarize_episode, generate_digest_script

SAMPLE_TRANSCRIPT = "Sam Altman discusses AI scaling and the future of compute. " * 50

def _mock_claude(response_text: str):
    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=response_text)]
    mock_client.messages.create.return_value = mock_msg
    return mock_client

def test_summarize_episode_returns_valid_json():
    valid_json = json.dumps({
        "relevance_score": 0.9,
        "key_topics": ["AI scaling"],
        "highlights": ["Compute is key"],
        "summary": "Sam discusses AI."
    })
    mock_client = _mock_claude(valid_json)
    with patch("summarizer.anthropic.Anthropic", return_value=mock_client):
        result = summarize_episode(
            transcript=SAMPLE_TRANSCRIPT,
            interest_description="I care about AI",
            topic_tags=["AI", "tech"]
        )
    assert result["relevance_score"] == 0.9
    assert "key_topics" in result
    assert "summary" in result

def test_summarize_episode_handles_json_in_markdown():
    """Claude sometimes wraps JSON in ```json ... ```"""
    wrapped = '```json\n{"relevance_score": 0.7, "key_topics": [], "highlights": [], "summary": "test"}\n```'
    mock_client = _mock_claude(wrapped)
    with patch("summarizer.anthropic.Anthropic", return_value=mock_client):
        result = summarize_episode(SAMPLE_TRANSCRIPT, "AI interest", [])
    assert result["relevance_score"] == 0.7

def test_generate_digest_script_returns_string():
    mock_client = _mock_claude("Welcome to your digest. Today we cover AI agents...")
    summaries = [
        {"episode_title": "Lex #401", "show_title": "Lex Fridman",
         "summary_data": {"relevance_score": 0.9, "key_topics": ["AI"], "highlights": ["Great insight"], "summary": "AI ep."}}
    ]
    with patch("summarizer.anthropic.Anthropic", return_value=mock_client):
        script = generate_digest_script(summaries, "en", "I love AI", ["AI"])
    assert isinstance(script, str)
    assert len(script) > 0
