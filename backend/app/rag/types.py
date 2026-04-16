from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    distance: float
    source: str = "vector"  # vector | keyword | neighbor | fts | rrf
