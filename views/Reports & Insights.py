
import streamlit as st
from common import H, answer_box, ask_report

H('<div class="card"><h3>📄 Reports & Insights</h3>Generate an AI report from the current farm data.</div>')
st.button("📄 Generate AI Report", type="primary", on_click=ask_report)
answer_box("rep_out")
 
