from __future__ import annotations

from ..llm.ollama_client import chat
from .schemas import TagsOut
from .utils import parse_json_model


SYSTEM = """You are a personal knowledge assistant.
Return ONLY valid JSON, no markdown, no extra text."""


def tag_document(text: str, max_tags: int = 8) -> TagsOut:
    prompt = {
        "role": "user",
        "content": (
            "Generate topical tags for this document.\n"
            f"Return JSON: {{\"tags\": [{{\"name\": string, \"score\": number}}...]}}.\n"
            f"Rules: 3 to {max_tags} tags, short names (1-4 words), score in [0,1].\n\n"
            f"DOCUMENT:\n{text}\n"
        ),
    }
    raw = chat([{"role": "system", "content": SYSTEM}, prompt])
    return parse_json_model(raw, TagsOut)

