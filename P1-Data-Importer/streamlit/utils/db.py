import os
import io
import base64
import pandas as pd
from sqlalchemy import create_engine, text, inspect

db_host = os.environ.get("DB_HOST", "localhost")
db_port = os.environ.get("DB_PORT", "3306")
db_name = os.environ.get("DB_NAME", "appdb")
db_user = os.environ.get("DB_USER", "appuser")
db_password = os.environ.get("DB_PASSWORD", "apppassword")

engine = create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4", pool_pre_ping=True)

def ensure_files_table():
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS files (id INT AUTO_INCREMENT PRIMARY KEY,filename VARCHAR(255) NOT NULL,content_type VARCHAR(128) NOT NULL,size_bytes BIGINT NOT NULL,data LONGBLOB NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))

def list_tables():
    insp = inspect(engine)
    return sorted([t for t in insp.get_table_names()])

def normalize_table_name(name):
    s = "".join(c if c.isalnum() or c in ("_",) else "_" for c in name.lower())
    s = s.strip("_")
    if s and s[0].isdigit():
        s = f"t_{s}"
    return s or "table"

def unique_table_name(base):
    base = normalize_table_name(base)
    existing = set(list_tables())
    if base not in existing:
        return base
    i = 2
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"

def read_tabular_file(uploaded):
    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(io.BytesIO(data))
    return None

def write_df(df, table_name, replace=False):
    if replace and table_name in list_tables():
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
    df.to_sql(table_name, engine, index=False, if_exists="fail")

def save_file_to_db(uploaded):
    ensure_files_table()
    b = uploaded.read()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO files (filename, content_type, size_bytes, data) VALUES (:f,:c,:s,:d)"), {"f": uploaded.name, "c": uploaded.type or "", "s": len(b), "d": b})

def list_files():
    ensure_files_table()
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, filename, content_type, size_bytes, created_at FROM files ORDER BY id DESC")).fetchall()
    return rows

def get_file_blob(file_id):
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id, filename, content_type, size_bytes, data FROM files WHERE id=:i"), {"i": file_id}).fetchone()
    return row
