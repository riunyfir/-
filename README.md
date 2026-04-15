# 个人知识管理智能助手

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
