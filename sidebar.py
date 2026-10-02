# ==========================================================
# SIDEBAR - navigation + System Overview card
# Pages live inside the views/ folder.
# ==========================================================

import os
import streamlit as st
from common import PAGES, H, overview_html, show_location_controls


SIDEBAR_CSS = """<style>
section[data-testid="stSidebar"]{
    background:#061d12;
    border-right:1px solid rgba(60,200,120,.2)
}
</style>"""


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIEWS_DIR = os.path.join(BASE_DIR, "views")


def build_pages():
    """Create Streamlit pages from the actual files inside views/."""

    pages = []

    for i, (ic, title, filename, slug) in enumerate(PAGES):
        page_file = os.path.join(VIEWS_DIR, f"{filename}.py")

        if not os.path.isfile(page_file):
            continue

        pages.append(
            st.Page(
                page_file,
                title=title,
                icon=ic,
                url_path=slug,
                default=(i == 0)
            )
        )

    return pages


def render_sidebar(n_al):
    """Draw the sidebar and return pages + current page."""

    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)

    pages = build_pages()
    pg = st.navigation(pages)

    with st.sidebar:
        H(overview_html(n_al))

        if pg.url_path != "settings":
            with st.expander("⚙️ Farm Settings", expanded=False):
                show_location_controls()

    return pages, pg

