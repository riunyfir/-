from __future__ import annotations

from ..llm.ollama_client import chat


SYSTEM = """You are a personal knowledge assistant.
Return ONLY markdown outline text, no code fences."""


def to_outline_md(text: str) -> str:
    user = {
        "role": "user",
        "content": (
            "Convert the document into a clean markdown outline for a mindmap.\n"
            "Rules:\n"
            "- First line: '# <Title>'\n"
            "- Use '##' headings for major sections\n"
            "- Use '-' bullets for subpoints\n"
            "- Keep it concise (max ~120 lines)\n\n"
            f"DOCUMENT:\n{text}\n"
        ),
    }
    return chat([{"role": "system", "content": SYSTEM}, user]).strip()

