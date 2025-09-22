import io
import base64
import streamlit as st
import pandas as pd
from docx import Document
import streamlit.components.v1 as components
from utils.db import list_files, get_file_blob

def render_tab_files(engine):
    rows = list_files()
    if not rows:
        st.info("No files stored")
    else:
        df = pd.DataFrame(rows, columns=["id","filename","content_type","size_bytes","created_at"])
        st.dataframe(df, use_container_width=True, height=300)
        sel = st.selectbox("Select file id", options=df["id"].tolist(), key="sel_files_id")
        if st.button("Open", key="btn_files_open"):
            row = get_file_blob(sel)
            if row:
                fid, fname, ctype, sizeb, data = row
                st.write(f"{fname} • {ctype} • {sizeb} bytes")
                if ctype.startswith("application/pdf") or fname.lower().endswith(".pdf"):
                    b64 = base64.b64encode(data).decode("utf-8")
                    components.html(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="700px"></iframe>', height=720)
                elif ctype in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",) or fname.lower().endswith(".docx"):
                    doc = Document(io.BytesIO(data))
                    text_content = "\n".join(p.text for p in doc.paragraphs)
                    st.text_area("Preview", value=text_content, height=500, key="txt_files_open_preview")
                st.download_button("Download", data, file_name=fname, key="btn_files_download")
