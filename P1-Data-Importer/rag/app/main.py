from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.health import router as health_router
from .routers.files import router as files_router
from .routers.vdb import router as vdb_router
from .routers.chat import router as chat_router
from .routers.tables import router as tables_router

app = FastAPI(title="Vector Files + Chat", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
app.include_router(health_router)
app.include_router(files_router)
app.include_router(vdb_router)
app.include_router(chat_router)
app.include_router(tables_router)