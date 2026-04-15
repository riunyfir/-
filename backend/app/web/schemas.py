from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str
    scope: Literal["all", "document", "tag"] = "all"
    document_id: Optional[str] = None
    tag: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict] = Field(default_factory=list)
    session_id: str

