from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .settings import settings
from .web.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(title="PKM Assistant API", version="0.1.0")

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.on_event("startup")
    def _startup():
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.resolved_uploads_dir().mkdir(parents=True, exist_ok=True)
        settings.resolved_chroma_dir().mkdir(parents=True, exist_ok=True)
        init_db()

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()

