from __future__ import annotations

import json
from collections.abc import Callable
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from ..agents.summarizer import summarize
from ..agents.tagger import tag_document
from ..ingest.chunker import chunk_text
from ..ingest.doc_reader import read_text_from_path
from ..models import Chunk, Document, DocumentTag, DocumentText, Summary, Tag
from ..rag.fts import sync_chunk_fts_for_document
from ..rag.indexer import index_document_chunks
from ..settings import settings

ProgressFn = Callable[[int, str], None]


def _noop_progress(_p: int, _m: str) -> None:
    pass


def process_document_core(
    session: Session,
    document_id: UUID,
    *,
    on_progress: ProgressFn | None = None,
) -> dict:
    prog = on_progress or _noop_progress
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")

    uploads_dir = settings.resolved_uploads_dir()
    if not uploads_dir.exists():
        raise HTTPException(status_code=404, detail="uploads directory missing")
    matches = list(uploads_dir.glob(f"{document_id}__*"))
    uploaded = matches[0] if matches else None
    if not uploaded:
        raise HTTPException(status_code=404, detail="uploaded file missing on disk")

    prog(5, "读取文件…")
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

    prog(15, "保存全文…")
    existing_text = session.get(DocumentText, document_id)
    if existing_text:
        existing_text.full_text = text
        session.add(existing_text)
    else:
        session.add(DocumentText(document_id=document_id, full_text=text))

    old_chunks = session.exec(select(Chunk).where(Chunk.document_id == document_id)).all()
    for ch in old_chunks:
        session.delete(ch)
    session.commit()

    prog(25, "文本切块…")
    chunks = chunk_text(text, max_chars=settings.chunk_max_chars, overlap=settings.chunk_overlap)
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

    prog(45, "更新全文索引(FTS)…")
    try:
        sync_chunk_fts_for_document(session, document_id)
    except Exception:
        pass

    prog(55, "向量嵌入与索引…")
    indexed = 0
    indexing_error: str | None = None
    try:
        indexed = index_document_chunks(session=session, document_id=document_id)
        if indexed:
            doc.status = "indexed"
            session.add(doc)
            session.commit()
    except ModuleNotFoundError:
        indexing_error = "chromadb not installed"
    except Exception as e:
        indexing_error = f"{type(e).__name__}: {e}"

    prog(100, "完成")
    return {
        "document_id": str(document_id),
        "chunks": len(chunks),
        "indexed": indexed,
        "indexing_error": indexing_error,
        "status": doc.status,
    }


def summarize_document_core(
    session: Session,
    document_id: UUID,
    *,
    on_progress: ProgressFn | None = None,
) -> dict:
    prog = on_progress or _noop_progress
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    text = session.get(DocumentText, document_id)
    if not text:
        raise HTTPException(status_code=400, detail="document not processed yet")

    prog(10, "生成摘要（可能分段处理长文）…")
    out = summarize(text.full_text)
    prog(85, "写入数据库…")
    row = Summary(
        document_id=document_id,
        short_summary=out.short_summary,
        bullets_json=json.dumps(out.bullets, ensure_ascii=False),
        outline_md=out.outline_md,
    )
    session.merge(row)
    session.commit()
    prog(100, "完成")
    return out.model_dump()


def tag_document_core(
    session: Session,
    document_id: UUID,
    *,
    on_progress: ProgressFn | None = None,
) -> dict:
    prog = on_progress or _noop_progress
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    text = session.get(DocumentText, document_id)
    if not text:
        raise HTTPException(status_code=400, detail="document not processed yet")

    prog(15, "加载文档块…")
    chunk_rows = session.exec(
        select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index.asc())
    ).all()
    chunk_contents = [c.content for c in chunk_rows if c.content]

    prog(40, "生成标签…")
    out = tag_document(
        text.full_text,
        chunk_contents=chunk_contents if chunk_contents else None,
    )

    prog(70, "保存标签…")
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
    prog(100, "完成")
    return {"document_id": str(document_id), "tags": created}
