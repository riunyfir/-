from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ...agents.mindmap import to_outline_md
from ...agents.summarizer import summarize
from ...agents.tagger import tag_document
from ...agents.qna import answer_question
from ...db import get_session
from ...ingest.chunker import chunk_text
from ...ingest.doc_reader import read_text_from_path
from ...models import (
    ChatMessage,
    ChatSession,
    Chunk,
    Document,
    DocumentTag,
    DocumentText,
    Summary,
    Tag,
)
from ...settings import settings
from ...rag.indexer import index_document_chunks
from ..schemas import ChatRequest, ChatResponse

router = APIRouter()


def _find_uploaded_file(document_id: UUID) -> Path | None:
    uploads_dir = settings.resolved_uploads_dir()
    if not uploads_dir.exists():
        return None
    matches = list(uploads_dir.glob(f"{document_id}__*"))
    return matches[0] if matches else None


@router.get("/documents")
def list_documents(session: Session = Depends(get_session)):
    docs = session.exec(select(Document).order_by(Document.created_at.desc())).all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "mime_type": d.mime_type,
            "size_bytes": d.size_bytes,
            "created_at": d.created_at.isoformat(),
            "status": d.status,
            "text_chars": d.text_chars,
        }
        for d in docs
    ]


@router.get("/documents/{document_id}")
def get_document(document_id: UUID, session: Session = Depends(get_session)):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "mime_type": doc.mime_type,
        "size_bytes": doc.size_bytes,
        "created_at": doc.created_at.isoformat(),
        "status": doc.status,
        "text_chars": doc.text_chars,
    }


@router.post("/documents/{document_id}/process")
def process_document(document_id: UUID, session: Session = Depends(get_session)):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")

    uploaded = _find_uploaded_file(document_id)
    if not uploaded:
        raise HTTPException(status_code=404, detail="uploaded file missing on disk")

    try:
        text = read_text_from_path(uploaded)
    except ValueError as e:
        doc.status = "failed"
        session.add(doc)
        session.commit()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        doc.status = "failed"
        session.add(doc)
        session.commit()
        raise

    if not text.strip():
        doc.status = "failed"
        session.add(doc)
        session.commit()
        raise HTTPException(status_code=400, detail="no extractable text")

    # Upsert document text
    existing_text = session.get(DocumentText, document_id)
    if existing_text:
        existing_text.full_text = text
        session.add(existing_text)
    else:
        session.add(DocumentText(document_id=document_id, full_text=text))

    # Replace chunks for idempotency
    old_chunks = session.exec(select(Chunk).where(Chunk.document_id == document_id)).all()
    for ch in old_chunks:
        session.delete(ch)
    session.commit()

    chunks = chunk_text(text)
    for i, ch in enumerate(chunks):
        session.add(
            Chunk(
                document_id=document_id,
                chunk_index=i,
                content=ch.content,
                start_char=ch.start_char,
                end_char=ch.end_char,
            )
        )

    doc.text_chars = len(text)
    doc.status = "parsed"
    session.add(doc)
    session.commit()

    # Best-effort vector indexing (requires chromadb installed + ollama running)
    indexed = 0
    indexing_error: str | None = None
    try:
        indexed = index_document_chunks(session=session, document_id=document_id)
        if indexed:
            doc.status = "indexed"
            session.add(doc)
            session.commit()
    except ModuleNotFoundError:
        # chromadb not installed yet
        indexing_error = "chromadb not installed"
    except Exception as e:
        # indexing failure should not block parsing for MVP, but should be visible to caller
        indexing_error = f"{type(e).__name__}: {e}"

    return {
        "document_id": str(document_id),
        "chunks": len(chunks),
        "indexed": indexed,
        "indexing_error": indexing_error,
        "status": doc.status,
    }


@router.post("/documents/{document_id}/summarize")
def summarize_document(document_id: UUID, session: Session = Depends(get_session)):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    text = session.get(DocumentText, document_id)
    if not text:
        raise HTTPException(status_code=400, detail="document not processed yet")

    out = summarize(text.full_text[:20000])  # keep latency bounded for MVP
    row = Summary(
        document_id=document_id,
        short_summary=out.short_summary,
        bullets_json=json.dumps(out.bullets, ensure_ascii=False),
        outline_md=out.outline_md,
    )
    session.merge(row)
    session.commit()
    return out.model_dump()


@router.post("/documents/{document_id}/tag")
def tag_doc(document_id: UUID, session: Session = Depends(get_session)):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    text = session.get(DocumentText, document_id)
    if not text:
        raise HTTPException(status_code=400, detail="document not processed yet")

    out = tag_document(text.full_text[:20000])
    # upsert tags + mapping
    # delete existing mappings
    existing = session.exec(select(DocumentTag).where(DocumentTag.document_id == document_id)).all()
    for r in existing:
        session.delete(r)
    session.commit()

    created: list[dict] = []
    for t in out.tags:
        tag_row = session.exec(select(Tag).where(Tag.name == t.name)).first()
        if not tag_row:
            tag_row = Tag(name=t.name)
            session.add(tag_row)
            session.commit()
            session.refresh(tag_row)

        session.add(DocumentTag(document_id=document_id, tag_id=tag_row.id, score=float(t.score)))
        created.append({"id": str(tag_row.id), "name": tag_row.name, "score": float(t.score)})

    session.commit()
    return {"document_id": str(document_id), "tags": created}


@router.get("/documents/{document_id}/mindmap")
def get_mindmap(document_id: UUID, session: Session = Depends(get_session)):
    summ = session.get(Summary, document_id)
    if summ and summ.outline_md.strip():
        return {"document_id": str(document_id), "outline_md": summ.outline_md}

    text = session.get(DocumentText, document_id)
    if not text:
        raise HTTPException(status_code=400, detail="document not processed yet")

    outline = to_outline_md(text.full_text[:20000])
    return {"document_id": str(document_id), "outline_md": outline}


@router.post("/chat", response_model=ChatResponse)
def chat_api(body: ChatRequest, session: Session = Depends(get_session)):
    doc_id = body.document_id if body.scope == "document" else None
    tag = body.tag if body.scope == "tag" else None

    out = answer_question(body.question, session=session, document_id=doc_id, tag=tag)

    # Session persistence (SQLite)
    sess_id: UUID
    if body.session_id:
        try:
            sess_id = UUID(body.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid session_id")
        sess = session.get(ChatSession, sess_id)
        if not sess:
            sess = ChatSession(id=sess_id, title=body.question[:40] or "Chat")
            session.add(sess)
            session.commit()
    else:
        sess = ChatSession(id=uuid4(), title=body.question[:40] or "Chat")
        session.add(sess)
        session.commit()
        session.refresh(sess)
        sess_id = sess.id

    citations = [c.model_dump() for c in out.citations]
    session.add(ChatMessage(session_id=sess.id, role="user", content=body.question))
    session.add(
        ChatMessage(
            session_id=sess.id,
            role="assistant",
            content=out.answer,
            citations_json=json.dumps(citations, ensure_ascii=False),
        )
    )
    session.commit()

    return ChatResponse(answer=out.answer, citations=citations, session_id=str(sess.id))

