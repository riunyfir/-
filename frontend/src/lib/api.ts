export type DocumentItem = {
  id: string
  filename: string
  mime_type: string
  size_bytes: number
  created_at: string
  status: string
  text_chars: number
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

export async function summarizeDocument(id: string): Promise<any> {
  return http(`/documents/${id}/summarize`, { method: 'POST' })
}

export async function tagDocument(id: string): Promise<any> {
  return http(`/documents/${id}/tag`, { method: 'POST' })
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

