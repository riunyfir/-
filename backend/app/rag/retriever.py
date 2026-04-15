from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from ..llm.ollama_client import embed_texts
from ..models import DocumentTag, Tag
from .chroma_store import get_chroma_collection


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    distance: float


def retrieve(
    query: str,
    top_k: int = 6,
    document_id: UUID | None = None,
    tag: str | None = None,
    session: Session | None = None,
) -> list[RetrievedChunk]:
    col = get_chroma_collection()

    where: dict[str, Any] | None = None
    if document_id is not None:
        where = {"document_id": str(document_id)}
    if tag is not None:
        if session is None:
            raise ValueError("session is required for tag filtering")
        tag_row = session.exec(select(Tag).where(Tag.name == tag)).first()
        if not tag_row:
            return []
        doc_ids = session.exec(select(DocumentTag.document_id).where(DocumentTag.tag_id == tag_row.id)).all()
        ids = [str(did) for did in doc_ids]
        if not ids:
            return []
        where = (where or {}) | {"document_id": {"$in": ids}}

    q_emb = embed_texts([query])[0]
    res = col.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out: list[RetrievedChunk] = []
    for doc_text, meta, dist in zip(docs, metas, dists):
        out.append(
            RetrievedChunk(
                chunk_id=str(meta.get("chunk_id")),
                document_id=str(meta.get("document_id")),
                chunk_index=int(meta.get("chunk_index", -1)),
                content=str(doc_text),
                distance=float(dist),
            )
        )
    return out

