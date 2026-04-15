from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PKM_", env_file=".env", extra="ignore")

    # Storage
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    sqlite_path: Path | None = None  # default: data_dir/app.db
    uploads_dir: Path | None = None  # default: data_dir/uploads
    chroma_dir: Path | None = None  # default: data_dir/chroma

    # CORS
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    # Ollama
    ollama_host: str = "http://127.0.0.1:11434"
    llm_model: str = "qwen2.5:7b-instruct"
    embed_model: str = "nomic-embed-text"

    def resolved_sqlite_path(self) -> Path:
        return self.sqlite_path or (self.data_dir / "app.db")

    def resolved_uploads_dir(self) -> Path:
        return self.uploads_dir or (self.data_dir / "uploads")

    def resolved_chroma_dir(self) -> Path:
        return self.chroma_dir or (self.data_dir / "chroma")


settings = Settings()

