import os
import json
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from .models import IngestRequest, ChatRequest, IngestState
from .mcp import openapi_to_mcp
from .providers import call_swagger_tool
from .state import registry, rag_store
from .openai_client import get_client

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class IngestResponse(BaseModel):
    session_id: str
    tool_count: int
    doc_count: int

class ToolInfo(BaseModel):
    name: str
    description: str | None = None
    method: str
    path: str
    base: str

@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    sid = "sess"
    tools: List[Dict[str, Any]] = []
    docs: List[str] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for spec_url in req.swagger_urls:
            r = await client.get(spec_url)
            if r.status_code >= 400:
                raise HTTPException(400, f"Failed to fetch {spec_url}")
            spec = r.json()
            new_tools = openapi_to_mcp(spec, spec_url)
            tools.extend(new_tools)
            for t in new_tools:
                meta = t.get("x-mcp", {})
                text = json.dumps({
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "method": meta.get("method"),
                    "path": meta.get("path"),
                    "base": meta.get("base_url")
                }, ensure_ascii=False)
                docs.append(text)
    rag_store.add(docs)
    state = IngestState(tools=tools, vector_docs=docs, instructions=req.instructions)
    registry.set(sid, state.model_dump())
    from .tool_select import build_vocab
    registry.sessions[sid]["vocab"] = list(build_vocab(tools))
    registry.clear_history(sid)
    return IngestResponse(session_id=sid, tool_count=len(tools), doc_count=len(docs))

@app.get("/tools", response_model=List[ToolInfo])
async def tools(session_id: str = Query(...)):
    st = registry.get(session_id)
    if not st:
        raise HTTPException(404, "No session")
    out: List[ToolInfo] = []
    for t in st["tools"]:
        meta = t.get("x-mcp", {})
        out.append(ToolInfo(
            name=t["name"],
            description=t.get("description"),
            method=meta.get("method",""),
            path=meta.get("path",""),
            base=meta.get("base_url","")
        ))
    return out

@app.post("/chat")
async def chat(req: ChatRequest):
    st = registry.get(req.session_id)
    if not st:
        raise HTTPException(400, "No session. Call /ingest first.")
    topk = int(os.getenv("RAG_TOP_K", "5"))
    ctx = rag_store.query(req.message, k=topk)
    context_blob = "\n".join([d for d,_ in ctx])
    from .tool_select import rank_tools
    tool_limit = int(os.getenv("TOP_TOOL_LIMIT", "8"))
    vocab = set(st.get("vocab", []))
    selected = rank_tools(req.message, st["tools"], limit=tool_limit, vocab=vocab)
    tools = []
    tool_map = {}
    for t in selected:
        tools.append({"type":"function","function":{"name":t["name"],"description":t.get("description",""),"parameters":t["parameters"]}})
        tool_map[t["name"]] = t
    client = get_client()
    sys_base = st.get("instructions", "You are a helpful assistant that uses tools when relevant.")
    sys_rules = "Do not use any upload, image, file, or multipart endpoints unless the user explicitly asks. Prefer create endpoints for add/make/new; prefer GET for find/list/get; prefer update for edit/modify; prefer delete for remove."
    messages = []
    messages.append({"role":"system","content":sys_base + "\n" + sys_rules})
    if context_blob:
        messages.append({"role":"system","content":"Context:\n" + context_blob})
    for m in registry.get_history(req.session_id):
        messages.append(m)
    messages.append({"role":"user","content":req.message})
    registry.append_history(req.session_id, "user", req.message)
    rsp = client.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools, tool_choice="auto")
    out = rsp.choices[0].message
    if getattr(out, "tool_calls", None):
        call = out.tool_calls[0]
        tname = call.function.name
        targs = json.loads(call.function.arguments or "{}")
        tool_def = tool_map.get(tname)
        if not tool_def:
            raise HTTPException(500, "Unknown tool")
        result = call_swagger_tool(tool_def, targs)
        messages.append({"role":"assistant","tool_calls":[{"id":call.id,"type":"function","function":{"name":tname,"arguments":json.dumps(targs)}}]})
        messages.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(result, ensure_ascii=False)})
        final = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        answer = final.choices[0].message.content
        registry.append_history(req.session_id, "assistant", answer)
        return {"answer": answer, "tool_result": result, "tools_considered": [t["name"] for t in selected]}
    answer = out.content
    registry.append_history(req.session_id, "assistant", answer)
    return {"answer": answer, "tools_considered": [t["name"] for t in selected]}
