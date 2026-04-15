from __future__ import annotations

import datetime as dt
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    filename: str
    mime_type: str
    sha256: str = Field(index=True)
    size_bytes: int
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    text_chars: int = 0
    status: str = "uploaded"  # uploaded/parsed/indexed/failed


class DocumentText(SQLModel, table=True):
    __tablename__ = "document_texts"

    document_id: UUID = Field(primary_key=True, foreign_key="documents.id")
    full_text: str


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    document_id: UUID = Field(index=True, foreign_key="documents.id")
    chunk_index: int
    content: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class Summary(SQLModel, table=True):
    __tablename__ = "summaries"

    document_id: UUID = Field(primary_key=True, foreign_key="documents.id")
    short_summary: str
    bullets_json: str
    outline_md: str
    updated_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))


class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(index=True, unique=True)


class DocumentTag(SQLModel, table=True):
    __tablename__ = "document_tags"

    document_id: UUID = Field(primary_key=True, foreign_key="documents.id")
    tag_id: UUID = Field(primary_key=True, foreign_key="tags.id")
    score: float = 0.0


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    title: str = "New Chat"


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    session_id: UUID = Field(index=True, foreign_key="chat_sessions.id")
    role: str  # user/assistant
    content: str
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    # Minimal citation storage (JSON string) for MVP
    citations_json: str = "[]"

