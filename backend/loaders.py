"""
Document Loaders - Extract text from various file formats
"""
import json
from pathlib import Path
from typing import Tuple

import fitz  # PyMuPDF
from docx import Document


def load_document(file_path: str, file_type: str) -> Tuple[str, dict]:
    """
    Load document and extract text based on file type.
    Returns (text, metadata)
    """
    path = Path(file_path)
    metadata = {"filename": path.name, "type": file_type}
    
    loaders = {
        "pdf": load_pdf,
        "docx": load_docx,
        "txt": load_txt,
        "md": load_txt,  # Same as txt
        "json": load_json,
    }
    
    loader = loaders.get(file_type.lower())
    if not loader:
        raise ValueError(f"Unsupported file type: {file_type}")
    
    text = loader(file_path)
    return text, metadata


def load_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF"""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


def load_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx"""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def load_txt(file_path: str) -> str:
    """Read plain text or markdown file"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_json(file_path: str) -> str:
    """Extract text from JSON - concatenates all string values"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    def extract_strings(obj, texts=None):
        if texts is None:
            texts = []
        if isinstance(obj, str):
            texts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                extract_strings(v, texts)
        elif isinstance(obj, list):
            for item in obj:
                extract_strings(item, texts)
        return texts
    
    strings = extract_strings(data)
    return "\n".join(strings)
