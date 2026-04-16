from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    content: str
    start_char: int
    end_char: int


def _window_chunks(rebuilt: str, max_chars: int, overlap: int) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    n = len(rebuilt)
    start = 0
    while start < n:
        end = min(n, start + max_chars)
        slice_ = rebuilt[start:end]

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


def _split_markdown_sections(text: str) -> list[str]:
    """
    Split on ATX headings (# .. ######) at line starts for denser topical chunks.
    """
    t = (text or "").strip()
    if not t:
        return []
    parts = re.split(r"(?m)(?=^#{1,6}\s)", t)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str, max_chars: int = 900, overlap: int = 200) -> list[TextChunk]:
    """
    Chunk by Markdown headings when present, then sliding-window within each section.
    Slightly smaller windows + more overlap improve embedding recall for Q&A.
    """
    t = (text or "").strip()
    if not t:
        return []

    sections = _split_markdown_sections(t)
    if len(sections) <= 1 and not re.search(r"^#{1,6}\s", t, re.MULTILINE):
        paragraphs = [p.strip() for p in t.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [t]
        rebuilt = "\n\n".join(paragraphs)
        return _window_chunks(rebuilt, max_chars, overlap)

    out: list[TextChunk] = []
    offset = 0
    for sec in sections:
        pos = t.find(sec, offset)
        if pos < 0:
            pos = offset
        sub = sec
        if len(sub) <= max_chars:
            out.append(TextChunk(content=sub.strip(), start_char=pos, end_char=pos + len(sub)))
            offset = pos + len(sub)
            continue
        for w in _window_chunks(sub, max_chars, overlap):
            out.append(TextChunk(content=w.content, start_char=pos + w.start_char, end_char=pos + w.end_char))
        offset = pos + len(sub)

    return out

