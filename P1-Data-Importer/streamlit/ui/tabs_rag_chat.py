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
        topk = st.number_input("Top K chunks", min_value=1, max_value=10, value=3, step=1, key="rag_topk")
        if st.button("Setup Embed Model", key="btn_rag_setup_embed"):
            try:
                r = requests.post(f"{rag_base}/vdb/models/setup", timeout=600)
                st.success(r.json())
            except Exception as e:
                st.error(str(e))
    with col_c:
        use_tables = st.checkbox("Use SQL (LLM-generated)", value=True, key="rag_use_sql")
        model_name = st.text_input("LLM Model", value="mistral", key="rag_model")

    sel_tables = []
    if use_tables:
        try:
            # Fetch available tables from backend
            rt = requests.get(f"{rag_base}/tables", timeout=10)
            if rt.status_code == 200:
                available_tables = rt.json().get("tables", [])
                sel_tables = st.multiselect("Tables to include", options=available_tables, key="rag_tables")
            else:
                st.warning("Could not fetch table list from backend")
        except Exception as e:
            st.warning(str(e))

    dbg = st.checkbox("Show debug", value=True, key="rag_dbg")

    if st.button("Ask (RAG)", key="btn_rag_ask"):
        if not q.strip():
            st.warning("Enter a question")
        else:
            try:
                # Call backend with RAG enabled
                t0 = time.time()
                payload = {
                    "message": q,
                    "model": model_name,
                    "use_rag": use_files,
                    "topk": int(topk),
                    "use_sql": use_tables,
                    "selected_tables": sel_tables
                }
                rc = requests.post(f"{rag_base}/chat", json=payload, timeout=240)
                dt = round((time.time()-t0)*1000.0, 1)
                
                if rc.status_code >= 400:
                    st.error(f"Chat error {rc.status_code}")
                    st.code(rc.text)
                else:
                    data = rc.json()
                    
                    # Display Answer
                    st.markdown("### Answer")
                    st.write(data.get("answer", ""))
                    
                    # Display Sources
                    sources = data.get("sources", {})
                    
                    with st.expander("Sources", expanded=True):
                        # File sources from VDB
                        src_files = sources.get("files", [])
                        if src_files:
                            st.markdown("**Retrieved Chunks from Files**")
                            for idx, s in enumerate(src_files, 1):
                                fid = s.get("file_id")
                                fn = s.get("filename", "")
                                sc = s.get("score", None)
                                text = s.get("text", "")
                                
                                st.markdown(f"**{idx}. {fn}** (chunk {s.get('chunk')}, score: {round(sc,4) if isinstance(sc,(int,float)) else sc})")
                                
                                st.text_area(
                                    f"Chunk {idx}",
                                    value=text,
                                    height=150,
                                    key=f"chunk_{idx}",
                                    disabled=True
                                )
                                st.divider()
                        
                        # SQL sources
                        src_sql = sources.get("sql", [])
                        if src_sql:
                            st.markdown("**Retrieved Data from Database**")
                            for idx, s in enumerate(src_sql, 1):
                                st.markdown(f"**Query {s.get('query_index')}**: {s.get('explanation')}")
                                st.write(f"Tables used: {', '.join(s.get('tables_used', []))}")
                                st.write(f"Rows retrieved: {s.get('row_count')}")
                                st.divider()
                    
                    # PDF Previews
                    src_files = sources.get("files", [])
                    pdf_files = [s for s in src_files if str(s.get("filename", "")).lower().endswith(".pdf") and s.get("file_id")]
                    if pdf_files:
                        with st.expander("PDF Previews"):
                            for s in pdf_files:
                                fid = s.get("file_id")
                                fn = s.get("filename", "")
                                st.markdown(f"**{fn}**")
                                components.html(
                                    f'<iframe src="{rag_base}/files/{fid}/inline" width="100%" height="400px"></iframe>',
                                    height=420
                                )
                    
                    # Display Debug Info
                    if dbg:
                        with st.expander("Debug"):
                            debug_data = data.get("debug", {})
                            debug_data["frontend_total_ms"] = dt
                            
                            st.json(debug_data)
                            
                            # Show SQL queries if available
                            if "sql_queries" in debug_data:
                                st.markdown("**SQL Queries Executed**")
                                for q in debug_data["sql_queries"]:
                                    if q.get("success"):
                                        st.success(f"✓ {q.get('explanation')} ({q.get('row_count')} rows)")
                                        st.code(q.get("sql"), language="sql")
                                    else:
                                        st.error(f"✗ {q.get('explanation')}")
                                        st.code(q.get("sql"), language="sql")
                                        st.write(f"Error: {q.get('error')}")
                            
                            # Show the augmented prompt
                            if "augmented_prompt" in debug_data:
                                st.markdown("**Final Prompt Sent to LLM**")
                                st.code(debug_data["augmented_prompt"])
                            
            except Exception as e:
                st.error(str(e))