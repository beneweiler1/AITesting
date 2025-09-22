from sqlalchemy import create_engine, text
from .config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4", pool_pre_ping=True)

def list_files_meta():
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, filename, content_type, size_bytes, created_at FROM files ORDER BY id DESC")).mappings().all()
    return [dict(r) for r in rows]

def file_blob(fid: int):
    with engine.begin() as conn:
        r = conn.execute(text("SELECT filename, content_type, data FROM files WHERE id=:i"), {"i": fid}).first()
    return r

def list_file_rows_full():
    with engine.begin() as conn:
        return conn.execute(text("SELECT id, filename, content_type, size_bytes, data FROM files ORDER BY id DESC")).fetchall()
