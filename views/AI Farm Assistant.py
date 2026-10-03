
import streamlit as st
from common import H, answer_box, ask_from

H('<div class="card"><h3>🤖 AI Farm Assistant</h3>Ask anything about your farm. Answers are based on the current sensor values.</div>')
st.text_input("Your question", key="q2", placeholder="Why is my soil moisture low?", on_change=ask_from, args=("q2", "a2"))
st.button("➤ Ask AI", type="primary", on_click=ask_from, args=("q2", "a2"))
answer_box("a2")
 
