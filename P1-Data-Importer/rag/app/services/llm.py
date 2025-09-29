import json
import requests
from fastapi import HTTPException
from ..config import OLLAMA_BASE

def pull(model: str):
    r = requests.post(f"{OLLAMA_BASE}/api/pull", json={"name": model}, stream=True, timeout=600)
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=r.text)

def try_generate(model: str, prompt: str):
    response = requests.post(
        f"{OLLAMA_BASE}/api/generate",
        json={"model": model, "prompt": prompt, "stream": True},
        timeout=300,
        stream=True
    )
    
    # Collect streamed response
    full_response = ""
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            if "response" in chunk:
                full_response += chunk["response"]
            if chunk.get("done"):
                break
    
    return type('obj', (object,), {
        'status_code': response.status_code,
        'json': lambda: {"response": full_response}
    })

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
