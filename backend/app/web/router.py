from __future__ import annotations

from fastapi import APIRouter

from .routes import documents, files

api_router = APIRouter()
api_router.include_router(files.router, tags=["files"])
api_router.include_router(documents.router, tags=["documents"])

