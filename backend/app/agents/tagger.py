from __future__ import annotations

from ..llm.ollama_client import chat
from ..settings import settings
from .schemas import TagsOut
from .utils import parse_json_model


SYSTEM = """You are a personal knowledge assistant.
Return ONLY valid JSON, no markdown, no extra text."""


def _even_sample_strings(lines: list[str], k: int) -> list[str]:
    lines = [x.strip() for x in lines if x and x.strip()]
    if not lines:
        return []
    if len(lines) <= k:
        return lines
    out: list[str] = []
    for i in range(k):
        idx = int(i * (len(lines) - 1) / max(1, k - 1))
        out.append(lines[idx])
    return out


def _sample_windows(text: str, n: int, w: int) -> list[str]:
    t = (text or "").strip()
    if not t:
        return []
    if len(t) <= w:
        return [t]
    n = max(3, n)
    starts: list[int] = []
    span = max(0, len(t) - w)
    for i in range(n):
        starts.append((span * i) // max(1, n - 1) if n > 1 else 0)
    seen: set[int] = set()
    out: list[str] = []
    for s in sorted(set(starts)):
        if s in seen:
            continue
        seen.add(s)
        out.append(t[s : s + w])
    return out


def tag_document(
    text: str,
    max_tags: int = 8,
    *,
    chunk_contents: list[str] | None = None,
) -> TagsOut:
    """
    短文档：全文打标签。
    长文档：优先用已切分的 chunk 均匀抽样；否则对全文做窗口抽样，避免超出模型上下文导致失败。
    """
    bundle: str
    if chunk_contents and len(chunk_contents) > 0:
        sampled = _even_sample_strings(chunk_contents, settings.tag_sample_count)
        bundle = "\n\n--- CHUNK ---\n\n".join(sampled)
    else:
        t = (text or "").strip()
        if len(t) <= settings.tag_single_max_chars:
            bundle = t
        else:
            wins = _sample_windows(t, settings.tag_sample_count, settings.tag_sample_chars)
            bundle = "\n\n--- SAMPLE ---\n\n".join(wins)

    cap = settings.tag_single_max_chars * 2
    if len(bundle) > cap:
        bundle = bundle[:cap]

    prompt = {
        "role": "user",
        "content": (
            "Generate topical tags for this document (the text may be excerpts from a long document).\n"
            f'Return JSON: {{"tags": [{{"name": string, "score": number}}...]}}.\n'
            f"Rules: 3 to {max_tags} tags, short names (1-4 words), score in [0,1].\n\n"
            f"DOCUMENT EXCERPTS:\n{bundle}\n"
        ),
    }
    raw = chat(
        [{"role": "system", "content": SYSTEM}, prompt],
        num_ctx=settings.llm_num_ctx,
    )
    return parse_json_model(raw, TagsOut)
