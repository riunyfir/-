from __future__ import annotations

from sqlmodel import Session

from ..llm.ollama_client import chat
from ..rag.retriever import retrieve
from ..rag.types import RetrievedChunk
from .schemas import AnswerOut
from .utils import parse_json_model


SYSTEM = """你是个人知识库问答助手。
你必须严格依据下面「上下文」中的内容作答；不要编造上下文中不存在的事实。
若上下文不足以回答，请明确说明「知识库中未找到直接依据」，并简要说明缺少什么信息或建议用户补充哪类文档。
回答语言尽量与用户问题一致（中文问题用中文答）。
输出必须是合法 JSON，不要 Markdown 代码块，不要多余说明。"""


def _format_context(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for c in chunks:
        src = getattr(c, "source", "vector")
        parts.append(
            f"[doc={c.document_id} chunk={c.chunk_id} idx={c.chunk_index} src={src}]\n{c.content}\n"
        )
    return "\n---\n".join(parts)


def answer_question(
    question: str,
    session: Session,
    document_id: str | None = None,
    tag: str | None = None,
) -> AnswerOut:
    uid = None if document_id is None else __import__("uuid").UUID(document_id)

    chunks = retrieve(
        query=question.strip(),
        document_id=uid,
        tag=tag,
        session=session,
    )

    if not chunks:
        return AnswerOut(
            answer="知识库中暂时没有找到与问题相关的片段。请先上传/处理文档，或尝试换一种问法（更具体的关键词）。",
            citations=[],
        )

    context = _format_context(chunks)
    user = {
        "role": "user",
        "content": (
            "请根据 CONTEXT 回答问题。\n"
            "输出 JSON，格式："
            '{"answer": string, "citations": ['
            '{"document_id": string, "chunk_id": string, "chunk_index": number, "quote": string}'
            "]}\n"
            "要求：\n"
            "- citations 中的 quote 必须是 CONTEXT 里出现的原文短句（不要改写）。\n"
            "- 若无法从 CONTEXT 可靠回答，answer 中说明原因，citations 可为空数组。\n\n"
            f"问题：\n{question}\n\n"
            f"CONTEXT：\n{context}\n"
        ),
    }
    raw = chat([{"role": "system", "content": SYSTEM}, user])
    return parse_json_model(raw, AnswerOut)
