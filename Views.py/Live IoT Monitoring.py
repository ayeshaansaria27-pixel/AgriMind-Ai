import streamlit as st
from common import H
from farm_utils import devices_df, get_history, readings

S, sm, t, h, rain, ph = readings()
df = devices_df(only_sensors=True)

H('<div class="card"><h3>📡 Live IoT Monitoring</h3>Saare sensors ki live halat: status, battery, signal aur taza readings.</div>')

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total sensors", len(df))
m2.metric("Online", int((df["Status"] == "🟢 Online").sum()))
m3.metric("Offline", int((df["Status"] == "🔴 Offline").sum()))
m4.metric("Low battery (<20%)", int((df["Battery (%)"] < 20).sum()))

st.dataframe(
    df, hide_index=True,
    column_config={"Battery (%)": st.column_config.ProgressColumn("Battery", min_value=0, max_value=100, format="%d%%")},
)
st.button("🔄 Refresh now")

hist = get_history(S)
a, b = st.columns(2)
with a:
    H('<div class="card"><h3>💧 Soil Moisture (live)</h3></div>')
    st.line_chart(hist[["Soil Moisture (%)"]])
with b:
    H('<div class="card"><h3>🌡️ Temperature (live)</h3></div>')
    st.line_chart(hist[["Temperature (°C)"]], color="#ff8c42")
st.caption("Har refresh par chart mein nayi reading jud jati hai.")
