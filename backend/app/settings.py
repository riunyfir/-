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

    # RAG: hybrid retrieval + chunking (tune for recall vs latency)
    chunk_max_chars: int = 900
    chunk_overlap: int = 200
    rag_vec_candidates: int = 18
    rag_keyword_limit: int = 14
    rag_final_top_k: int = 10
    rag_neighbor_window: int = 1  # include ±N adjacent chunks around each hit
    rag_max_context_chunks: int = 24  # cap after neighbor expansion (avoid huge prompts)

    # Accuracy-oriented RAG (slower)
    rag_query_rewrite: bool = True
    rag_query_rewrite_max: int = 4
    rag_rrf_k: int = 60
    rag_rerank: bool = True
    rag_rerank_pool: int = 28  # candidates after RRF before LLM rerank

    # Long-document summarization / tagging (map-reduce & sampling)
    summarize_single_max_chars: int = 12000  # below this: one-shot summarize
    summarize_map_chunk_chars: int = 5500
    summarize_map_overlap: int = 400
    summarize_max_map_chunks: int = 32
    llm_num_ctx: int = 16384  # passed to Ollama for larger context windows

    tag_single_max_chars: int = 14000
    tag_sample_count: int = 10
    tag_sample_chars: int = 3200

    def resolved_sqlite_path(self) -> Path:
        return self.sqlite_path or (self.data_dir / "app.db")

    def resolved_uploads_dir(self) -> Path:
        return self.uploads_dir or (self.data_dir / "uploads")

    def resolved_chroma_dir(self) -> Path:
        return self.chroma_dir or (self.data_dir / "chroma")


settings = Settings()

