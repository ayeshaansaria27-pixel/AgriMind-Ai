
import streamlit as st
from common import H, start_pump

H('<div class="card"><h3> Irrigation Automation</h3>Choose a zone, choose a duration and start the pump. Every action is recorded in the log below.</div>')
st.selectbox("Zone", ["Zone 1", "Zone 2", "Zone 3"], index=1, key="zone")
st.slider("Duration (minutes)", 5, 60, 15, step=5, key="mins")
st.button("▶ Start Pump", type="primary", on_click=start_pump)
st.text_area("Irrigation log", value=st.session_state.pump_log, height=150, disabled=True)
 
