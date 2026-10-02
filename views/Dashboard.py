import streamlit as st
from common import (CHIPS, WORKFLOW, H, alerts_html, answer_box, ask_chip, ask_from, decision_html,
                    field_html, get_state, health_html, hero_html, metrics_html, sensors_html, toggle_irr)

S = get_state()
sm, t, h, rain, ph, crop, stage = (S[k] for k in ("sm", "t", "h", "rain", "ph", "crop", "stage"))
res, weather, n_al = S["res"], S["weather"], S["n_al"]

left, right = st.columns([7, 3])
with left:
    H(hero_html(n_al, weather) + metrics_html(sm, t, h, rain, ph))
    a, b = st.columns([5, 6])
    with a:
        H(sensors_html(sm, t, h, ph, weather))
    with b:
        H(health_html(res, crop, stage))
    mode = st.radio("View", ["Live View", "Satellite View"], horizontal=True, label_visibility="collapsed")
    H(field_html(sm, crop, mode, st.session_state.irr, S["sat_url"], st.session_state.location_name))
    H(WORKFLOW)
with right:
    H(decision_html(res, rain))
    st.button("⏹ Stop Irrigation" if st.session_state.irr else "💧 Start Irrigation", key="irr_btn", type="primary", on_click=toggle_irr)
    H(alerts_html(res))
    H('<div class="card"><h3>🤖 AI Farm Assistant</h3><div style="background:rgba(46,226,122,.12);border-radius:12px;padding:10px">'
      "I'm your AgriMind AI assistant. You can ask me anything about your farm, weather, crops, or system status.</div></div>")
    for j, c in enumerate(CHIPS):
        st.button(c, key=f"chip{j}", on_click=ask_chip, args=(c,))
    st.text_input("Question", key="chat_in", placeholder="Type your question...", label_visibility="collapsed",
                  on_change=ask_from, args=("chat_in", "chat_out"))
    st.button("➤ Ask", key="chat_btn", type="primary", on_click=ask_from, args=("chat_in", "chat_out"))
    answer_box("chat_out")
