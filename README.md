---
title: Portfolio Assistant
emoji: 🤖
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
license: mit
---

# 🤖 Portfolio Assistant

A lightweight RAG-powered chatbot that answers questions about your documents. Upload your resume, portfolio, or any documents and chat with them.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

## ✨ Features

- 📄 **Multi-format support** - PDF, DOCX, TXT, Markdown, JSON
- 🔍 **Semantic search** - Find relevant information using embeddings
- 💬 **Conversational AI** - Natural language Q&A powered by Groq
- 🌙 **Beautiful dark UI** - Animated star background
- 🔒 **Session-based** - Each user gets isolated storage
- ⚡ **No LangChain** - Lightweight, fast, minimal dependencies

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React + Vite Frontend                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ File Upload │  │    Chat     │  │  Star Background    │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘  │
└─────────┼────────────────┼──────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Session Manager                    │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │    │
│  │  │Session 1│  │Session 2│  │Session N│  (30m TTL)  │    │
│  │  └────┬────┘  └────┬────┘  └────┬────┘             │    │
│  └───────┼────────────┼────────────┼───────────────────┘    │
│          │            │            │                         │
│  ┌───────▼────────────▼────────────▼───────────────────┐    │
│  │              RAG Pipeline (per session)              │    │
│  │  ┌────────┐  ┌────────┐  ┌───────┐  ┌───────────┐  │    │
│  │  │ Loader │→ │Chunker │→ │Embed  │→ │FAISS Index│  │    │
│  │  └────────┘  └────────┘  └───────┘  └───────────┘  │    │
│  └──────────────────────────────────────────────────────┘    │
│                              │                               │
│                              ▼                               │
│                    ┌─────────────────┐                      │
│                    │    Groq LLM     │                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Groq API key ([get one free](https://console.groq.com))

### Local Development

```bash
# Clone the repo
git clone https://github.com/Saivineeth147/llm-testlab.git
cd llm-testlab/portfolio-assistant

# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Your Groq API key | Yes |

## 📁 Project Structure

```
portfolio-assistant/
├── README.md
├── Dockerfile
├── requirements.txt
├── backend/
│   ├── main.py          # FastAPI server + session management
│   ├── rag.py           # RAG pipeline (chunk, embed, retrieve)
│   └── loaders.py       # Document loaders (PDF, DOCX, TXT, MD, JSON)
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx      # Main chat + upload UI
        └── index.css    # Dark theme + animated stars
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/assistant/upload` | Upload documents |
| `POST` | `/assistant/chat` | Send message, get response |
| `GET` | `/assistant/documents` | List uploaded documents |
| `DELETE` | `/assistant/documents/{id}` | Remove a document |
| `DELETE` | `/assistant/session/end` | End session (cleanup) |

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 18 + Vite |
| Backend | FastAPI |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | FAISS (in-memory) |
| LLM | Groq (llama-3.3-70b-versatile) |
| Deployment | HuggingFace Spaces (Docker) |

## 📝 License

MIT License - feel free to use for your own portfolio!

---

<p align="center">
  Built with ❤️ by <a href="https://iamsaivineeth.com">Vineeth</a>
</p>
