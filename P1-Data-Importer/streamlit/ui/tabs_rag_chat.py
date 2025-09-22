import time
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import text, inspect

def render_tab_rag_chat(engine, rag_base):
    st.subheader("RAG Chat")
    col_a, col_b, col_c = st.columns([1.2,1,1])
    with col_a:
        q = st.text_area("Question", height=140, key="rag_q")
    with col_b:
        use_files = st.checkbox("Use files (VDB)", value=True, key="rag_use_files")
        topk = st.number_input("Top K chunks", min_value=1, max_value=20, value=5, step=1, key="rag_topk")
        if st.button("Setup Embed Model", key="btn_rag_setup_embed"):
            try:
                r = requests.post(f"{rag_base}/vdb/models/setup", timeout=600)
                st.success(r.json())
            except Exception as e:
                st.error(str(e))
    with col_c:
        use_tables = st.checkbox("Use tables (SQL)", value=True, key="rag_use_tables")
        sample_rows = st.number_input("Rows per table", min_value=0, max_value=1000, value=50, step=10, key="rag_rows")
        model_name = st.text_input("LLM Model", value="mistral", key="rag_model")

    sel_tables = []
    if use_tables:
        try:
            from utils.db import list_tables
            sel_tables = st.multiselect("Tables to include", options=list_tables(), key="rag_tables")
        except Exception as e:
            st.warning(str(e))

    dbg = st.checkbox("Show debug", value=True, key="rag_dbg")

    if st.button("Ask (RAG)", key="btn_rag_ask"):
        if not q.strip():
            st.warning("Enter a question")
        else:
            try:
                ctx_files = []
                src_files = []
                if use_files:
                    rf = requests.post(f"{rag_base}/vdb/search", json={"q": q, "k": int(topk)}, timeout=120)
                    if rf.status_code >= 400:
                        st.error(f"VDB search error {rf.status_code}")
                    else:
                        hits = rf.json().get("results", [])
                        for h in hits:
                            m = h.get("meta", {})
                            t = h.get("text","")
                            ctx_files.append(f"[file:{m.get('filename','')} id:{m.get('file_id')} chunk:{m.get('chunk')}] {t}")
                            src_files.append({"file_id": m.get("file_id"), "filename": m.get("filename"), "chunk": m.get("chunk"), "score": h.get("score")})

                ctx_tables = []
                src_tables = []
                if use_tables and sel_tables:
                    for tname in sel_tables:
                        try:
                            cols = []
                            insp = inspect(engine)
                            for c in insp.get_columns(tname):
                                cols.append(f"{c.get('name')} {str(c.get('type'))}")
                            schema_txt = f"TABLE {tname} COLUMNS: " + ", ".join(cols)
                            ctx_tables.append(schema_txt)
                            if sample_rows and sample_rows > 0:
                                with engine.begin() as conn:
                                    df = pd.read_sql(text(f"SELECT * FROM `{tname}` LIMIT :lim"), conn, params={"lim": int(sample_rows)})
                                if not df.empty:
                                    ctx_tables.append(f"SAMPLE {tname}\n" + df.to_csv(index=False))
                            src_tables.append({"table": tname, "columns": [c.split()[0] for c in cols]})
                        except Exception as ex:
                            st.warning(f"{tname}: {ex}")

                ctx_sections = []
                if ctx_files:
                    ctx_sections.append("Context Files:\n" + "\n\n".join(ctx_files))
                if ctx_tables:
                    ctx_sections.append("Context Tables:\n" + "\n\n".join(ctx_tables))
                ctx_block = "\n\n---\n\n".join(ctx_sections) if ctx_sections else ""

                final_prompt = q if not ctx_block else f"Use the provided context to answer.\n\n{ctx_block}\n\nQuestion:\n{q}\n\nAnswer:"
                t0 = time.time()
                rc = requests.post(f"{rag_base}/chat", json={"message": final_prompt, "model": model_name}, timeout=240)
                dt = round((time.time()-t0)*1000.0,1)
                if rc.status_code >= 400:
                    st.error(f"Chat error {rc.status_code}")
                    st.code(rc.text)
                else:
                    data = rc.json()
                    st.markdown("### Answer")
                    st.write(data.get("answer",""))
                    with st.expander("Sources"):
                        if src_files:
                            st.markdown("Files")
                            for s in src_files:
                                fid = s.get("file_id")
                                fn = s.get("filename","")
                                sc = s.get("score", None)
                                label = f"{fn} (id={fid}, chunk={s.get('chunk')}, score={round(sc,4) if isinstance(sc,(int,float)) else sc})"
                                if str(fn).lower().endswith(".pdf") and fid is not None:
                                    components.html(f'<iframe src="{rag_base}/files/{fid}/inline" width="100%" height="400px"></iframe>', height=420)
                                st.write(label)
                        if src_tables:
                            st.markdown("Tables")
                            st.json(src_tables)
                    if dbg:
                        with st.expander("Debug"):
                            st.write({"latency_ms": dt, "top_k": int(topk), "use_files": use_files, "use_tables": use_tables, "rows_per_table": int(sample_rows)})
                            st.markdown("Prompt Sent")
                            st.code(final_prompt)
            except Exception as e:
                st.error(str(e))
