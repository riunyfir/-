import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Mindmap } from '../components/Mindmap'
import { getMindmap, summarizeDocument, tagDocument } from '../lib/api'

export function DocPage() {
  const { id } = useParams()
  const docId = id ?? ''
  const [summary, setSummary] = useState<any | null>(null)
  const [tags, setTags] = useState<any | null>(null)
  const [outline, setOutline] = useState<string>('# 加载中…')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!docId) return
    setErr(null)
    void (async () => {
      try {
        const mm = await getMindmap(docId)
        setOutline(mm.outline_md)
      } catch (e: any) {
        setErr(e?.message ?? String(e))
      }
    })()
  }, [docId])

  async function doSummarize() {
    if (!docId) return
    setBusy(true)
    setErr(null)
    try {
      const s = await summarizeDocument(docId)
      setSummary(s)
      if (s?.outline_md) setOutline(s.outline_md)
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
    }
  }

  async function doTag() {
    if (!docId) return
    setBusy(true)
    setErr(null)
    try {
      setTags(await tagDocument(docId))
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-lg font-semibold">文档详情</div>
          <div className="flex gap-2">
            <button
              disabled={busy}
              onClick={() => void doSummarize()}
              className="rounded-lg border px-3 py-2 text-sm font-semibold hover:bg-slate-50 disabled:opacity-60"
            >
              自动总结
            </button>
            <button
              disabled={busy}
              onClick={() => void doTag()}
              className="rounded-lg border px-3 py-2 text-sm font-semibold hover:bg-slate-50 disabled:opacity-60"
            >
              生成标签
            </button>
          </div>
        </div>

        {err && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{err}</div>}

        {summary && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border bg-slate-50 p-3">
              <div className="text-sm font-semibold">摘要</div>
              <div className="mt-2 text-sm text-slate-700 whitespace-pre-wrap">{summary.short_summary}</div>
            </div>
            <div className="rounded-lg border bg-slate-50 p-3">
              <div className="text-sm font-semibold">要点</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {(summary.bullets ?? []).map((b: string, i: number) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {tags?.tags?.length > 0 && (
          <div className="mt-4">
            <div className="text-sm font-semibold">标签</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {tags.tags.map((t: any) => (
                <span key={t.id ?? t.name} className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
                  {t.name}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="rounded-xl border bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold">思维导图</div>
          <div className="text-xs text-slate-500">基于 outline_md（markmap）渲染</div>
        </div>
        <Mindmap markdown={outline} />
      </div>
    </div>
  )
}

