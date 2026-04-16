from __future__ import annotations

import re
from uuid import UUID

from sqlmodel import Session, col, select

from ..models import Chunk, DocumentTag, Tag


def extract_search_terms(question: str, max_terms: int = 48) -> list[str]:
    """
    Build substring terms for lexical matching (English words + CJK n-grams).
    No external tokenizer required (works offline).
    """
    q = (question or "").strip()
    if not q:
        return []

    terms: list[str] = []
    seen: set[str] = set()

    def add(t: str) -> None:
        t = t.strip()
        if len(t) < 2:
            return
        if t not in seen:
            seen.add(t)
            terms.append(t)

    # Alphanumeric tokens (incl. common tech tokens)
    for w in re.findall(r"[A-Za-z][A-Za-z0-9_.-]{1,}", q):
        add(w.lower())

    # CJK / mixed: remove spaces and generate 2–4 char n-grams
    compact = re.sub(r"\s+", "", q)
    for n in (4, 3, 2):
        if len(compact) < n:
            continue
        for i in range(len(compact) - n + 1):
            add(compact[i : i + n])

    # Short question as whole phrase (helps exact match)
    if len(compact) <= 24:
        add(compact)

    return terms[:max_terms]


def _doc_ids_for_tag(session: Session, tag: str) -> list[UUID] | None:
    tag_row = session.exec(select(Tag).where(Tag.name == tag)).first()
    if not tag_row:
        return []
    rows = session.exec(select(DocumentTag.document_id).where(DocumentTag.tag_id == tag_row.id)).all()
    return list(rows)


def keyword_search_chunks(
    session: Session,
    question: str,
    *,
    document_id: UUID | None = None,
    tag: str | None = None,
    limit: int = 14,
) -> list[tuple[Chunk, float]]:
    """
    Lexical fallback: score chunks by term overlap (cheap, improves recall when embeddings miss).
    Returns (chunk, score) sorted by score desc.
    """
    terms = extract_search_terms(question)
    if not terms:
        return []

    stmt = select(Chunk)
    if document_id is not None:
        stmt = stmt.where(Chunk.document_id == document_id)
    elif tag is not None:
        doc_ids = _doc_ids_for_tag(session, tag)
        if not doc_ids:
            return []
        stmt = stmt.where(col(Chunk.document_id).in_(doc_ids))

    chunks = session.exec(stmt).all()
    if not chunks:
        return []

    scored: list[tuple[Chunk, float]] = []
    q_lower = question.lower()

    for ch in chunks:
        text = ch.content or ""
        tl = text.lower()
        hits = 0.0
        for t in terms:
            if len(t) <= 4 and t in tl:
                hits += 1.0
            elif len(t) > 4 and t in tl:
                hits += 1.2
        # Boost if full question (compact) appears
        cq = re.sub(r"\s+", "", question)
        if len(cq) >= 4 and cq in re.sub(r"\s+", "", text):
            hits += 3.0
        if q_lower and q_lower in tl:
            hits += 0.5
        if hits <= 0:
            continue
        # Mild length normalization (prefer denser matches in shorter snippets)
        norm = hits / (1.0 + min(2000, len(text)) / 2000.0)
        scored.append((ch, float(norm)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
