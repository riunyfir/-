from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SummaryOut(BaseModel):
    short_summary: str = Field(..., description="1-3 sentences summary")
    bullets: list[str] = Field(default_factory=list, description="Key takeaways")
    outline_md: str = Field(..., description="Markdown outline for mindmap/markmap")


class TagOut(BaseModel):
    name: str
    score: float = 0.5


class TagsOut(BaseModel):
    tags: list[TagOut] = Field(default_factory=list)


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    chunk_index: int
    quote: str


class AnswerOut(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)

