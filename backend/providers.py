"""
LLM Provider Adapters with Dynamic Model Fetching
Supports: Groq, HuggingFace
"""
import os
import logging
import requests
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# Cache for fetched models
_model_cache = {}


# ═══════════════════════════════════════════════════════════════════════════
# Groq Provider
# ═══════════════════════════════════════════════════════════════════════════

GROQ_FALLBACK_MODELS = [
    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B Versatile"},
    {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant"},
    {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
    {"id": "gemma2-9b-it", "name": "Gemma 2 9B IT"},
]


def fetch_groq_models(api_key: str) -> List[Dict]:
    """Fetch available models from Groq API."""
    if not api_key:
        return GROQ_FALLBACK_MODELS
    
    cache_key = f"groq_{api_key[:8]}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]
    
    try:
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        models = []
        for model in data.get("data", []):
            model_id = model.get("id", "")
            # Skip audio models
            if "whisper" in model_id.lower() or "tts" in model_id.lower():
                continue
            models.append({
                "id": model_id,
                "name": model_id.replace("-", " ").title()
            })
        
        models.sort(key=lambda x: x["name"])
        _model_cache[cache_key] = models
        return models
        
    except Exception as e:
        logger.warning(f"Failed to fetch Groq models: {e}")
        return GROQ_FALLBACK_MODELS


def generate_groq(prompt: str, api_key: str, model: str = "llama-3.3-70b-versatile", 
                  system_prompt: str = "", max_tokens: int = 1024) -> str:
    """Generate response using Groq."""
    from groq import Groq
    
    client = Groq(api_key=api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7
    )
    return response.choices[0].message.content


# ═══════════════════════════════════════════════════════════════════════════
# HuggingFace Provider
# ═══════════════════════════════════════════════════════════════════════════

HF_FALLBACK_MODELS = [
    {"id": "meta-llama/Llama-3.2-3B-Instruct", "name": "Llama 3.2 3B Instruct"},
    {"id": "meta-llama/Llama-3.1-8B-Instruct", "name": "Llama 3.1 8B Instruct"},
    {"id": "mistralai/Mistral-7B-Instruct-v0.3", "name": "Mistral 7B Instruct"},
    {"id": "microsoft/Phi-3-mini-4k-instruct", "name": "Phi 3 Mini 4K Instruct"},
    {"id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen 2.5 7B Instruct"},
]


def fetch_huggingface_models(api_key: str) -> List[Dict]:
    """Fetch available text-generation models from HuggingFace."""
    if not api_key:
        return HF_FALLBACK_MODELS
    
    cache_key = f"hf_{api_key[:8]}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]
    
    try:
        response = requests.get(
            "https://huggingface.co/api/models",
            params={
                "pipeline_tag": "text-generation",
                "filter": "conversational",
                "inference": "warm",
                "sort": "downloads",
                "direction": "-1",
                "limit": 30
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        models = []
        for model in data:
            model_id = model.get("modelId", model.get("id", ""))
            if any(x in model_id.lower() for x in ["instruct", "chat", "it"]):
                models.append({
                    "id": model_id,
                    "name": model_id.split("/")[-1].replace("-", " ")
                })
        
        if models:
            _model_cache[cache_key] = models
            return models
            
    except Exception as e:
        logger.warning(f"Failed to fetch HuggingFace models: {e}")
    
    return HF_FALLBACK_MODELS


def generate_huggingface(prompt: str, api_key: str, model: str = "meta-llama/Llama-3.2-3B-Instruct",
                         system_prompt: str = "", max_tokens: int = 1024) -> str:
    """Generate response using HuggingFace Inference API."""
    from huggingface_hub import InferenceClient
    
    client = InferenceClient(api_key=api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content


# ═══════════════════════════════════════════════════════════════════════════
# Unified Interface
# ═══════════════════════════════════════════════════════════════════════════

def fetch_models(provider: str, api_key: str) -> List[Dict]:
    """Fetch models for a provider."""
    if provider == "groq":
        return fetch_groq_models(api_key)
    elif provider == "huggingface":
        return fetch_huggingface_models(api_key)
    return []


def generate(provider: str, prompt: str, api_key: str, model: str,
             system_prompt: str = "", max_tokens: int = 1024) -> str:
    """Generate response using selected provider and model."""
    if provider == "groq":
        return generate_groq(prompt, api_key, model, system_prompt, max_tokens)
    elif provider == "huggingface":
        return generate_huggingface(prompt, api_key, model, system_prompt, max_tokens)
    raise ValueError(f"Unknown provider: {provider}")
