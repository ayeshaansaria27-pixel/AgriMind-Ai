# ==========================================================
# AGRIMIND AI - STREAMLIT DASHBOARD (v3, multipage)
# Run locally:  pip install -r requirements.txt && streamlit run app.py
#
# app.py is the single entrypoint / router:
#   sidebar.render_sidebar() -> st.navigation(pages from common.PAGES)
#   shared header / status bar / farm panel wrap every page
#   pg.run() executes the selected views/<page>.py
# ==========================================================
import streamlit as st

st.set_page_config(page_title="AgriMind AI", page_icon="🌿", layout="wide")  # must be the first Streamlit call

from common import (CSS, PAGES, STATUSBAR, H, answer_box, do_search, get_state, header_html,
                    init_state, refresh_analysis)
from sidebar import render_sidebar

init_state()
S = get_state()          # live weather sync + cached AI analysis (shared by all pages)
st.markdown(CSS, unsafe_allow_html=True)

# ---------------- SIDEBAR + NAVIGATION ----------------
pages, pg = render_sidebar(S["n_al"])

# ---------------- HEADER ----------------
brand_h, user_h = header_html()
c1, c2, c3 = st.columns([3, 5, 3], vertical_alignment="center")
with c1:
    H(brand_h)
with c2:
    st.text_input("search", key="search", on_change=do_search, label_visibility="collapsed",
                  placeholder="🔍 Search pages or ask AI (e.g. alerts, irrigation, 'when to water tomato?') and press Enter")
with c3:
    H(user_h)

# search box asked for a page change -> navigate (st.switch_page cannot run inside a callback reliably)
target = st.session_state.get("goto")
if target:
    st.session_state.goto = None
    st.switch_page(next(p for p, (_, _, f, _) in zip(pages, PAGES) if f == target))

answer_box("search_ans")

# ---------------- CURRENT PAGE (views/*.py) ----------------
pg.run()

# ---------------- FARM DATA PANEL ----------------
weather = S["weather"]
with st.expander("📡 Farm Intelligence & Simulation", expanded=False):
    st.caption("Live mode uses the selected farm location for weather. Manual values are available for hackathon simulation/testing.")
    data_mode = st.radio("Data Mode", ["🌐 Live Weather", "🧪 Simulation"], horizontal=True, key="data_mode")
    if data_mode == "🧪 Simulation":
        r1 = st.columns(3)
        r1[0].slider("💧 Soil Moisture (%)", 0, 100, key="sm")
        r1[1].slider("🌡️ Temperature (°C)", 0, 50, key="t")
        r1[2].slider("💦 Humidity (%)", 0, 100, key="h")
        r2 = st.columns(2)
        r2[0].slider("🌧️ Rain Probability (%)", 0, 100, key="rain")
        r2[1].slider("🧪 Soil pH", 0.0, 14.0, step=0.1, key="ph")
    else:
        st.success(
            f"🌐 Live weather connected for **{st.session_state.location_name}**. "
            f"Temperature, humidity and rain probability update automatically."
        )
        if weather:
            st.write(
                f"**Current:** {weather['icon']} {weather['temperature']:.1f}°C · "
                f"{weather['condition']} · 💧 {weather['humidity']:.0f}% humidity · "
                f"🌧️ {weather['rain']:.0f}% rain probability"
            )
        else:
            st.warning("Live weather temporarily unavailable. Showing the last/default farm values.")
    r3 = st.columns(2)
    r3[0].selectbox("🌱 Crop", ["Tomato", "Wheat", "Rice", "Corn", "Potato", "Lettuce"], key="crop")
    r3[1].selectbox("🌿 Growth Stage", ["Seedling", "Vegetative", "Flowering", "Fruiting", "Mature"], key="stage")
    st.button("🤖 Analyze Farm with AI", type="primary", on_click=refresh_analysis)

H(STATUSBAR(S["n_al"]))