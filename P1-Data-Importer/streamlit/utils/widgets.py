# utils/widgets.py

import streamlit as st

def inject_base_css():
    # Optional: put global CSS here
    st.markdown(
        """
        <style>
        /* basic padding so things don't touch edges */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def inject_topbar_css():
    # Optional: style for the top bar if you want
    st.markdown(
        """
        <style>
        /* simple top bar styling */
        .st-emotion-cache-1v0mbdj {
            background-color: #f5f5f5;
            padding: 0.5rem;
            border-bottom: 1px solid #ddd;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
