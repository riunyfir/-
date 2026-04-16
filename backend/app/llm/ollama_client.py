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


def chat(messages: list[dict], *, num_ctx: int | None = None) -> str:
    opts: dict[str, int] = {}
    if num_ctx is not None and num_ctx > 0:
        opts["num_ctx"] = int(num_ctx)
    kwargs: dict = {"model": settings.llm_model, "messages": messages}
    if opts:
        kwargs["options"] = opts
    resp = _client().chat(**kwargs)
    return resp.message.content

