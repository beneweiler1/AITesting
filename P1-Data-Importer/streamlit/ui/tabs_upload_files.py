import io
import base64
import streamlit as st
from docx import Document
import streamlit.components.v1 as components
from utils.db import save_file_to_db
from utils.rag_api import rag_ingest_files

def render_tab_upload_files(engine, rag_base):
    up = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"], key="up_files_pdfdocx")
    if up:
        name = up.name.lower()
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Save File", type="primary", key="btn_files_save"):
                try:
                    up.seek(0)
                    save_file_to_db(up)
                    st.success("Saved")
                    if st.session_state.auto_sync:
                        ok, res = rag_ingest_files(rag_base)
                        if ok:
                            st.success("RAG synced files")
                        else:
                            st.warning(f"RAG sync failed: {res}")
                except Exception as e:
                    st.error(str(e))
        with col2:
            if name.endswith(".pdf"):
                up.seek(0)
                b = up.read()
                b64 = base64.b64encode(b).decode("utf-8")
                components.html(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="700px"></iframe>', height=720)
            elif name.endswith(".docx"):
                up.seek(0)
                b = up.read()
                doc = Document(io.BytesIO(b))
                text_content = "\n".join(p.text for p in doc.paragraphs)
                st.text_area("Preview", value=text_content, height=500, key="txt_files_preview")
