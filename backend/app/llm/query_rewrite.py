from __future__ import annotations

import json

from pydantic import BaseModel, Field

from ..settings import settings
from .ollama_client import chat


class _RewriteOut(BaseModel):
    queries: list[str] = Field(default_factory=list)


SYSTEM = """你是检索助手。把用户问题改写成多条「检索式」，用于向量检索与全文检索。
要求：
- 保留原意，可补充同义词、相关术语、英文关键词（若原文有技术词）。
- 输出 2~4 条短句，每条独立一行语义，不要解释。
- 只输出 JSON：{"queries":["...","..."]}
"""


def expand_search_queries(question: str, max_queries: int = 4) -> list[str]:
    q = (question or "").strip()
    if not q:
        return []
    if not getattr(settings, "rag_query_rewrite", True):
        return [q]

    user = {
        "role": "user",
        "content": f"用户问题：\n{q}\n",
    }
    try:
        raw = chat([{"role": "system", "content": SYSTEM}, user])
        data = _RewriteOut.model_validate(json.loads(_extract_json(raw)))
        out = [x.strip() for x in data.queries if x and x.strip()]
        merged: list[str] = []
        for x in [q] + out:
            if x not in merged:
                merged.append(x)
        merged = merged[: max(1, max_queries)]
        return merged if merged else [q]
    except Exception:
        return [q]


def _extract_json(text: str) -> str:
    s = (text or "").strip()
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        return s[start : end + 1]
    return s
