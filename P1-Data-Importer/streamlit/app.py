import os
import streamlit as st
from utils.db import engine, ensure_files_table, list_tables
from ui.topbar import render_topbar
from ui.tabs_upload_data import render_tab_upload_data
from ui.tabs_browse_tables import render_tab_browse_tables
from ui.tabs_upload_files import render_tab_upload_files
from ui.tabs_files import render_tab_files
from ui.tabs_clear_all import render_tab_clear_all
from ui.tabs_vector_search import render_tab_vector_search
from ui.tabs_chat import render_tab_chat
from ui.tabs_rag_chat import render_tab_rag_chat

st.set_page_config(page_title="Data Importer", layout="wide")
st.title("Data Importer")

rag_base = os.environ.get("RAG_BASE_URL", "http://localhost:8001")

if "auto_sync" not in st.session_state:
    st.session_state.auto_sync = True

st.sidebar.checkbox("Auto-sync to RAG on upload/import", value=st.session_state.auto_sync, key="auto_sync")

render_topbar(engine, rag_base)

tabs = st.tabs(["Browse Tables", "Clear All", "Vector Search", "Chat", "Rag Chat"])

with tabs[0]:
    render_tab_browse_tables(engine)
with tabs[1]:
    render_tab_clear_all(engine, rag_base)
with tabs[2]:
    render_tab_vector_search(rag_base)
with tabs[3]:
    render_tab_chat(rag_base)
with tabs[4]:
    render_tab_rag_chat(engine, rag_base)
