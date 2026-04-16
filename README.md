# PKM 智能助手（本地离线）

上传文档 → 自动总结 → 智能问答（RAG） → 生成思维导图。

## 先决条件

- Windows 10/11
- Python 3.10+
- Node.js 18+
- 已安装并启动 [Ollama](https://ollama.com/)

建议拉取模型（可按需替换）：

```bash
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

## 一键启动（开发）

### 后端

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-vector.txt
python -m uvicorn app.main:app --reload --port 8000
```

后端启动后访问：`http://127.0.0.1:8000/docs`

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认：`http://127.0.0.1:5173`

## 数据落地

- SQLite：`data/app.db`
- 上传文件：`data/uploads/`
- 向量库（Chroma）：`data/chroma/`

## 问答（RAG）说明

- 检索为 **查询改写（LLM）→ 多路召回 → RRF 融合 → LLM 重排 → 邻块扩展**：
  - **向量**：Chroma + 多条改写查询
  - **全文**：SQLite **FTS5**（优先 `trigram`，失败则 `unicode61`）BM25
  - **词面**：字符/n-gram 重叠兜底
- 若升级了切块/检索参数，需对旧文档 **重新处理** 以重建切块、FTS 与向量：调用 `POST /api/documents/{id}/process`。
- 可通过环境变量 `PKM_` 前缀调整（见 `backend/app/settings.py`），例如 `PKM_RAG_FINAL_TOP_K`、`PKM_RAG_QUERY_REWRITE`、`PKM_RAG_RERANK`、`PKM_CHUNK_MAX_CHARS`。
- **长文档**：自动总结使用 **map-reduce** 分段摘要再合并；标签优先基于已切分的 **chunk 均匀抽样**，避免一次性塞满上下文导致失败。可用 `PKM_SUMMARIZE_SINGLE_MAX_CHARS`、`PKM_LLM_NUM_CTX` 等调节。

## 后台任务与进度

- 解析/向量化：`POST /api/documents/{id}/process-async` → 返回 `job_id`，轮询 `GET /api/jobs/{job_id}`（含 `progress`、`message`、`status`）。
- 总结：`POST /api/documents/{id}/summarize-async`；标签：`POST /api/documents/{id}/tag-async`。
- 某文档历史任务：`GET /api/documents/{id}/jobs`。
- 任务状态存于 SQLite 表 `background_jobs`；实现为 FastAPI **BackgroundTasks**（单进程内异步，适合作业/演示；多进程部署可换 Celery/RQ）。

