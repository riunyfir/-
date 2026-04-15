from __future__ import annotations

from functools import lru_cache

from ..settings import settings


@lru_cache(maxsize=1)
def get_chroma_collection():
    """
    Lazily create a persistent Chroma collection.
    """
    import chromadb  # type: ignore

    client = chromadb.PersistentClient(path=str(settings.resolved_chroma_dir()))
    # Default HNSW space in Chroma is cosine for many embeddings; keep defaults for MVP.
    return client.get_or_create_collection(name="chunks")

