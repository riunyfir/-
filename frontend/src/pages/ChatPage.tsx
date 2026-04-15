import { useState } from 'react'
import { chat } from '../lib/api'

type Msg = { role: 'user' | 'assistant'; content: string; citations?: any[] }

export function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)

  async function send() {
    const question = q.trim()
    if (!question || busy) return
    setErr(null)
    setBusy(true)
    setMessages((m) => [...m, { role: 'user', content: question }])
    setQ('')
    try {
      const res = await chat(question, 'all', undefined, undefined, sessionId ?? undefined)
      if (res.session_id) setSessionId(res.session_id)
      setMessages((m) => [...m, { role: 'assistant', content: res.answer, citations: res.citations ?? [] }])
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-white p-4">
        <div className="text-lg font-semibold">智能问答</div>
        <div className="mt-1 text-sm text-slate-600">当前为全库问答（需要文档已建立向量索引）</div>
        {sessionId && <div className="mt-1 text-xs text-slate-500">session: {sessionId}</div>}
      </div>

      <div className="rounded-xl border bg-white">
        <div className="max-h-[520px] space-y-3 overflow-auto p-4">
          {messages.length === 0 && <div className="text-sm text-slate-600">输入问题开始对话。</div>}
          {messages.map((m, i) => (
            <div key={i} className={m.role === 'user' ? 'ml-auto max-w-[85%]' : 'mr-auto max-w-[85%]'}>
              <div
                className={
                  m.role === 'user'
                    ? 'rounded-2xl bg-indigo-600 px-4 py-2 text-sm text-white'
                    : 'rounded-2xl bg-slate-100 px-4 py-2 text-sm text-slate-900'
                }
              >
                <div className="whitespace-pre-wrap">{m.content}</div>
              </div>
              {m.role === 'assistant' && (m.citations?.length ?? 0) > 0 && (
                <details className="mt-2 text-xs text-slate-600">
                  <summary className="cursor-pointer select-none">引用</summary>
                  <div className="mt-2 space-y-2">
                    {(m.citations ?? []).map((c: any, idx: number) => (
                      <div key={idx} className="rounded-lg border bg-white p-2">
                        <div className="font-mono text-[11px] text-slate-500">
                          doc={c.document_id} chunk={c.chunk_id} idx={c.chunk_index}
                        </div>
                        <div className="mt-1 whitespace-pre-wrap">{c.quote}</div>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))}
        </div>

        {err && <div className="border-t bg-red-50 px-4 py-2 text-sm text-red-700">{err}</div>}

        <div className="flex items-center gap-2 border-t p-3">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void send()
            }}
            placeholder="输入你的问题…"
            className="flex-1 rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200"
          />
          <button
            disabled={busy}
            onClick={() => void send()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}

