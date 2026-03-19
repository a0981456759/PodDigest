import os
import time
import httpx
import openai
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

WHISPER_SIZE_LIMIT = 25 * 1024 * 1024  # 25 MB


def download_audio(url: str, storage_dir: str, progress_callback=None) -> str:
    """Download audio file to storage_dir with optional progress callback(downloaded, total)."""
    os.makedirs(storage_dir, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0] or "episode.mp3"
    if not filename.endswith('.mp3'):
        filename += '.mp3'
    local_path = os.path.join(storage_dir, filename)
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        with open(local_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)
    return local_path


def _chunk_audio(file_path: str) -> list[str]:
    """Split audio into ≤10min chunks using ffmpeg. Returns list of chunk paths."""
    import subprocess
    import shutil

    ffmpeg = shutil.which("ffmpeg") or r"C:\Users\Howard\anaconda3\envs\ML\Library\bin\ffmpeg.exe"
    base = os.path.splitext(file_path)[0]
    pattern = base + "_chunk%03d.mp3"

    subprocess.run(
        [ffmpeg, "-y", "-i", file_path, "-f", "segment", "-segment_time", "600",
         "-c", "copy", pattern],
        check=True, capture_output=True
    )

    # Collect generated chunks in order
    i = 0
    paths = []
    while True:
        p = base + f"_chunk{i:03d}.mp3"
        if not os.path.exists(p):
            break
        paths.append(p)
        i += 1
    return paths if paths else [file_path]


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
