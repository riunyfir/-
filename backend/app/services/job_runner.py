from __future__ import annotations

import json
import datetime as dt
from uuid import UUID

from sqlmodel import Session

from ..db import engine
from ..models import BackgroundJob
from ..pipeline.document_ops import process_document_core, summarize_document_core, tag_document_core


def _touch_updated(job: BackgroundJob) -> None:
    job.updated_at = dt.datetime.now(dt.timezone.utc)


def run_background_job(job_id: UUID) -> None:
    with Session(engine) as session:
        job = session.get(BackgroundJob, job_id)
        if not job:
            return
        if job.status not in ("pending",):
            return

        job.status = "running"
        job.progress = 0
        job.message = "开始…"
        _touch_updated(job)
        session.add(job)
        session.commit()

        def on_progress(p: int, msg: str) -> None:
            with Session(engine) as s2:
                j = s2.get(BackgroundJob, job_id)
                if not j:
                    return
                j.progress = min(100, max(0, p))
                j.message = msg
                _touch_updated(j)
                s2.add(j)
                s2.commit()

        try:
            if job.job_type == "process":
                result = process_document_core(session, job.document_id, on_progress=on_progress)
            elif job.job_type == "summarize":
                result = summarize_document_core(session, job.document_id, on_progress=on_progress)
            elif job.job_type == "tag":
                result = tag_document_core(session, job.document_id, on_progress=on_progress)
            else:
                raise ValueError(f"unknown job_type: {job.job_type}")

            with Session(engine) as s3:
                j = s3.get(BackgroundJob, job_id)
                if not j:
                    return
                j.status = "succeeded"
                j.progress = 100
                j.message = "完成"
                j.result_json = json.dumps(result, ensure_ascii=False)
                j.error = ""
                _touch_updated(j)
                s3.add(j)
                s3.commit()
        except Exception as e:
            err = getattr(e, "detail", None)
            if err is None:
                err = str(e)
            elif not isinstance(err, str):
                err = str(err)
            with Session(engine) as s4:
                j = s4.get(BackgroundJob, job_id)
                if not j:
                    return
                j.status = "failed"
                j.error = err[:4000]
                j.message = "失败"
                _touch_updated(j)
                s4.add(j)
                s4.commit()
