from fastapi import APIRouter, HTTPException
from ..services.llm import chat_once
from ..config import DEFAULT_MODEL

router = APIRouter()

@router.post("/chat")
def chat(payload: dict):
    msg = str(payload.get("message") or "")
    model = str(payload.get("model") or DEFAULT_MODEL)
    if not msg.strip():
        raise HTTPException(status_code=400, detail="message required")
    return {"answer": chat_once(model, msg)}
