import chromadb
from chromadb.config import Settings
from .config import CHROMA_DIR, COLLECTION_NAME

client = chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False))
collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

def reset_collection():
    client.delete_collection(name=COLLECTION_NAME)
    global collection
    collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
