from __future__ import annotations

from pydantic import BaseModel, Field

from ..ingest.chunker import chunk_text
from ..llm.ollama_client import chat
from ..settings import settings
from .schemas import SummaryOut
from .utils import parse_json_model


SYSTEM = """You are a helpful personal knowledge assistant.
Return ONLY valid JSON, no markdown, no extra text."""

SYSTEM_MAP = """你是文档分段摘要助手。只输出合法 JSON，不要 Markdown 代码块，不要多余文字。"""


class _MapPart(BaseModel):
    note: str = Field(default="", description="该段 1-2 句概括")
    points: list[str] = Field(default_factory=list, description="该段要点，3-6 条")


def _summarize_one(text: str) -> SummaryOut:
    prompt = {
        "role": "user",
        "content": (
            "Summarize the document.\n\n"
            "Output JSON with keys:\n"
            "- short_summary: string\n"
            "- bullets: string[] (3-8 items)\n"
            "- outline_md: string (markdown outline, start with '# Title' then '##' subsections and '-' bullets)\n\n"
            f"DOCUMENT:\n{text}\n"
        ),
    }
    raw = chat(
        [{"role": "system", "content": SYSTEM}, prompt],
        num_ctx=settings.llm_num_ctx,
    )
    return parse_json_model(raw, SummaryOut)


def _map_part(text: str, index: int, total: int) -> str:
    prompt = {
        "role": "user",
        "content": (
            f"这是长文档的第 {index}/{total} 段。请阅读并输出 JSON：\n"
            '{{"note": "一两句概括", "points": ["要点1", "要点2", ...]}}\n'
            "要点使用与原文相同的语言（中文则中文）。\n\n"
            f"段落内容：\n{text}\n"
        ),
    }
    raw = chat(
        [{"role": "system", "content": SYSTEM_MAP}, prompt],
        num_ctx=min(settings.llm_num_ctx, 8192),
    )
    try:
        data = _MapPart.model_validate_json(_json_object(raw))
        bits = [data.note.strip()] if data.note.strip() else []
        bits.extend([p.strip() for p in data.points if p and str(p).strip()])
        return "\n".join(bits)
    except Exception:
        return (text or "")[:1200]


def _json_object(raw: str) -> str:
    s = (raw or "").strip()
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        return s[a : b + 1]
    return s


def _reduce_map_notes(parts: list[str]) -> SummaryOut:
    bundle = "\n\n---\n\n".join(f"### 分段摘要 {i+1}\n{p}" for i, p in enumerate(parts) if p.strip())
    # 二次压缩：仍过长则隔段合并
    while len(bundle) > 18000 and len(parts) > 4:
        merged: list[str] = []
        for i in range(0, len(parts), 2):
            merged.append(parts[i] if i + 1 >= len(parts) else parts[i] + "\n" + parts[i + 1])
        parts = merged
        bundle = "\n\n---\n\n".join(f"### 分段摘要 {i+1}\n{p}" for i, p in enumerate(parts) if p.strip())

    prompt = {
        "role": "user",
        "content": (
            "下面是一篇长文档的分段摘要与要点，请整合为一份完整输出。\n"
            "Output JSON with keys:\n"
            "- short_summary: string（全文 2-4 句总述）\n"
            "- bullets: string[]（8-15 条全局要点，去重合并）\n"
            "- outline_md: string（Markdown 大纲：'# 标题'、'##' 小节、'-' 要点）\n\n"
            f"分段材料：\n{bundle}\n"
        ),
    }
    raw = chat(
        [{"role": "system", "content": SYSTEM}, prompt],
        num_ctx=settings.llm_num_ctx,
    )
    return parse_json_model(raw, SummaryOut)


def summarize(text: str) -> SummaryOut:
    """
    短文档一次总结；长文档自动 map-reduce，避免超出上下文导致失败。
    """
    t = (text or "").strip()
    if not t:
        return SummaryOut(short_summary="", bullets=[], outline_md="# 空文档\n")

    if len(t) <= settings.summarize_single_max_chars:
        return _summarize_one(t)

    tc = chunk_text(
        t,
        max_chars=settings.summarize_map_chunk_chars,
        overlap=settings.summarize_map_overlap,
    )
    parts_in = [c.content for c in tc[: settings.summarize_max_map_chunks]]
    if not parts_in:
        return _summarize_one(t[: settings.summarize_single_max_chars])

    mapped: list[str] = []
    total = len(parts_in)
    for i, p in enumerate(parts_in):
        mapped.append(_map_part(p, i + 1, total))

    return _reduce_map_notes(mapped)
