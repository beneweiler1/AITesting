from sqlalchemy import create_engine, text, inspect
import pandas as pd
from .config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
    pool_pre_ping=True
)

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

def list_tables():
    """List all tables in the database"""
    insp = inspect(engine)
    return sorted([t for t in insp.get_table_names()])

def get_table_schema(table_name: str):
    """Get schema information for a specific table"""
    insp = inspect(engine)
    columns = []
    for c in insp.get_columns(table_name):
        columns.append({
            "name": c.get("name"),
            "type": str(c.get("type")),
            "nullable": c.get("nullable", True),
            "default": c.get("default")
        })
    return {
        "table": table_name,
        "columns": columns
    }

def get_all_schemas():
    """Get schema information for all tables"""
    tables = list_tables()
    schemas = {}
    for table in tables:
        schemas[table] = get_table_schema(table)
    return schemas

def execute_sql_query(query: str, params: dict = None):
    """Execute a SQL query and return results as a DataFrame"""
    with engine.begin() as conn:
        df = pd.read_sql(text(query), conn, params=params or {})
    return df

def get_sample_data(table_name: str, limit: int = 3):
    """Get sample rows from a table"""
    with engine.begin() as conn:
        df = pd.read_sql(text(f"SELECT * FROM `{table_name}` LIMIT :lim"), conn, params={"lim": limit})
    return df