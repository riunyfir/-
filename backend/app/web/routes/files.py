from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from ...db import get_session
from ...models import Document
from ...settings import settings

router = APIRouter()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@router.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename is required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file")

    sha256 = _sha256_bytes(content)
    existing = session.exec(select(Document).where(Document.sha256 == sha256)).first()
    if existing:
        return {"document_id": str(existing.id), "deduped": True}

    doc = Document(
        filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        sha256=sha256,
        size_bytes=len(content),
        status="uploaded",
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    uploads_dir = settings.resolved_uploads_dir()
    uploads_dir.mkdir(parents=True, exist_ok=True)
    target: Path = uploads_dir / f"{doc.id}__{Path(file.filename).name}"
    target.write_bytes(content)

    return {"document_id": str(doc.id), "deduped": False}

