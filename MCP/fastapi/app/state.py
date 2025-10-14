from typing import Dict, Any, List
from .rag import SimpleRAG
import os

class Registry:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_history = int(os.getenv("MAX_HISTORY", "16"))
    def set(self, sid: str, data: Dict[str, Any]):
        if sid not in self.sessions:
            self.sessions[sid] = {}
        self.sessions[sid].update(data)
        if "history" not in self.sessions[sid]:
            self.sessions[sid]["history"] = []
    def get(self, sid: str) -> Dict[str, Any]:
        return self.sessions.get(sid, {})
    def append_history(self, sid: str, role: str, content: str):
        if sid not in self.sessions:
            self.sessions[sid] = {"history": []}
        self.sessions[sid].setdefault("history", [])
        self.sessions[sid]["history"].append({"role": role, "content": content})
        if len(self.sessions[sid]["history"]) > self.max_history:
            overflow = len(self.sessions[sid]["history"]) - self.max_history
            self.sessions[sid]["history"] = self.sessions[sid]["history"][overflow:]
    def get_history(self, sid: str) -> List[Dict[str, str]]:
        return self.sessions.get(sid, {}).get("history", [])
    def clear_history(self, sid: str):
        if sid in self.sessions:
            self.sessions[sid]["history"] = []

registry = Registry()
rag_store = SimpleRAG()
