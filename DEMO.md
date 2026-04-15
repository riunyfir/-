# 演示流程（建议按此顺序录屏/验收）

## 0. 启动

### 0.1 启动 Ollama（本地大模型）

确保 Ollama 在后台运行，并拉取模型：

```bash
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

### 0.2 启动后端

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-vector.txt
python -m uvicorn app.main:app --port 8000
```

打开 API 文档：`http://127.0.0.1:8000/docs`

### 0.3 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开前端：`http://127.0.0.1:5173`

## 1. 上传文件 → 自动解析/向量化

在「文库」页面点击 **上传**，选择 `sample.md` 或你自己的 `txt/md/pdf/docx`。\n\n上传后系统会调用：\n- `POST /api/files`（保存原始文件 + 元数据入库）\n- `POST /api/documents/{id}/process`（抽取文本 → 切块 → 写入 SQLite；并尝试向量索引）\n\n如果 Ollama 未运行，`process` 返回里会包含 `indexing_error`；Ollama 正常时会看到 `status=indexed`。\n\n## 2. 自动总结\n\n进入文档详情页点击 **自动总结**，对应：\n- `POST /api/documents/{id}/summarize`\n\n会得到：\n- `short_summary`\n- `bullets[]`\n- `outline_md`（用于思维导图渲染）\n\n## 3. 标签分类\n\n点击 **生成标签**，对应：\n- `POST /api/documents/{id}/tag`\n\n标签会写入 SQLite（`tags` / `document_tags`）。\n\n## 4. 智能问答（RAG）\n\n打开「问答」页面，输入问题。\n\n后端流程：\n- 使用 `nomic-embed-text` 生成 query embedding\n- Chroma 检索 topK chunks\n- 将检索到的 chunks 拼接为上下文\n- 使用 `qwen2.5:7b-instruct` 生成 **带引用** 的回答（JSON）\n\n前端会展示回答，并可展开查看引用片段。\n\n## 5. 生成思维导图\n\n文档详情页「思维导图」区域使用 `markmap` 渲染 `outline_md`。\n\n如果没有摘要，后端会调用 `GET /api/documents/{id}/mindmap` 直接从全文生成 outline。\n+