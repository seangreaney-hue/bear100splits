import streamlit as st

_WIDGET_CSS = """
<style>
/* Selectbox: visible border so the control reads as a control on dark bg */
div[data-baseweb="select"] > div:first-child {
    border: 1px solid #4a5168 !important;
}
div[data-baseweb="select"] > div:first-child:hover {
    border-color: #f0a500 !important;
}
</style>
"""


def render_nav():
    st.markdown(_WIDGET_CSS, unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        st.page_link("app.py", label="Data Notes", icon="📋")
    with cols[1]:
        st.page_link("pages/1_Home.py", label="Main Overview", icon="🏠")
    with cols[2]:
        st.page_link("pages/2_Year_Details.py", label="Results by Year", icon="📅")
    st.divider()
