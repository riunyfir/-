from __future__ import annotations

import json
import re

from ..llm.ollama_client import chat
from ..settings import settings
from .types import RetrievedChunk


SYSTEM = """你是排序助手。根据用户问题，给候选段落按相关性从高到低排序。
只输出 JSON：{"order":[整数下标,...]}，下标从 0 开始，对应候选列表顺序。
不要输出任何解释。"""


def llm_rerank(
    question: str,
    candidates: list[RetrievedChunk],
    *,
    top_n: int,
) -> list[RetrievedChunk]:
    if not candidates:
        return []
    if len(candidates) <= top_n:
        return candidates
    if not getattr(settings, "rag_rerank", True):
        return candidates[:top_n]

    lines: list[str] = []
    for i, c in enumerate(candidates):
        snippet = (c.content or "").strip().replace("\n", " ")
        if len(snippet) > 420:
            snippet = snippet[:420] + "…"
        lines.append(f"[{i}] doc={c.document_id} chunk={c.chunk_id} idx={c.chunk_index}\n{snippet}")

    user = {
        "role": "user",
        "content": "问题：\n"
        f"{question}\n\n"
        "候选段落：\n"
        + "\n\n".join(lines)
        + f"\n\n请输出 JSON，保留最相关的 {top_n} 个下标（order 数组长度={top_n}）。",
    }
    raw = chat([{"role": "system", "content": SYSTEM}, user])
    order = _parse_order(raw, len(candidates))
    if not order:
        return candidates[:top_n]

    seen: set[int] = set()
    out: list[RetrievedChunk] = []
    for idx in order:
        if 0 <= idx < len(candidates) and idx not in seen:
            seen.add(idx)
            out.append(candidates[idx])
        if len(out) >= top_n:
            break
    # fill if model too short
    for i, c in enumerate(candidates):
        if len(out) >= top_n:
            break
        if i not in seen:
            out.append(c)
    return out[:top_n]


def _parse_order(raw: str, n: int) -> list[int]:
    s = (raw or "").strip()
    m = re.search(r"\{[\s\S]*\}", s)
    if m:
        s = m.group(0)
    try:
        data = json.loads(s)
        arr = data.get("order") if isinstance(data, dict) else None
        if isinstance(arr, list):
            out: list[int] = []
            for x in arr:
                if isinstance(x, int):
                    out.append(x)
                elif isinstance(x, str) and x.isdigit():
                    out.append(int(x))
            return [i for i in out if 0 <= i < n]
    except Exception:
        pass
    return []
