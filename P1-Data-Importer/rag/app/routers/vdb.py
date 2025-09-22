from fastapi import APIRouter, HTTPException
from typing import Optional
from ..db import list_file_rows_full
from ..services.parse import parse_pdf, parse_docx
from ..services.chunks import chunk_text
from ..services.embeddings import embed_texts, pull_embed_model
from ..vector import collection, reset_collection

router = APIRouter(prefix="/vdb")

@router.post("/reset")
def vdb_reset():
    reset_collection()
    return {"reset": True}

@router.post("/models/setup")
def vdb_models_setup():
    pull_embed_model()
    return {"status":"ok"}

@router.post("/ingest_files")
def vdb_ingest_files(reindex: Optional[bool] = False):
    rows = list_file_rows_full()
    docs = []
    metas = []
    ids = []
    for rid, fname, ctype, sizeb, data in rows:
        tx = ""
        n = str(fname).lower()
        if n.endswith(".pdf") or (ctype or "").startswith("application/pdf"):
            tx = parse_pdf(data)
        elif n.endswith(".docx") or (ctype or "") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            tx = parse_docx(data)
        else:
            continue
        if not tx.strip():
            continue
        chunks = chunk_text(tx)
        for idx, c in enumerate(chunks):
            did = f"f{rid}-{idx}"
            docs.append(c)
            metas.append({"file_id": rid, "filename": fname, "chunk": idx})
            ids.append(did)
    if not docs:
        return {"ingested": 0}
    vecs = embed_texts(docs)
    if reindex:
        reset_collection()
    collection.upsert(embeddings=vecs, documents=docs, metadatas=metas, ids=ids)
    return {"ingested": len(docs)}

@router.post("/search")
def vdb_search(payload: dict):
    q = str(payload.get("q") or "")
    k = int(payload.get("k") or 5)
    if not q.strip():
        raise HTTPException(status_code=400, detail="q required")
    v = embed_texts([q])[0]
    res = collection.query(query_embeddings=[v], n_results=k, include=["documents","metadatas","distances"])
    out = []
    if res and res.get("documents"):
        D = res["documents"][0]
        M = res["metadatas"][0]
        S = res["distances"][0] if res.get("distances") else [None]*len(D)
        for i in range(len(D)):
            out.append({"text": D[i], "meta": M[i], "score": S[i]})
    return {"results": out}
