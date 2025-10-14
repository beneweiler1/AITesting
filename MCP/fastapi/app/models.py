from pydantic import BaseModel, Field
from typing import List, Dict, Any

class IngestRequest(BaseModel):
    swagger_urls: List[str]
    instructions: str = Field(default="")

class ChatRequest(BaseModel):
    session_id: str
    message: str

class IngestState(BaseModel):
    tools: List[Dict[str, Any]]
    vector_docs: List[str]
    instructions: str