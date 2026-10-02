# ==========================================================
# SIDEBAR - navigation (13 pages) + System Overview card
# Pages themselves live in views/. To add a page: add a row in common.PAGES
# and create views/<file>.py
# ==========================================================
import streamlit as st
from common import PAGES, H, overview_html, show_location_controls

SIDEBAR_CSS = """<style>
section[data-testid="stSidebar"]{background:#061d12;border-right:1px solid rgba(60,200,120,.2)}
</style>"""


def build_pages():
    """One st.Page per sidebar item (each gets its own URL)."""
    return [st.Page(f"views/{f}.py", title=n, icon=ic, url_path=slug, default=(i == 0))
            for i, (ic, n, f, slug) in enumerate(PAGES)]


def render_sidebar(n_al):
    """Draw the sidebar. Returns (pages, current_page)."""
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
    pages = build_pages()
    pg = st.navigation(pages)          # sidebar navigation links
    with st.sidebar:
        H(overview_html(n_al))         # System Overview card under the links
        # The Settings page shows the same widgets in its body; render them only once (duplicate widget keys otherwise)
        if pg.url_path != "settings":
            with st.expander("⚙️ Farm Settings", expanded=False):
                show_location_controls()
    return pages, pg