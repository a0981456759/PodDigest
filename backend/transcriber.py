import os
import time
import httpx
import openai
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

WHISPER_SIZE_LIMIT = 25 * 1024 * 1024  # 25 MB


def download_audio(url: str, storage_dir: str) -> str:
    """Download audio file to storage_dir. Returns local path."""
    os.makedirs(storage_dir, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0] or "episode.mp3"
    local_path = os.path.join(storage_dir, filename)
    response = httpx.get(url, follow_redirects=True, timeout=120)
    response.raise_for_status()
    with open(local_path, "wb") as f:
        f.write(response.content)
    return local_path


def _chunk_audio(file_path: str) -> list[str]:
    """Split audio file into ≤10min chunks. Returns list of chunk paths."""
    try:
        from pydub import AudioSegment
        from pydub.silence import split_on_silence
    except ImportError:
        raise RuntimeError("pydub not installed")

    audio = AudioSegment.from_file(file_path)
    ten_min_ms = 10 * 60 * 1000

    # Try splitting on silence first
    chunks = split_on_silence(audio, min_silence_len=500, silence_thresh=-40, keep_silence=200)

    # Merge small chunks into ≤10min segments
    merged = []
    current = AudioSegment.empty()
    for chunk in chunks:
        if len(current) + len(chunk) > ten_min_ms:
            merged.append(current)
            current = chunk
        else:
            current += chunk
    if len(current) > 0:
        merged.append(current)

    if not merged:
        # Fallback: force-split at exactly 10 min
        merged = [audio[i:i + ten_min_ms] for i in range(0, len(audio), ten_min_ms)]

    base = os.path.splitext(file_path)[0]
    paths = []
    for i, seg in enumerate(merged):
        path = f"{base}_chunk{i}.mp3"
        seg.export(path, format="mp3", bitrate="64k")
        paths.append(path)
    return paths


def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file using Whisper. Returns transcript text."""
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    file_size = os.path.getsize(file_path)

    if file_size > WHISPER_SIZE_LIMIT:
        chunk_paths = _chunk_audio(file_path)
    else:
        chunk_paths = [file_path]

    transcripts = []
    for chunk_path in chunk_paths:
        with open(chunk_path, "rb") as f:
            result = client.audio.transcriptions.create(model="whisper-1", file=f)
        transcripts.append(result.text)
        # Clean up chunk files (but not the original)
        if chunk_path != file_path:
            try:
                os.remove(chunk_path)
            except OSError:
                pass

    return "\n".join(transcripts)


def transcribe_with_retry(file_path: str, max_retries: int = 2) -> str:
    """Transcribe with up to max_retries retries on failure."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return transcribe_audio(file_path)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(5)
    raise last_error


def split_script_for_tts(text: str, max_chars: int = 4000) -> list[str]:
    """Split text into chunks ≤ max_chars at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text
    while len(remaining) > max_chars:
        # Scan backwards from max_chars for sentence boundary
        boundary = -1
        for i in range(max_chars, max(max_chars - 500, 0), -1):
            if i < len(remaining) and remaining[i - 1] in ".?!" and (i >= len(remaining) or remaining[i] in " \n"):
                boundary = i
                break
        if boundary == -1:
            # Fallback: split at last space
            boundary = remaining.rfind(" ", 0, max_chars)
            if boundary == -1:
                boundary = max_chars
        chunks.append(remaining[:boundary].strip())
        remaining = remaining[boundary:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks
