import os
from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a neutral, fact-based political context summarizer.
Your only job is to explain what a speaker was referring to in context.
Do not editorialize, express opinion, or characterize the speaker's position as good or bad.
Write 2-3 sentences maximum."""

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
    return _client


def summarize(quote_text: str, speaker: str | None, excerpt: str, source_title: str, source_url: str) -> str:
    speaker_label = speaker or "the speaker"
    prompt = (
        f'Quote submitted: "{quote_text}"\n'
        f"Attributed to: {speaker_label}\n\n"
        f'Matched transcript excerpt:\n"""{excerpt}"""\n'
        f"Source: {source_title} ({source_url})\n\n"
        f"Summarize what context surrounds this quote based on the transcript."
    )
    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return response.text.strip()
