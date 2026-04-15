from __future__ import annotations

from typing import Iterable
from uuid import UUID

from sqlmodel import Session, select

from ..llm.ollama_client import embed_texts
from ..models import Chunk
from .chroma_store import get_chroma_collection


def _batched(seq: list, batch_size: int) -> Iterable[list]:
    for i in range(0, len(seq), batch_size):
        yield seq[i : i + batch_size]


def index_document_chunks(session: Session, document_id: UUID, batch_size: int = 64) -> int:
    chunks = session.exec(
        select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index.asc())
    ).all()
    if not chunks:
        return 0

    col = get_chroma_collection()

    # Remove old vectors for idempotency (by where filter)
    try:
        existing = col.get(where={"document_id": str(document_id)}, include=[])
        if existing and existing.get("ids"):
            col.delete(ids=existing["ids"])
    except Exception:
        # Collection may not support where on empty; ignore for MVP
        pass

    count = 0
    for batch in _batched(chunks, batch_size):
        texts = [c.content for c in batch]
        embs = embed_texts(texts)
        ids = [str(c.id) for c in batch]
        metas = [
            {
                "document_id": str(c.document_id),
                "chunk_id": str(c.id),
                "chunk_index": int(c.chunk_index),
            }
            for c in batch
        ]
        col.add(ids=ids, documents=texts, embeddings=embs, metadatas=metas)
        count += len(batch)

    return count

