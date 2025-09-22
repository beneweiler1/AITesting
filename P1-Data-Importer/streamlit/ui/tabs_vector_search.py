import requests
import streamlit as st
from docx import Document
from io import BytesIO
import streamlit.components.v1 as components

def render_tab_vector_search(rag_base):
    st.subheader("Vector Search")
    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        if st.button("Index Files", key="btn_vs_index"):
            try:
                r = requests.post(f"{rag_base}/vdb/ingest_files", timeout=600)
                st.success(r.json())
            except Exception as e:
                st.error(str(e))

    with c2:
        if st.button("Reset Index", key="btn_vs_reset"):
            try:
                r = requests.post(f"{rag_base}/vdb/reset", timeout=60)
                st.success(r.json())
            except Exception as e:
                st.error(str(e))
    with c3:
        if st.button("List Files", key="btn_vs_list_files"):
            try:
                r = requests.get(f"{rag_base}/files", timeout=30)
                files = r.json().get("files", [])
                if not files:
                    st.info("No files found in DB")
                else:
                    st.dataframe(files, use_container_width=True)
            except Exception as e:
                st.error(str(e))

    q = st.text_input("Query", key="in_vs_query")
    k = st.number_input("Top K", min_value=1, max_value=20, value=5, step=1, key="in_vs_k")
    if st.button("Search", key="btn_vs_search"):
        try:
            r = requests.post(f"{rag_base}/vdb/search", json={"q": q, "k": int(k)}, timeout=60)
            res = r.json().get("results", [])
            for hit in res:
                meta = hit.get("meta", {})
                text = hit.get("text", "")
                score = hit.get("score", None)
                with st.expander(f"{meta.get('filename','')}  id={meta.get('file_id')}  score={round(score,4) if isinstance(score,(int,float)) else score}"):
                    st.write(text)
                    fid = meta.get("file_id")
                    if fid:
                        if str(meta.get("filename","")).lower().endswith(".pdf"):
                            components.html(f'<iframe src="{rag_base}/files/{fid}/inline" width="100%" height="600px"></iframe>', height=620)
                        else:
                            try:
                                g = requests.get(f"{rag_base}/files/{fid}/inline", timeout=30)
                                b = BytesIO(g.content)
                                doc = Document(b)
                                t = "\n".join([p.text for p in doc.paragraphs])
                                st.text_area("Preview", value=t, height=300, key=f"txt_vs_preview_{fid}")
                            except Exception as e:
                                st.warning(str(e))
        except Exception as e:
            st.error(str(e))
