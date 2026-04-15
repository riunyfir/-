import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listDocuments, processDocument, uploadFile, type DocumentItem } from '../lib/api'

function bytes(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export function LibraryPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [q, setQ] = useState('')
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return docs
    return docs.filter((d) => d.filename.toLowerCase().includes(s))
  }, [docs, q])

  async function refresh() {
    setLoading(true)
    try {
      setDocs(await listDocuments())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function onUpload(file: File) {
    setLoading(true)
    try {
      const up = await uploadFile(file)
      await processDocument(up.document_id)
      await refresh()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-xl border bg-white p-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-lg font-semibold">文库</div>
          <div className="text-sm text-slate-600">上传文档后会自动解析与切块（向量索引/问答稍后可用）</div>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜索文件名…"
            className="w-56 rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200"
          />
          <label className="cursor-pointer rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            上传
            <input
              type="file"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) void onUpload(f)
                e.currentTarget.value = ''
              }}
            />
          </label>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border bg-white">
        <div className="grid grid-cols-12 border-b bg-slate-50 px-4 py-2 text-xs font-semibold text-slate-600">
          <div className="col-span-6">文件</div>
          <div className="col-span-2">大小</div>
          <div className="col-span-2">状态</div>
          <div className="col-span-2">创建时间</div>
        </div>
        {loading && <div className="px-4 py-3 text-sm text-slate-600">加载中…</div>}
        {!loading && filtered.length === 0 && <div className="px-4 py-3 text-sm text-slate-600">暂无文档</div>}
        {filtered.map((d) => (
          <Link
            key={d.id}
            to={`/doc/${d.id}`}
            className="grid grid-cols-12 items-center px-4 py-3 text-sm hover:bg-slate-50"
          >
            <div className="col-span-6 truncate font-medium">{d.filename}</div>
            <div className="col-span-2 text-slate-600">{bytes(d.size_bytes)}</div>
            <div className="col-span-2">
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{d.status}</span>
            </div>
            <div className="col-span-2 text-xs text-slate-600">{new Date(d.created_at).toLocaleString()}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}

