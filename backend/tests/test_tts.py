import os
import pytest
from unittest.mock import patch, MagicMock
from tts import synthesize_script

def test_synthesize_script_single_chunk(tmp_path):
    short_script = "Hello world. This is a test."
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = b"fake-mp3-data"
    mock_client.audio.speech.create.return_value = mock_response

    with patch("tts.openai.OpenAI", return_value=mock_client), \
         patch("tts._concat_mp3_chunks", return_value=str(tmp_path / "out.mp3")) as mock_concat:
        result = synthesize_script(short_script, str(tmp_path / "out.mp3"))

    mock_client.audio.speech.create.assert_called_once()
    assert result == str(tmp_path / "out.mp3")

def test_synthesize_script_multiple_chunks(tmp_path):
    long_script = "This is a sentence. " * 210  # > 4000 chars
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = b"fake-mp3-data"
    mock_client.audio.speech.create.return_value = mock_response

    with patch("tts.openai.OpenAI", return_value=mock_client), \
         patch("tts._concat_mp3_chunks", return_value=str(tmp_path / "out.mp3")):
        result = synthesize_script(long_script, str(tmp_path / "out.mp3"))

    assert mock_client.audio.speech.create.call_count >= 2
