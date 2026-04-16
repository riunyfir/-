from __future__ import annotations

import json
from uuid import uuid4
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, col, select

from ...agents.mindmap import to_outline_md
from ...agents.qna import answer_question
from ...db import get_session
from ...models import BackgroundJob, ChatMessage, ChatSession, Document, DocumentText, Summary
from ...pipeline.document_ops import (
    process_document_core,
    summarize_document_core,
    tag_document_core,
)
from ...services.job_runner import run_background_job
from ..schemas import ChatRequest, ChatResponse

router = APIRouter()


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


@router.get("/documents/{document_id}/jobs")
def list_document_jobs(document_id: UUID, session: Session = Depends(get_session), limit: int = 30):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    rows = session.exec(
        select(BackgroundJob)
        .where(BackgroundJob.document_id == document_id)
        .order_by(col(BackgroundJob.created_at).desc())
    ).all()
    return [
        {
            "id": str(j.id),
            "job_type": j.job_type,
            "status": j.status,
            "progress": j.progress,
            "message": j.message,
            "created_at": j.created_at.isoformat(),
        }
        for j in rows[:limit]
    ]


@router.post("/documents/{document_id}/process")
def process_document(document_id: UUID, session: Session = Depends(get_session)):
    return process_document_core(session, document_id)


@router.post("/documents/{document_id}/process-async")
def process_document_async(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    job = BackgroundJob(
        job_type="process",
        document_id=document_id,
        status="pending",
        progress=0,
        message="排队中…",
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    background_tasks.add_task(run_background_job, job.id)
    return {"job_id": str(job.id), "status": job.status, "message": job.message}


@router.post("/documents/{document_id}/summarize")
def summarize_document(document_id: UUID, session: Session = Depends(get_session)):
    return summarize_document_core(session, document_id)


@router.post("/documents/{document_id}/summarize-async")
def summarize_document_async(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    if not session.get(DocumentText, document_id):
        raise HTTPException(status_code=400, detail="document not processed yet")
    job = BackgroundJob(
        job_type="summarize",
        document_id=document_id,
        status="pending",
        progress=0,
        message="排队中…",
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    background_tasks.add_task(run_background_job, job.id)
    return {"job_id": str(job.id), "status": job.status, "message": job.message}


@router.post("/documents/{document_id}/tag")
def tag_doc(document_id: UUID, session: Session = Depends(get_session)):
    return tag_document_core(session, document_id)


@router.post("/documents/{document_id}/tag-async")
def tag_doc_async(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    if not session.get(DocumentText, document_id):
        raise HTTPException(status_code=400, detail="document not processed yet")
    job = BackgroundJob(
        job_type="tag",
        document_id=document_id,
        status="pending",
        progress=0,
        message="排队中…",
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    background_tasks.add_task(run_background_job, job.id)
    return {"job_id": str(job.id), "status": job.status, "message": job.message}


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
