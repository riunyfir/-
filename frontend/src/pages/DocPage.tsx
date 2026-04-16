import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Mindmap } from '../components/Mindmap'
import { getMindmap, pollJob, summarizeDocumentAsync, tagDocumentAsync, type JobStatus } from '../lib/api'

export function DocPage() {
  const { id } = useParams()
  const docId = id ?? ''
  const [summary, setSummary] = useState<any | null>(null)
  const [tags, setTags] = useState<any | null>(null)
  const [outline, setOutline] = useState<string>('# 加载中…')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [progress, setProgress] = useState<{ pct: number; msg: string } | null>(null)

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

  function onJobProgress(j: JobStatus) {
    setProgress({ pct: j.progress, msg: j.message })
  }

  async function doSummarize() {
    if (!docId) return
    setBusy(true)
    setErr(null)
    setProgress({ pct: 0, msg: '排队中…' })
    try {
      const { job_id } = await summarizeDocumentAsync(docId)
      const done = await pollJob(job_id, onJobProgress)
      if (done.status === 'failed') {
        throw new Error(done.error || '总结失败')
      }
      const res = done.result as any
      setSummary(res)
      if (res?.outline_md) setOutline(res.outline_md)
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
      setProgress(null)
    }
  }

  async function doTag() {
    if (!docId) return
    setBusy(true)
    setErr(null)
    setProgress({ pct: 0, msg: '排队中…' })
    try {
      const { job_id } = await tagDocumentAsync(docId)
      const done = await pollJob(job_id, onJobProgress)
      if (done.status === 'failed') {
        throw new Error(done.error || '打标签失败')
      }
      setTags(done.result)
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
      setProgress(null)
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

        {progress && (
          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs text-slate-600">
              <span>{progress.msg}</span>
              <span>{progress.pct}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all duration-300"
                style={{ width: `${Math.min(100, Math.max(0, progress.pct))}%` }}
              />
            </div>
          </div>
        )}

        {err && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{err}</div>}

        {summary && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border bg-slate-50 p-3">
              <div className="text-sm font-semibold">摘要</div>
              <div className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{summary.short_summary}</div>
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
                <span
                  key={t.id ?? t.name}
                  className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700"
                >
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
