import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "appdb")
DB_USER = os.environ.get("DB_USER", "appuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "apppassword")

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
DEFAULT_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "mistral")

CHROMA_DIR = os.environ.get("CHROMA_DIR", "/chroma")
COLLECTION_NAME = os.environ.get("RAG_COLLECTION_NAME", "files_kb")
