import streamlit as st
import pandas as pd
from sqlalchemy import text
from utils.db import list_tables

def render_tab_browse_tables(engine):
    table_list = list_tables()
    if not table_list:
        st.info("No tables found")
    else:
        left, right = st.columns([1,3])
        with left:
            selected = st.selectbox("Tables", options=table_list, key="sel_browse_table")
            limit = st.number_input("Limit", min_value=1, max_value=10000, value=100, step=50, key="in_browse_limit")
            st.button("Refresh", key="btn_browse_refresh")
        if selected:
            try:
                with engine.begin() as conn:
                    df = pd.read_sql(text(f"SELECT * FROM `{selected}` LIMIT :lim"), conn, params={"lim": int(limit)})
                st.subheader(selected)
                st.dataframe(df, use_container_width=True)
                st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), file_name=f"{selected}.csv", mime="text/csv", key="btn_browse_download")
            except Exception as e:
                st.error(str(e))
