from chromadb import Client, Settings

_CLIENT = None
_COLL_NAME = "files"

def _client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = Client(Settings(persist_directory="/chroma"))
    return _CLIENT

def get_collection():
    return _client().get_or_create_collection(_COLL_NAME, metadata={"hnsw:space": "cosine"})

def reset_collection():
    c = _client()
    try:
        c.delete_collection(_COLL_NAME)
    except Exception:
        pass
    return c.get_or_create_collection(_COLL_NAME, metadata={"hnsw:space": "cosine"})
