"""
Portfolio Assistant - FastAPI Backend
Session-based RAG chatbot with multi-format document support
"""
import os
import uuid
import time
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

try:
    from loaders import load_document
    from rag import RAGPipeline
    from providers import fetch_models, generate as llm_generate
except ImportError:
    from backend.loaders import load_document
    from backend.rag import RAGPipeline
    from backend.providers import fetch_models, generate as llm_generate


# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

SESSION_TTL_MINUTES = 30
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".json"}
MAX_FILE_SIZE_MB = 10

app = FastAPI(
    title="Portfolio Assistant",
    description="RAG-powered document chatbot",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# Session Management
# ═══════════════════════════════════════════════════════════════════════════

class Session:
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.last_active = datetime.now()
        self.messages: List[Dict] = []  # Conversation history


sessions: Dict[str, Session] = {}


def get_session(session_id: str) -> Session:
    """Get or create a session"""
    if session_id not in sessions:
        sessions[session_id] = Session()
    
    session = sessions[session_id]
    session.last_active = datetime.now()
    return session


def cleanup_sessions():
    """Remove expired sessions"""
    cutoff = datetime.now() - timedelta(minutes=SESSION_TTL_MINUTES)
    expired = [sid for sid, s in sessions.items() if s.last_active < cutoff]
    for sid in expired:
        del sessions[sid]


# ═══════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    provider: str = "groq"  # "groq" or "huggingface"
    model: Optional[str] = None  # Model ID (uses default if not specified)
    api_key: Optional[str] = None  # Client-provided API key


class ModelsRequest(BaseModel):
    provider: str
    api_key: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict]


class DocumentResponse(BaseModel):
    id: str
    filename: str
    type: str


# ═══════════════════════════════════════════════════════════════════════════
# LLM Integration
# ═══════════════════════════════════════════════════════════════════════════

def build_prompt(question: str, context: List[Dict], history: List[Dict]) -> tuple:
    """Build system and user prompts for LLM"""
    context_text = "\n\n".join([
        f"[Source: {c['source']}]\n{c['text']}" 
        for c in context
    ]) if context else "No documents uploaded yet."
    
    history_text = "\n".join([
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in history[-6:]
    ]) if history else ""
    
    system_prompt = """You are a helpful AI assistant that answers questions based on the provided documents.
Rules:
- Only use information from the provided context
- If the answer isn't in the context, say "I don't have that information in the uploaded documents"
- Be concise and helpful
- Cite sources when possible"""

    user_prompt = f"""Context from documents:
{context_text}

{f"Previous conversation:{chr(10)}{history_text}{chr(10)}{chr(10)}" if history_text else ""}Question: {question}

Answer based on the context above:"""

    return system_prompt, user_prompt


def generate_answer(question: str, context: List[Dict], history: List[Dict], 
                   provider: str = "groq", model: str = None, api_key: str = None) -> str:
    """Generate answer using selected provider and model"""
    # Get API key from env if not provided
    if not api_key:
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
        else:
            api_key = os.getenv("HF_API_KEY")
    
    if not api_key:
        return f"⚠️ {provider.title()} API key not provided. Please enter your API key."
    
    # Set default models
    if not model:
        model = "llama-3.3-70b-versatile" if provider == "groq" else "meta-llama/Llama-3.2-3B-Instruct"
    
    system_prompt, user_prompt = build_prompt(question, context, history)
    
    try:
        return llm_generate(
            provider=provider,
            prompt=user_prompt,
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            max_tokens=1024
        )
    except Exception as e:
        return f"Error with {provider}: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/assistant/health")
def health_check():
    """Health check endpoint"""
    cleanup_sessions()  # Cleanup on health check
    return {"status": "healthy", "active_sessions": len(sessions)}


@app.post("/assistant/models")
def get_models(request: ModelsRequest):
    """Fetch available models for a provider"""
    try:
        models = fetch_models(request.provider, request.api_key)
        return {"provider": request.provider, "models": models}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/assistant/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    x_session_id: str = Header(alias="X-Session-ID")
):
    """Upload a document to the session"""
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max size: {MAX_FILE_SIZE_MB}MB")
    
    # Save to temp file and process
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        text, _ = load_document(tmp_path, ext[1:])  # Remove leading dot
        
        # Add to session
        session = get_session(x_session_id)
        doc_id = str(uuid.uuid4())[:8]
        session.pipeline.add_document(doc_id, file.filename, ext[1:], text)
        
        return DocumentResponse(id=doc_id, filename=file.filename, type=ext[1:])
    
    finally:
        os.unlink(tmp_path)  # Cleanup temp file


@app.get("/assistant/documents", response_model=List[DocumentResponse])
def list_documents(x_session_id: str = Header(alias="X-Session-ID")):
    """List documents in the session"""
    session = get_session(x_session_id)
    return [
        DocumentResponse(**doc) 
        for doc in session.pipeline.get_documents()
    ]


@app.delete("/assistant/documents/{doc_id}")
def delete_document(doc_id: str, x_session_id: str = Header(alias="X-Session-ID")):
    """Remove a document from the session"""
    session = get_session(x_session_id)
    if session.pipeline.remove_document(doc_id):
        return {"status": "deleted", "id": doc_id}
    raise HTTPException(status_code=404, detail="Document not found")


@app.post("/assistant/chat", response_model=ChatResponse)
def chat(request: ChatRequest, x_session_id: str = Header(alias="X-Session-ID")):
    """Chat with the documents"""
    session = get_session(x_session_id)
    
    # Retrieve relevant context
    context = session.pipeline.query(request.message, top_k=3)
    
    # Generate answer
    answer = generate_answer(request.message, context, session.messages, request.provider, request.model, request.api_key)
    
    # Update conversation history
    session.messages.append({"role": "user", "content": request.message})
    session.messages.append({"role": "assistant", "content": answer})
    
    return ChatResponse(answer=answer, sources=context)


@app.post("/assistant/session/end")
def end_session(x_session_id: str = Header(alias="X-Session-ID")):
    """Explicitly end a session"""
    if x_session_id in sessions:
        del sessions[x_session_id]
        return {"status": "session ended"}
    return {"status": "session not found"}


# ═══════════════════════════════════════════════════════════════════════════
# Static Files (for production)
# ═══════════════════════════════════════════════════════════════════════════

# Serve frontend build
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")
    
    @app.get("/")
    def serve_frontend():
        return FileResponse(frontend_path / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
