import os, re
from typing import List, Dict, Any, Set

NEG = re.compile(r"(upload|image|file|avatar|photo|multipart)", re.I)
POS_UPLOAD = re.compile(r"(upload|image|file|photo|avatar|picture|binary)", re.I)

def tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", str(text).lower()) if len(w) > 2]

def desired_methods(text: str) -> List[str]:
    t = text.lower()
    if any(w in t for w in ["create","add","make","new","register","open","start","post"]):
        return ["POST","PUT"]
    if any(w in t for w in ["update","edit","change","modify","patch"]):
        return ["PUT","PATCH"]
    if any(w in t for w in ["delete","remove","cancel","close","destroy"]):
        return ["DELETE"]
    if any(w in t for w in ["find","list","get","show","fetch","lookup","search","read","query"]):
        return ["GET"]
    return ["GET","POST","PUT","PATCH","DELETE"]

def build_vocab(tools: List[Dict[str, Any]]) -> Set[str]:
    vocab: Set[str] = set()
    for t in tools:
        meta = t.get("x-mcp", {})
        path = str(meta.get("path",""))
        name = str(t.get("name",""))
        desc = str(t.get("description",""))
        vocab.update(tokenize(path))
        vocab.update(tokenize(name))
        vocab.update(tokenize(desc))
    return vocab

def score_tool(utterance: str, tool: Dict[str, Any], vocab: Set[str]) -> float:
    toks = set(tokenize(utterance))
    meta = tool.get("x-mcp", {})
    path = str(meta.get("path",""))
    name = str(tool.get("name",""))
    desc = str(tool.get("description",""))
    method = str(meta.get("method","GET")).upper()
    consumes = meta.get("consumes", []) or []
    s = 0.0
    dm = desired_methods(utterance)
    if method in dm:
        s += 3.0
    if method == dm[0]:
        s += 2.0
    overlap = 0
    target_text = " ".join([path, name, desc])
    lt = target_text.lower()
    for w in toks:
        if w in lt:
            overlap += 1
        elif w in vocab:
            overlap += 0.5
    s += min(overlap, 8) * 1.2
    depth = path.count("/")
    s += max(0, 5 - depth) * 0.2
    avoid_upload = os.getenv("AVOID_UPLOAD_BY_DEFAULT","1") == "1"
    if avoid_upload and NEG.search(lt) and not POS_UPLOAD.search(utterance):
        s -= 8.0
    if any("multipart/form-data" in c for c in consumes) and not POS_UPLOAD.search(utterance) and avoid_upload:
        s -= 6.0
    return s

def rank_tools(utterance: str, tools: List[Dict[str, Any]], limit: int, vocab: Set[str]) -> List[Dict[str, Any]]:
    scored = [(score_tool(utterance, t, vocab), t) for t in tools]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:max(1, limit)]]
