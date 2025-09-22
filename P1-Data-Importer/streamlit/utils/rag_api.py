import requests

def _json_or_text(r):
    try:
        return True, r.json()
    except Exception:
        return False, r.text

def rag_models_setup(rag_base: str, timeout: int = 600):
    r = requests.post(f"{rag_base}/vdb/models/setup", timeout=timeout)
    return _json_or_text(r)

def rag_ingest_files(rag_base: str, timeout: int = 600):
    r = requests.post(f"{rag_base}/vdb/ingest_files", timeout=timeout)
    return _json_or_text(r)

def rag_ingest_tables(rag_base: str, tables_csv: str | None = None, timeout: int = 600):
    payload = {"tables": tables_csv} if tables_csv else {}
    r = requests.post(f"{rag_base}/ingest/db", json=payload, timeout=timeout)
    return _json_or_text(r)

def rag_reset_vdb(rag_base: str, timeout: int = 60):
    r = requests.post(f"{rag_base}/vdb/reset", timeout=timeout)
    return _json_or_text(r)
