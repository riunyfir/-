from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session, col, select

from ..llm.query_rewrite import expand_search_queries
from ..llm.ollama_client import embed_texts
from ..models import Chunk, DocumentTag, Tag
from ..settings import settings
from .chroma_store import get_chroma_collection
from .fts import fts_search_chunk_ids
from .fusion import reciprocal_rank_fusion
from .keyword_search import keyword_search_chunks
from .rerank import llm_rerank
from .types import RetrievedChunk


def _where_clause(document_id: UUID | None, session: Session | None, tag: str | None) -> dict[str, Any] | None:
    where: dict[str, Any] | None = None
    if document_id is not None:
        where = {"document_id": str(document_id)}
    if tag is not None:
        if session is None:
            raise ValueError("session is required for tag filtering")
        tag_row = session.exec(select(Tag).where(Tag.name == tag)).first()
        if not tag_row:
            return None
        doc_ids = session.exec(select(DocumentTag.document_id).where(DocumentTag.tag_id == tag_row.id)).all()
        ids = [str(did) for did in doc_ids]
        if not ids:
            return None
        where = (where or {}) | {"document_id": {"$in": ids}}
    return where


def _vector_search(
    collection,
    query: str,
    n_results: int,
    where: dict[str, Any] | None,
) -> list[RetrievedChunk]:
    q_emb = embed_texts([query])[0]
    res = collection.query(
        query_embeddings=[q_emb],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out: list[RetrievedChunk] = []
    for doc_text, meta, dist in zip(docs, metas, dists):
        if not meta:
            continue
        out.append(
            RetrievedChunk(
                chunk_id=str(meta.get("chunk_id")),
                document_id=str(meta.get("document_id")),
                chunk_index=int(meta.get("chunk_index", -1)),
                content=str(doc_text or ""),
                distance=float(dist),
                source="vector",
            )
        )
    return out


def _load_chunks_by_ids(session: Session, chunk_ids: list[str], *, source: str, score_by_id: dict[str, float]) -> list[RetrievedChunk]:
    if not chunk_ids:
        return []
    uuids = []
    for cid in chunk_ids:
        try:
            uuids.append(UUID(cid))
        except Exception:
            continue
    if not uuids:
        return []
    rows = session.exec(select(Chunk).where(col(Chunk.id).in_(uuids))).all()
    by_id = {str(r.id): r for r in rows}
    out: list[RetrievedChunk] = []
    for cid in chunk_ids:
        row = by_id.get(cid)
        if not row:
            continue
        s = float(score_by_id.get(cid, 0.0))
        out.append(
            RetrievedChunk(
                chunk_id=str(row.id),
                document_id=str(row.document_id),
                chunk_index=int(row.chunk_index),
                content=row.content or "",
                distance=1.0 - min(1.0, s),
                source=source,
            )
        )
    return out


def _load_neighbors(session: Session, center: RetrievedChunk, window: int) -> list[RetrievedChunk]:
    if window <= 0:
        return []
    try:
        did = UUID(center.document_id)
    except Exception:
        return []
    idx = center.chunk_index
    out: list[RetrievedChunk] = []
    for delta in range(-window, window + 1):
        if delta == 0:
            continue
        row = session.exec(
            select(Chunk).where(Chunk.document_id == did).where(Chunk.chunk_index == idx + delta)
        ).first()
        if not row:
            continue
        out.append(
            RetrievedChunk(
                chunk_id=str(row.id),
                document_id=str(row.document_id),
                chunk_index=int(row.chunk_index),
                content=row.content or "",
                distance=float(center.distance) + 0.01 * abs(delta),
                source="neighbor",
            )
        )
    return out


def retrieve(
    query: str,
    top_k: int | None = None,
    document_id: UUID | None = None,
    tag: str | None = None,
    session: Session | None = None,
) -> list[RetrievedChunk]:
    """
    High-recall pipeline:
    - Query rewrite (LLM) -> multiple vector queries
    - Vector (Chroma) + FTS5 (BM25) + lexical keyword overlap
    - Reciprocal Rank Fusion (RRF)
    - LLM rerank on a candidate pool
    - Neighbor chunk expansion for context completeness
    """
    top_k = top_k or settings.rag_final_top_k
    pool = max(int(getattr(settings, "rag_rerank_pool", 28)), top_k * 3)
    vec_k = max(settings.rag_vec_candidates, pool)
    kw_limit = max(settings.rag_keyword_limit, pool)

    where = _where_clause(document_id, session, tag)
    if where is None and tag is not None:
        return []

    if session is None:
        # Minimal fallback (should not happen in QnA path)
        collection = get_chroma_collection()
        try:
            return _vector_search(collection, query.strip(), min(top_k, vec_k), where)[:top_k]
        except Exception:
            return []

    queries = expand_search_queries(query.strip(), max_queries=int(getattr(settings, "rag_query_rewrite_max", 4)))
    tag_doc_ids: list[UUID] | None = None
    if tag is not None:
        tag_row = session.exec(select(Tag).where(Tag.name == tag)).first()
        if not tag_row:
            return []
        tag_doc_ids = list(session.exec(select(DocumentTag.document_id).where(DocumentTag.tag_id == tag_row.id)).all())

    collection = get_chroma_collection()

    vec_rank_lists: list[list[str]] = []
    for q in queries:
        try:
            hits = _vector_search(collection, q, vec_k, where)
            vec_rank_lists.append([h.chunk_id for h in hits])
        except Exception:
            vec_rank_lists.append([])

    fts_lists: list[list[str]] = []
    primary_q = queries[0] if queries else query.strip()
    for q in queries[:2]:
        fts_lists.append(
            fts_search_chunk_ids(
                session,
                q,
                document_id=document_id,
                tag_doc_ids=tag_doc_ids,
                limit=pool,
            )
        )
    # de-dup fts lists into one ranked list (keep first list primary)
    fts_merged: list[str] = []
    seen_fts: set[str] = set()
    for lst in fts_lists:
        for cid in lst:
            if cid not in seen_fts:
                seen_fts.add(cid)
                fts_merged.append(cid)

    kw_pairs = keyword_search_chunks(
        session,
        primary_q,
        document_id=document_id,
        tag=tag,
        limit=kw_limit,
    )
    kw_rank_list = [str(ch.id) for ch, _s in kw_pairs]

    ranked_lists = [x for x in vec_rank_lists if x] + [fts_merged] + ([kw_rank_list] if kw_rank_list else [])
    fused = reciprocal_rank_fusion(ranked_lists, k=int(getattr(settings, "rag_rrf_k", 60)))
    if not fused:
        return []

    score_by_id = {cid: sc for cid, sc in fused}
    candidate_ids = [cid for cid, _ in fused[:pool]]

    candidates = _load_chunks_by_ids(session, candidate_ids, source="rrf", score_by_id=score_by_id)
    # Preserve RRF order
    order_map = {cid: i for i, cid in enumerate(candidate_ids)}
    candidates.sort(key=lambda c: order_map.get(c.chunk_id, 9999))

    reranked = llm_rerank(primary_q, candidates, top_n=top_k) if getattr(settings, "rag_rerank", True) else candidates[:top_k]

    if settings.rag_neighbor_window <= 0:
        return reranked[: settings.rag_max_context_chunks]

    final: list[RetrievedChunk] = []
    seen2: set[str] = set()
    for c in reranked:
        for part in [c] + _load_neighbors(session, c, settings.rag_neighbor_window):
            if part.chunk_id in seen2:
                continue
            seen2.add(part.chunk_id)
            final.append(part)

    final.sort(key=lambda x: (x.document_id, x.chunk_index))
    return final[: settings.rag_max_context_chunks]
