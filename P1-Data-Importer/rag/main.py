import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LLM Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)

ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
default_model = os.environ.get("OLLAMA_LLM_MODEL", "mistral")

def ollama_pull(model: str):
    r = requests.post(f"{ollama_base}/api/pull", json={"name": model}, stream=True, timeout=600)
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"ollama pull failed: {r.text}")

def try_generate(model: str, prompt: str):
    return requests.post(f"{ollama_base}/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=180)

def try_chat(model: str, prompt: str):
    return requests.post(f"{ollama_base}/api/chat", json={"model": model, "messages":[{"role":"user","content": prompt}]}, timeout=180)

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/chat")
def chat(payload: dict):
    msg = str(payload.get("message") or "")
    model = str(payload.get("model") or default_model)
    if not msg.strip():
        raise HTTPException(status_code=400, detail="message required")
    r = try_generate(model, msg)
    if r.status_code == 404:
        ollama_pull(model)
        r = try_generate(model, msg)
    if r.status_code == 404:
        r = try_chat(model, msg)
    if r.status_code >= 400:
        raise HTTPException(status_code=500, detail=r.text)
    j = r.json()
    ans = j.get("response") or j.get("message", {}).get("content") or ""
    return {"answer": ans}
