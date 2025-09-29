# RAG Application Architecture

This diagram shows the overall system architecture with Streamlit UI, FastAPI backend, Chroma vector DB, MySQL, and Ollama.

```mermaid
flowchart LR
  subgraph Browser
    UI[Streamlit UI]
  end

  subgraph App_Container
    ST[Streamlit App]
  end

  subgraph RAG_API_Container
    API[FastAPI Routers]
    VEC[Chroma (Vector DB)]
    DBLayer[SQLAlchemy]
  end

  subgraph Data_Stores
    MySQL[(MySQL)]
    Files[(MySQL: files table LONGBLOB)]
    ChromaFS[/Chroma Persistent Dir/]
  end

  subgraph Ollama_Container
    LLM[LLM (mistral)]
    EMB[Embeddings (mxbai-embed-large)]
    Ollama[Ollama Server :11434]
  end

  UI -->|HTTP :8501| ST
  ST -->|/chat| API
  ST -->|/vdb/search /vdb/ingest_files /files| API
  API -->|Embeddings| Ollama
  API -->|LLM Generate/Chat| Ollama
  API -->|Vector ops| VEC
  API -->|SQL read| DBLayer
  DBLayer --> MySQL
  DBLayer --> Files
  VEC --- ChromaFS
  Ollama --> LLM
  Ollama --> EMB
