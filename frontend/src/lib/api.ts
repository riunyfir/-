export type DocumentItem = {
  id: string
  filename: string
  mime_type: string
  size_bytes: number
  created_at: string
  status: string
  text_chars: number
}

export type JobStatus = {
  id: string
  job_type: string
  document_id: string
  status: string
  progress: number
  message: string
  error?: string | null
  result?: unknown
  created_at: string
  updated_at: string
}

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api'

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    const txt = await res.text().catch(() => '')
    throw new Error(txt || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}

export async function listDocuments(): Promise<DocumentItem[]> {
  return http<DocumentItem[]>('/documents')
}

export async function uploadFile(file: File): Promise<{ document_id: string; deduped: boolean }> {
  const fd = new FormData()
  fd.append('file', file)
  return http('/files', { method: 'POST', body: fd })
}

export async function processDocument(id: string): Promise<any> {
  return http(`/documents/${id}/process`, { method: 'POST' })
}

export async function processDocumentAsync(id: string): Promise<{ job_id: string; status: string; message: string }> {
  return http(`/documents/${id}/process-async`, { method: 'POST' })
}

export async function getJob(jobId: string): Promise<JobStatus> {
  return http<JobStatus>(`/jobs/${jobId}`)
}

export async function pollJob(
  jobId: string,
  onProgress?: (j: JobStatus) => void,
  intervalMs = 400,
  maxWaitMs = 30 * 60 * 1000,
): Promise<JobStatus> {
  const start = Date.now()
  for (;;) {
    if (Date.now() - start > maxWaitMs) {
      throw new Error('任务等待超时，请稍后到文档详情重试或查看后端日志')
    }
    const j = await getJob(jobId)
    onProgress?.(j)
    if (j.status === 'succeeded' || j.status === 'failed') {
      return j
    }
    await new Promise((r) => setTimeout(r, intervalMs))
  }
}

export async function summarizeDocument(id: string): Promise<any> {
  return http(`/documents/${id}/summarize`, { method: 'POST' })
}

export async function summarizeDocumentAsync(id: string): Promise<{ job_id: string; status: string; message: string }> {
  return http(`/documents/${id}/summarize-async`, { method: 'POST' })
}

export async function tagDocument(id: string): Promise<any> {
  return http(`/documents/${id}/tag`, { method: 'POST' })
}

export async function tagDocumentAsync(id: string): Promise<{ job_id: string; status: string; message: string }> {
  return http(`/documents/${id}/tag-async`, { method: 'POST' })
}

export async function getMindmap(id: string): Promise<{ outline_md: string }> {
  return http(`/documents/${id}/mindmap`)
}

export async function chat(
  question: string,
  scope: 'all' | 'document' | 'tag',
  document_id?: string,
  tag?: string,
  session_id?: string,
) {
  return http<{ answer: string; citations: any[]; session_id: string }>('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, scope, document_id, tag, session_id }),
  })
}
