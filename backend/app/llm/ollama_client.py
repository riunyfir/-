from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Sequence

import ollama

from ..settings import settings


@lru_cache(maxsize=1)
def _client() -> ollama.Client:
    return ollama.Client(host=settings.ollama_host)


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    resp = _client().embed(model=settings.embed_model, input=list(texts))
    # ollama.EmbedResponse: embeddings: List[List[float]]
    return list(resp.embeddings)


def chat(messages: list[dict]) -> str:
    resp = _client().chat(model=settings.llm_model, messages=messages)
    return resp.message.content

