import requests
from fastapi import HTTPException
from typing import List
from ..config import OLLAMA_BASE, EMBED_MODEL

def pull_embed_model():
    r = requests.post(f"{OLLAMA_BASE}/api/pull", json={"name": EMBED_MODEL}, stream=True, timeout=600)
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=r.text)

def _embed_once(endpoint: str, text: str):
    return requests.post(f"{OLLAMA_BASE}{endpoint}", json={"model": EMBED_MODEL, "prompt": text}, timeout=120)

def embed_texts(texts: List[str]) -> List[List[float]]:
    try:
        t = _embed_once("/api/embeddings", "ping")
        if t.status_code == 404:
            t = _embed_once("/api/embed", "ping")
        if t.status_code in (404, 400) and "not found" in t.text.lower():
            pull_embed_model()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    out = []
    for x in texts:
        r = _embed_once("/api/embeddings", x)
        if r.status_code == 404:
            r = _embed_once("/api/embed", x)
        if r.status_code >= 400:
            if "not found" in r.text.lower():
                pull_embed_model()
                r = _embed_once("/api/embeddings", x)
                if r.status_code == 404:
                    r = _embed_once("/api/embed", x)
            if r.status_code >= 400:
                raise HTTPException(status_code=500, detail=r.text)
        j = r.json()
        v = j.get("embedding") or j.get("data") or j.get("vector")
        if not v:
            raise HTTPException(status_code=500, detail="embed payload missing vector")
        out.append(v)
    return out
