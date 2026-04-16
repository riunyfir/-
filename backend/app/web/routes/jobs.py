from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ...db import get_session
from ...models import BackgroundJob

router = APIRouter()


@router.get("/jobs/{job_id}")
def get_job(job_id: UUID, session: Session = Depends(get_session)):
    job = session.get(BackgroundJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    result = None
    if job.result_json:
        try:
            result = json.loads(job.result_json)
        except Exception:
            result = job.result_json
    return {
        "id": str(job.id),
        "job_type": job.job_type,
        "document_id": str(job.document_id),
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "error": job.error or None,
        "result": result,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }
