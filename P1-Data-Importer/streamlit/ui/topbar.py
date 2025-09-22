import os
import streamlit as st
import requests
from utils.db import ensure_files_table, read_tabular_file, write_df, save_file_to_db, unique_table_name

def render_topbar(engine, rag_base):
    st.divider()
    c1, c2, c3 = st.columns([2, 2, 1])

    with c1:
        up_tab = st.file_uploader("Import Table (CSV/XLS/XLSX)", type=["csv", "xls", "xlsx"], key="top_up_table")
        if st.button("Import Table", key="btn_top_import_table"):
            try:
                if not up_tab:
                    st.warning("Select a CSV/XLS/XLSX file")
                else:
                    up_tab.seek(0)
                    df = read_tabular_file(up_tab)
                    if df is None:
                        st.error("Unsupported file")
                    else:
                        base = os.path.splitext(os.path.basename(up_tab.name))[0]
                        tn = unique_table_name(base)
                        write_df(df, tn, replace=False)
                        st.success(f"Imported to table {tn}")
            except Exception as e:
                st.error(str(e))

    with c2:
        up_file = st.file_uploader("Import PDF/DOCX", type=["pdf", "docx"], key="top_up_doc")
        if st.button("Import File", key="btn_top_import_file"):
            try:
                if not up_file:
                    st.warning("Select a PDF or DOCX file")
                else:
                    ensure_files_table()
                    up_file.seek(0)
                    save_file_to_db(up_file)
                    st.success("File saved")
            except Exception as e:
                st.error(str(e))

    with c3:
        if st.button("Sync", key="btn_top_sync"):
            try:
                try:
                    r1 = requests.post(f"{rag_base}/vdb/models/setup", timeout=600)
                    st.info(f"Model: {r1.status_code}")
                except Exception as e:
                    st.warning(f"Model: {e}")
                r2 = requests.post(f"{rag_base}/vdb/ingest_files", timeout=600)
                if r2.status_code < 400:
                    st.success(r2.json())
                else:
                    st.error(f"Index error {r2.status_code}")
                    st.code(r2.text)
            except Exception as e:
                st.error(str(e))
    st.divider()
