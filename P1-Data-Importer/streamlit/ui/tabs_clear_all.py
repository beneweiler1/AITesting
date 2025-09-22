from utils.db import list_tables, ensure_files_table
from sqlalchemy import text
from utils.rag_api import rag_ingest_tables, rag_ingest_files, rag_reset_vdb
import streamlit as st

def render_tab_clear_all(engine, rag_base):
    st.warning("This will permanently delete all tables and vector indexes.")
    if st.button("Clear Everything", type="primary", key="btn_clear_all_tab"):
        try:
            with engine.begin() as conn:
                tables = list_tables()
                for t in tables:
                    conn.execute(text(f"DROP TABLE IF EXISTS `{t}`"))
            st.success("All SQL tables have been cleared.")
            ensure_files_table()

            ok_vdb, vdb_msg = rag_reset_vdb(rag_base)
            if ok_vdb:
                st.success("Vector DB reset successfully")
            else:
                st.warning(f"Vector DB reset issue: {vdb_msg}")

            if st.session_state.get("auto_sync"):
                ok1, _ = rag_ingest_tables(rag_base)      # all tables
                ok2, _ = rag_ingest_files(rag_base)
                if ok1 and ok2:
                    st.success("RAG cleared and resynced")
                else:
                    st.warning("RAG resync encountered an issue")

        except Exception as e:
            st.error(str(e))
