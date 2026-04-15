from __future__ import annotations

from pathlib import Path

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
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session

