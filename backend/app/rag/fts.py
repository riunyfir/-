from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlmodel import Session, select

from ..models import Chunk
from .keyword_search import extract_search_terms


def ensure_fts_table(engine: Engine) -> None:
    """
    SQLite FTS5 full-text index over chunk content for lexical/BM25 retrieval.
    Prefers trigram tokenizer (better for CJK substring) when available; falls back to unicode61.
    """
    with engine.begin() as conn:
        try:
            conn.execute(
                text(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
                      chunk_id UNINDEXED,
                      document_id UNINDEXED,
                      content,
                      tokenize = 'trigram'
                    );
                    """
                )
            )
        except Exception:
            conn.execute(
                text(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
                      chunk_id UNINDEXED,
                      document_id UNINDEXED,
                      content,
                      tokenize = 'unicode61 remove_diacritics 1'
                    );
                    """
                )
            )


def _delete_fts_for_document(conn: Connection, document_id: UUID) -> None:
    conn.execute(
        text("DELETE FROM chunk_fts WHERE document_id = :d"),
        {"d": str(document_id)},
    )


def sync_chunk_fts_for_document(session: Session, document_id: UUID) -> int:
    """
    Replace FTS rows for a document from current `chunks` table.
    """
    engine = session.get_bind()
    if engine is None:
        return 0

    chunks = session.exec(select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index.asc())).all()
    with engine.begin() as conn:
        _delete_fts_for_document(conn, document_id)
        for ch in chunks:
            conn.execute(
                text(
                    """
                    INSERT INTO chunk_fts(chunk_id, document_id, content)
                    VALUES (:cid, :did, :c)
                    """
                ),
                {"cid": str(ch.id), "did": str(document_id), "c": ch.content or ""},
            )
    return len(chunks)


def rebuild_chunk_fts_all(session: Session) -> int:
    """
    Full rebuild (e.g. after first FTS migration). Can be slow on large DBs.
    """
    engine = session.get_bind()
    if engine is None:
        return 0
    chunks = session.exec(select(Chunk).order_by(Chunk.document_id, Chunk.chunk_index)).all()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM chunk_fts"))
        for ch in chunks:
            conn.execute(
                text(
                    """
                    INSERT INTO chunk_fts(chunk_id, document_id, content)
                    VALUES (:cid, :did, :c)
                    """
                ),
                {"cid": str(ch.id), "did": str(ch.document_id), "c": ch.content or ""},
            )
    return len(chunks)


def _fts_match_query(question: str) -> str:
    """
    Build a conservative FTS5 MATCH string (OR of quoted terms / n-grams).
    """
    terms = extract_search_terms(question, max_terms=12)
    if not terms:
        return ""
    parts: list[str] = []
    for t in terms:
        t = t.replace('"', " ").strip()
        if len(t) < 2:
            continue
        # Quote each token; OR-combine for recall
        parts.append('"' + t.replace('"', "") + '"')
    if not parts:
        return ""
    return " OR ".join(parts[:10])


def fts_search_chunk_ids(
    session: Session,
    question: str,
    *,
    document_id: UUID | None = None,
    tag_doc_ids: list[UUID] | None = None,
    limit: int = 20,
) -> list[str]:
    """
    Return chunk_id strings ordered by BM25 relevance (better matches first).
    """
    mq = _fts_match_query(question)
    if not mq:
        return []

    engine = session.get_bind()
    if engine is None:
        return []

    # bm25(): smaller is better in SQLite FTS5 bm25 auxiliary
    where_extra = ""
    params: dict = {"m": mq, "lim": int(limit)}
    if document_id is not None:
        where_extra = " AND document_id = :did"
        params["did"] = str(document_id)
    elif tag_doc_ids is not None:
        if not tag_doc_ids:
            return []
        placeholders = ",".join([f":t{i}" for i in range(len(tag_doc_ids))])
        for i, u in enumerate(tag_doc_ids):
            params[f"t{i}"] = str(u)
        where_extra = f" AND document_id IN ({placeholders})"

    sql = f"""
    SELECT chunk_id
    FROM chunk_fts
    WHERE chunk_fts MATCH :m
    {where_extra}
    ORDER BY bm25(chunk_fts) ASC
    LIMIT :lim
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
        return [str(r[0]) for r in rows if r and r[0]]
    except Exception:
        return []
