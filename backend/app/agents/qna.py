from __future__ import annotations

import json

from ..llm.ollama_client import chat
from sqlmodel import Session

from ..rag.retriever import RetrievedChunk, retrieve
from .schemas import AnswerOut
from .utils import parse_json_model


SYSTEM = """You are a personal knowledge assistant.
Use ONLY the provided context to answer.
Return ONLY valid JSON, no markdown, no extra text.
If the answer is not in context, say you don't know and suggest what to upload."""


def _format_context(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for c in chunks:
        parts.append(
            f"[doc={c.document_id} chunk={c.chunk_id} idx={c.chunk_index}]\n{c.content}\n"
        )
    return "\n---\n".join(parts)


def answer_question(
    question: str,
    session: Session,
    document_id: str | None = None,
    tag: str | None = None,
) -> AnswerOut:
    chunks = retrieve(
        query=question,
        top_k=6,
        document_id=None if document_id is None else __import__("uuid").UUID(document_id),
        tag=tag,
        session=session,
    )
    context = _format_context(chunks)
    user = {
        "role": "user",
        "content": (
            "Answer the question based on CONTEXT.\n"
            "Output JSON: {\"answer\": string, \"citations\": [{\"document_id\": string, \"chunk_id\": string, "
            "\"chunk_index\": number, \"quote\": string}...]}\n"
            "Citations must reference the chunk metadata and quote exact supporting sentences.\n\n"
            f"QUESTION:\n{question}\n\n"
            f"CONTEXT:\n{context}\n"
        ),
    }
    raw = chat([{"role": "system", "content": SYSTEM}, user])
    return parse_json_model(raw, AnswerOut)

