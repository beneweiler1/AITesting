from fastapi import APIRouter, HTTPException
from typing import Optional
from ..db import list_file_rows_full
from ..services.parse import parse_pdf, parse_docx
from ..services.chunks import chunk_text
from ..services.embeddings import embed_texts, pull_embed_model
from ..vector import get_collection, reset_collection

router = APIRouter(prefix="/vdb")

@router.post("/reset")
def vdb_reset():
    reset_collection()
    return {"reset": True}

@router.post("/models/setup")
def vdb_models_setup():
    pull_embed_model()
    return {"status": "ok"}

@router.post("/ingest_files")
def vdb_ingest_files(reindex: Optional[bool] = False):
    rows = list_file_rows_full()
    docs = []
    metas = []
    ids = []
    for rid, fname, ctype, sizeb, data in rows:
        n = str(fname or "").lower()
        tx = ""
        if n.endswith(".pdf") or (ctype or "").startswith("application/pdf"):
            tx = parse_pdf(data)
        elif n.endswith(".docx") or (ctype or "") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            tx = parse_docx(data)
        if not tx:
            continue
        chunks = chunk_text(tx)
        for idx, c in enumerate(chunks):
            docs.append(c)
            metas.append({"file_id": rid, "filename": fname, "chunk": idx})
            ids.append(f"f{rid}-{idx}")
    if not docs:
        return {"ingested": 0}
    vecs = embed_texts(docs)
    coll = reset_collection() if reindex else get_collection()
    coll.upsert(embeddings=vecs, documents=docs, metadatas=metas, ids=ids)
    return {"ingested": len(docs)}

@router.post("/search")
def vdb_search(payload: dict):
    q = str(payload.get("q") or "")
    k = int(payload.get("k") or 5)
    if not q.strip():
        raise HTTPException(status_code=400, detail="q required")
    v = embed_texts([q])[0]
    coll = get_collection()
    res = coll.query(query_embeddings=[v], n_results=k, include=["documents", "metadatas", "distances"])
    out = []
    if res and res.get("documents"):
        d = res["documents"][0]
        m = res["metadatas"][0]
        s = res["distances"][0] if res.get("distances") else [None] * len(d)
        for i in range(len(d)):
            out.append({"text": d[i], "meta": m[i], "score": s[i]})
    return {"results": out}
