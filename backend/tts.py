import os
import openai
from transcriber import split_script_for_tts
from dotenv import load_dotenv

load_dotenv()


def _concat_mp3_chunks(chunk_paths: list[str], output_path: str) -> str:
    """Concatenate MP3 files via binary append (all chunks are same-format TTS output)."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as out:
        for path in chunk_paths:
            out.write(open(path, "rb").read())
    return output_path


def synthesize_script(script: str, output_path: str, voice: str = "nova") -> str:
    """Synthesize full script to MP3 at output_path. Returns output_path."""
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    chunks = split_script_for_tts(script)

    if len(chunks) == 1:
        response = client.audio.speech.create(model="tts-1", voice=voice, input=chunks[0])
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)
        return output_path

    # Multiple chunks: synthesize each, then concat
    chunk_paths = []
    try:
        for i, chunk in enumerate(chunks):
            response = client.audio.speech.create(model="tts-1", voice=voice, input=chunk)
            tmp_path = output_path + f".chunk{i}.mp3"
            with open(tmp_path, "wb") as f:
                f.write(response.content)
            chunk_paths.append(tmp_path)
        return _concat_mp3_chunks(chunk_paths, output_path)
    finally:
        for p in chunk_paths:
            try:
                os.remove(p)
            except OSError:
                pass
