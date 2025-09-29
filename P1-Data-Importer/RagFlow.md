# RAG Chat Flow

This diagram shows the interaction between the user, Streamlit UI, FastAPI RAG backend, Chroma vector DB, MySQL, and Ollama.

```mermaid
sequenceDiagram
  participant U as User (Streamlit)
  participant ST as Streamlit App
  participant API as FastAPI RAG
  participant VEC as Chroma
  participant DB as MySQL
  participant OL as Ollama

  U->>ST: Ask in RAG Chat
  ST->>API: POST /vdb/search {q,k}
  API->>OL: POST /api/embeddings
  OL-->>API: embedding
  API->>VEC: query(embedding,k)
  VEC-->>API: top-k chunks

  opt Use tables
    ST->>API: SQL fetch via API
    API->>DB: SELECT schema/sample
    DB-->>API: rows/schema
  end

  API->>OL: POST /api/generate or /api/chat (prompt + context)
  OL-->>API: answer text
  API-->>ST: {answer, citations}
  ST-->>U: Render answer + sources