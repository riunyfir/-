from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from .settings import settings


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


sqlite_path = settings.resolved_sqlite_path()
ensure_parent_dir(sqlite_path)

engine = create_engine(
    f"sqlite:///{sqlite_path}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    from .models import BackgroundJob  # noqa: F401

    SQLModel.metadata.create_all(engine)
    from .rag.fts import ensure_fts_table, rebuild_chunk_fts_all

    ensure_fts_table(engine)
    try:
        with Session(engine) as session:
            nfts = session.execute(text("SELECT COUNT(*) FROM chunk_fts")).scalar_one()
            nch = session.execute(text("SELECT COUNT(*) FROM chunks")).scalar_one()
            if int(nfts or 0) == 0 and int(nch or 0) > 0:
                rebuild_chunk_fts_all(session)
                session.commit()
    except Exception:
        # FTS optional on some SQLite builds; app still runs without FTS
        pass


def get_session():
    with Session(engine) as session:
        yield session

