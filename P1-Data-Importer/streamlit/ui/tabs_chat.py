import os
import time
import requests
import streamlit as st

def render_tab_chat(rag_base_default):
    st.subheader("Chat")
    c1, c2, c3 = st.columns([2,2,1])
    with c1:
        st.text_input("LLM Model", value=os.environ.get("OLLAMA_LLM_MODEL", "mistral"), key="chat_model")
    with c2:
        st.text_input("RAG Base URL", value=rag_base_default, key="chat_base")
    with c3:
        if st.button("Health", key="btn_chat_health"):
            try:
                r = requests.get(f"{st.session_state.chat_base}/health", timeout=10)
                st.success(str(r.json()))
            except Exception as e:
                st.error(str(e))

    msg = st.text_area("Message", height=140, key="chat_msg")
    dbg = st.checkbox("Show debug details", value=True, key="chat_debug")

    if st.button("Ask", key="btn_chat_ask"):
        if not msg.strip():
            st.warning("Enter a message")
        else:
            try:
                t0 = time.time()
                # Explicitly disable RAG and SQL search for simple chat
                payload = {
                    "message": msg,
                    "model": st.session_state.chat_model,
                    "use_rag": False,
                    "use_sql": False
                }
                r = requests.post(f"{st.session_state.chat_base}/chat", json=payload, timeout=180)
                dt = (time.time() - t0) * 1000.0
                
                if r.status_code >= 400:
                    st.error(f"Error {r.status_code}")
                    try:
                        st.code(r.text, language="json")
                    except Exception:
                        st.write(r.text)
                else:
                    data = r.json()
                    st.markdown("### Answer")
                    st.write(data.get("answer", ""))
                    
                if dbg:
                    with st.expander("Details"):
                        st.write({"status_code": r.status_code, "latency_ms": round(dt, 1)})
                        try:
                            st.markdown("**Request Body**")
                            st.code(payload)
                            st.markdown("**Raw Response**")
                            st.code(r.text)
                        except Exception:
                            st.write("debug display issue")
            except Exception as e:
                st.error(str(e))