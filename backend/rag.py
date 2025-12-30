"""
RAG Pipeline - Chunking, Embedding, Indexing, Retrieval
No LangChain - lightweight implementation
"""
import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import faiss


# Global model (loaded once)
_model = None


def get_model() -> SentenceTransformer:
    """Lazy load the embedding model"""
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Input text to chunk
        chunk_size: Target size of each chunk (characters)
        overlap: Number of overlapping characters between chunks
    
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            for sep in ['. ', '.\n', '! ', '? ', '\n\n']:
                last_sep = text[start:end].rfind(sep)
                if last_sep > chunk_size // 2:
                    end = start + last_sep + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
    
    return chunks


def create_embeddings(texts: List[str]) -> np.ndarray:
    """Generate embeddings for a list of texts"""
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.astype('float32')


def build_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """
    Build a FAISS index for similarity search.
    Uses Inner Product (cosine similarity after normalization).
    """
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Create index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    return index


def retrieve(
    query: str,
    index: faiss.IndexFlatIP,
    chunks: List[str],
    top_k: int = 3
) -> List[Dict]:
    """
    Retrieve most relevant chunks for a query.
    
    Returns:
        List of dicts with 'text' and 'score'
    """
    # Embed query
    query_embedding = create_embeddings([query])
    faiss.normalize_L2(query_embedding)
    
    # Search
    scores, indices = index.search(query_embedding, min(top_k, len(chunks)))
    
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0:  # Valid index
            results.append({
                "text": chunks[idx],
                "score": float(score)
            })
    
    return results


class RAGPipeline:
    """
    Complete RAG pipeline for a session.
    Manages documents, chunks, embeddings, and index.
    """
    
    def __init__(self):
        self.documents: List[Dict] = []  # {id, filename, type, text}
        self.chunks: List[str] = []
        self.chunk_sources: List[int] = []  # Which doc each chunk belongs to
        self.index: faiss.IndexFlatIP = None
    
    def add_document(self, doc_id: str, filename: str, file_type: str, text: str):
        """Add a document and rebuild index"""
        self.documents.append({
            "id": doc_id,
            "filename": filename,
            "type": file_type,
            "text": text
        })
        self._rebuild_index()
    
    def remove_document(self, doc_id: str) -> bool:
        """Remove a document and rebuild index"""
        initial_count = len(self.documents)
        self.documents = [d for d in self.documents if d["id"] != doc_id]
        
        if len(self.documents) < initial_count:
            self._rebuild_index()
            return True
        return False
    
    def _rebuild_index(self):
        """Rebuild chunks and index from all documents"""
        self.chunks = []
        self.chunk_sources = []
        
        for i, doc in enumerate(self.documents):
            doc_chunks = chunk_text(doc["text"])
            self.chunks.extend(doc_chunks)
            self.chunk_sources.extend([i] * len(doc_chunks))
        
        if self.chunks:
            embeddings = create_embeddings(self.chunks)
            self.index = build_index(embeddings)
        else:
            self.index = None
    
    def query(self, question: str, top_k: int = 3) -> List[Dict]:
        """
        Query the knowledge base.
        
        Returns:
            List of relevant chunks with source info
        """
        if not self.index or not self.chunks:
            return []
        
        results = retrieve(question, self.index, self.chunks, top_k)
        
        # Add source document info
        for i, result in enumerate(results):
            chunk_idx = self.chunks.index(result["text"])
            doc_idx = self.chunk_sources[chunk_idx]
            doc = self.documents[doc_idx]
            result["source"] = doc["filename"]
        
        return results
    
    def get_documents(self) -> List[Dict]:
        """Get list of documents (without full text)"""
        return [
            {"id": d["id"], "filename": d["filename"], "type": d["type"]}
            for d in self.documents
        ]
