from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    content: str
    start_char: int
    end_char: int


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[TextChunk]:
    """
    Simple sliding-window chunker over characters, biased to break at paragraph boundaries.
    """
    t = (text or "").strip()
    if not t:
        return []

    paragraphs = [p.strip() for p in t.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [t]

    chunks: list[TextChunk] = []
    cursor = 0
    rebuilt = "\n\n".join(paragraphs)

    n = len(rebuilt)
    start = 0
    while start < n:
        end = min(n, start + max_chars)
        slice_ = rebuilt[start:end]

        # Try to break nicely: last double-newline inside window
        if end < n:
            cut = slice_.rfind("\n\n")
            if cut > max_chars * 0.5:
                end = start + cut
                slice_ = rebuilt[start:end]

        content = slice_.strip()
        if content:
            chunks.append(TextChunk(content=content, start_char=start, end_char=end))

        if end >= n:
            break
        start = max(0, end - overlap)

    return chunks

