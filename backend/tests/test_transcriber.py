import pytest
import os
from unittest.mock import patch, MagicMock, mock_open
from transcriber import split_script_for_tts, transcribe_audio, download_audio

def test_split_script_short_text():
    """Text under 4000 chars returns single chunk."""
    text = "Hello world. " * 100  # ~1300 chars
    chunks = split_script_for_tts(text)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_split_script_splits_at_sentence_boundary():
    """Long text splits at sentence boundary before 4000 chars."""
    sentence = "This is a sentence. "
    text = sentence * 210  # ~4200 chars
    chunks = split_script_for_tts(text)
    assert len(chunks) == 2
    for chunk in chunks:
        assert len(chunk) <= 4000

def test_split_script_no_sentence_splits_at_space():
    """Text with no sentence boundary falls back to last space."""
    text = "a" * 3900 + " " + "b" * 200
    chunks = split_script_for_tts(text)
    assert len(chunks) == 2
    assert all(len(c) <= 4000 for c in chunks)

def test_download_audio_saves_file(tmp_path):
    mock_response = MagicMock()
    mock_response.content = b"fake audio data"
    mock_response.raise_for_status = MagicMock()
    with patch("transcriber.httpx.get", return_value=mock_response):
        path = download_audio("https://example.com/ep.mp3", str(tmp_path))
    assert os.path.exists(path)
    assert open(path, "rb").read() == b"fake audio data"

def test_transcribe_audio_small_file(tmp_path):
    """File under 25MB: single Whisper call."""
    audio_file = tmp_path / "ep.mp3"
    audio_file.write_bytes(b"x" * 1000)
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = MagicMock(text="Hello world")
    with patch("transcriber.openai.OpenAI", return_value=mock_client):
        result = transcribe_audio(str(audio_file))
    assert result == "Hello world"
    mock_client.audio.transcriptions.create.assert_called_once()
