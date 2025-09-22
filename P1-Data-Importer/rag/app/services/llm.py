import requests
from fastapi import HTTPException
from ..config import OLLAMA_BASE

def pull(model: str):
    r = requests.post(f"{OLLAMA_BASE}/api/pull", json={"name": model}, stream=True, timeout=600)
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=r.text)

def try_generate(model: str, prompt: str):
    return requests.post(f"{OLLAMA_BASE}/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=180)

def try_chat(model: str, prompt: str):
    return requests.post(f"{OLLAMA_BASE}/api/chat", json={"model": model, "messages":[{"role":"user","content": prompt}]}, timeout=180)

def chat_once(model: str, prompt: str):
    r = try_generate(model, prompt)
    if r.status_code == 404:
        pull(model)
        r = try_generate(model, prompt)
    if r.status_code == 404:
        r = try_chat(model, prompt)
    if r.status_code >= 400:
        raise HTTPException(status_code=500, detail=r.text)
    j = r.json()
    return j.get("response") or j.get("message", {}).get("content") or ""
