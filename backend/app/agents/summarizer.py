from __future__ import annotations

import json

from ..llm.ollama_client import chat
from .schemas import SummaryOut
from .utils import parse_json_model


SYSTEM = """You are a helpful personal knowledge assistant.
Return ONLY valid JSON, no markdown, no extra text."""


def summarize(text: str) -> SummaryOut:
    prompt = {
        "role": "user",
        "content": (
            "Summarize the document.\n\n"
            "Output JSON with keys:\n"
            "- short_summary: string\n"
            "- bullets: string[] (3-8 items)\n"
            "- outline_md: string (markdown outline, start with '# Title' then '##' subsections and '-' bullets)\n\n"
            f"DOCUMENT:\n{text}\n"
        ),
    }
    raw = chat([{"role": "system", "content": SYSTEM}, prompt])
    return parse_json_model(raw, SummaryOut)

