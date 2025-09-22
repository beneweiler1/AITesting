def chunk_text(txt: str, size: int = 500, overlap: int = 60):
    w = txt.split()
    out = []
    i = 0
    while i < len(w):
        out.append(" ".join(w[i:i+size]))
        step = size - overlap if size > overlap else size
        i += step
    return [c for c in out if c.strip()]
