from __future__ import annotations

from fastapi import APIRouter

from .routes import documents, files, jobs

api_router = APIRouter()
api_router.include_router(files.router, tags=["files"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(jobs.router, tags=["jobs"])

