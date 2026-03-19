import os
import json
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-20250514"
_COST_IN_PER_MTOK = 3.0   # $ per million input tokens
_COST_OUT_PER_MTOK = 15.0  # $ per million output tokens


def _extract_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1)
    return json.loads(text.strip())


def _calc_cost(usage) -> float:
    return (usage.input_tokens / 1e6 * _COST_IN_PER_MTOK +
            usage.output_tokens / 1e6 * _COST_OUT_PER_MTOK)


def summarize_episode(transcript: str, interest_description: str, topic_tags: list[str]) -> tuple[dict, float]:
    """Returns (summary_dict, cost_usd)."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    tags_str = ", ".join(topic_tags) if topic_tags else "general"

    prompt = f"""You are summarizing a podcast episode transcript for a listener with specific interests.

Listener interests: {interest_description}
Listener topic tags: {tags_str}

Transcript:
{transcript}

Respond with ONLY a JSON object (no markdown, no explanation):
{{
  "relevance_score": <float 0.0-1.0, how relevant this episode is to the listener's interests>,
  "key_topics": [<list of 3-6 main topics discussed>],
  "highlights": [<list of 3-5 notable quotes or insights>],
  "summary": "<2-4 sentence summary of the episode>"
}}"""

    message = client.messages.create(
        model=MODEL, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(message.content[0].text), _calc_cost(message.usage)


def generate_digest_script(
    summaries: list[dict],
    output_language: str,
    interest_description: str,
    topic_tags: list[str],
) -> tuple[str, float]:
    """Returns (script_text, cost_usd)."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    tags_str = ", ".join(topic_tags) if topic_tags else "general"
    lang_instruction = "Write in English." if output_language == "en" else "以繁體中文撰寫。"

    episodes_text = ""
    for i, item in enumerate(sorted(summaries, key=lambda x: -x["summary_data"].get("relevance_score", 0)), 1):
        sd = item["summary_data"]
        episodes_text += f"""
Episode {i}: {item['episode_title']} (from {item['show_title']})
Relevance: {sd.get('relevance_score', 0):.2f}
Topics: {', '.join(sd.get('key_topics', []))}
Highlights: {'; '.join(sd.get('highlights', []))}
Summary: {sd.get('summary', '')}
"""

    low_relevance_note = ""
    if all(item["summary_data"].get("relevance_score", 0) < 0.3 for item in summaries):
        low_relevance_note = "Note: This week's content has low relevance to the listener's interests. Open with an acknowledgment of this."

    prompt = f"""You are a podcast host creating a personalized audio digest. {lang_instruction}

Listener interests: {interest_description}
Listener topics: {tags_str}
{low_relevance_note}

Episodes to cover:
{episodes_text}

Write a natural, flowing broadcaster-style narration script that covers ALL episodes above in full detail.
- Start with a brief intro
- Cover each episode in order (most relevant first), giving each full treatment
- Use natural transitions between episodes
- End with a brief closing
- Write as if speaking aloud — no bullet points, just flowing prose
- No duration limit — cover everything thoroughly

Write ONLY the script text, nothing else."""

    message = client.messages.create(
        model=MODEL, max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text, _calc_cost(message.usage)
