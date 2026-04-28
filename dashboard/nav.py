import streamlit as st


def render_nav():
    cols = st.columns(3)
    with cols[0]:
        st.page_link("app.py", label="Data Notes", icon="📋")
    with cols[1]:
        st.page_link("pages/1_Home.py", label="Main Overview", icon="🏠")
    with cols[2]:
        st.page_link("pages/2_Year_Details.py", label="Results by Year", icon="📅")
    st.divider()
