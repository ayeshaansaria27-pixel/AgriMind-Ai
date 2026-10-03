
import numpy as np
import streamlit as st
from common import H
from farm_utils import AMBER, GREEN, RED, readings, thresholds

S, sm, t, h, rain, ph = readings()
lo, hi = thresholds()

# 3x3 zones: live values + a small variation in each zone
rng = np.random.default_rng(11)
off_m, off_t = rng.normal(0, 6, 9), rng.normal(0, 1.5, 9)
zones = {}
for i in range(1, 10):
    m = float(np.clip(sm + off_m[i - 1], 3, 98))
    tp = t + float(off_t[i - 1])
    health = float(np.clip(100 - abs(m - (lo + hi) / 2) * 1.6 - max(0, tp - 32) * 3 - max(0, 15 - tp) * 3, 0, 100))
    zones[i] = {"moisture": m, "temperature": tp, "health": health}

if "twin_zone" not in st.session_state:
    st.session_state["twin_zone"] = 5


def pick(i):
    st.session_state["twin_zone"] = i


def color_of(metric, v):
    """Heat map colour as (emoji, hex)."""
    if metric == "Moisture":
        return ("🔴", RED) if v < lo else ("🟡", AMBER) if v < lo + 10 else ("🔵", "#4da3ff") if v > 80 else ("🟢", GREEN)
    if metric == "Temperature":
        return ("🔵", "#4da3ff") if v < 15 else ("🟢", GREEN) if v <= 32 else ("🟡", AMBER) if v <= 38 else ("🔴", RED)
    return ("🔴", RED) if v < 50 else ("🟡", AMBER) if v < 75 else ("🟢", GREEN)


H('<div class="card"><h3>🗺️ Field Digital Twin <span style="font-size:12px;opacity:.7">(Beta)</span></h3>'
  "Click a zone, switch the heat map and run a what-if.</div>")

metric = st.radio("Heat map", ["Moisture", "Temperature", "Health"], horizontal=True, key="twin_metric")
key = metric.lower()
unit = {"Moisture": "%", "Temperature": "°C", "Health": "/100"}[metric]

left, right = st.columns([3, 2])
with left:
    for r in range(3):
        cols = st.columns(3)
        for c in range(3):
            i = r * 3 + c + 1
            v = zones[i][key]
            emoji, _ = color_of(metric, v)
            cols[c].button(f"{emoji} Zone {i} · {v:.0f}{unit}", key=f"tw{i}", on_click=pick, args=(i,),
                           type="primary" if st.session_state["twin_zone"] == i else "secondary")
    st.caption("🟢 OK  🟡 watch  🔴 danger  🔵 too high/low")

z = st.session_state["twin_zone"]
zd = zones[z]
with right:
    H(f'<div class="card"><h3>📍 Zone {z} details</h3></div>')
    st.metric("Soil moisture", f"{zd['moisture']:.0f}%")
    st.metric("Temperature", f"{zd['temperature']:.1f}°C")
    st.metric("Health score", f"{zd['health']:.0f}/100")

H('<div class="card"><h3>🔮 What-if: irrigation</h3></div>')
mins = st.slider("Irrigation (minutes)", 5, 60, 20, step=5, key="twin_mins")
GAIN = 0.45  # approx. % moisture per minute (estimate)
new_m = min(95.0, zd["moisture"] + mins * GAIN)
w1, w2 = st.columns(2)
w1.metric(f"Zone {z} moisture {mins} min later", f"{new_m:.0f}%", f"{new_m - zd['moisture']:+.0f}%")
with w2:
    if new_m > hi + 15:
        st.warning("Too much water — risk of waterlogging.")
    elif new_m >= hi:
        st.success("Moisture will reach the optimal range.")
    else:
        st.info(f"Still below {hi}% — increase the duration.")
st.caption("Estimate: 1 minute of irrigation ≈ 0.45% moisture. This will improve once real zone sensors are installed.")
 
