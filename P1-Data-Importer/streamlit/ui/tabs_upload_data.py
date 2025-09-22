import os
import streamlit as st
from utils.db import read_tabular_file, write_df, unique_table_name, normalize_table_name, list_tables
from utils.rag_api import rag_ingest_tables
import pandas as pd

def render_tab_upload_data(engine, rag_base):
    uploaded = st.file_uploader("Upload CSV/XLS/XLSX", type=["csv", "xls", "xlsx"], key="up_tab_upload")
    if uploaded:
        df = read_tabular_file(uploaded)
        if df is None:
            st.error("Unsupported file")
        else:
            st.subheader("Preview")
            st.dataframe(df.head(100), use_container_width=True)
            default_name = os.path.splitext(os.path.basename(uploaded.name))[0]
            table_input = st.text_input("Destination table name", value=unique_table_name(default_name), key="in_tab_table")
            c1, c2 = st.columns([1,1])
            with c1:
                do_import = st.button("Import to MySQL", type="primary", key="btn_tab_import_mysql")
            with c2:
                replace_existing = st.checkbox("Replace if table exists", value=False, key="chk_tab_replace")
            if do_import:
                tn = normalize_table_name(table_input) if replace_existing else unique_table_name(table_input)
                try:
                    write_df(df, tn, replace=replace_existing)
                    st.success(f"Imported to table {tn}")
                    if st.session_state.auto_sync:
                        ok, res = rag_ingest_tables(rag_base, tn)
                        if ok:
                            st.success(f"RAG synced table {tn}")
                        else:
                            st.warning(f"RAG sync failed: {res}")
                except Exception as e:
                    st.error(str(e))
