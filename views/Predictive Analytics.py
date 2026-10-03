
import numpy as np
import pandas as pd
import streamlit as st
from common import H, answer_box
from farm_utils import ask_with, get_forecast, next_24h, readings, thresholds

S, sm, t, h, rain, ph = readings()
lo, hi = thresholds()
GAIN = 0.45  # % moisture per minute of irrigation (estimate)

H('<div class="card"><h3>🔮 Predictive Analytics</h3>Moisture prediction for the next 24 hours (based on weather and sensors).</div>')
plus20 = st.checkbox("What if I irrigate for 20 minutes now?", key="pred_irr")

fc = get_forecast()
if fc is not None:
    nx = next_24h(fc)
    labels = list(nx["time"].dt.strftime("%a %H:%M"))
    temps = list(nx["temperature_2m"])
    hums = list(nx["relative_humidity_2m"])
    rains = list(nx["precipitation"])
else:
    labels = list(pd.date_range(pd.Timestamp.now().floor("h"), periods=24, freq="h").strftime("%a %H:%M"))
    temps, hums, rains = [t] * 24, [h] * 24, [0.0] * 24
    st.info("Forecast not available — estimate is based only on current sensor values.")

n = min(24, len(labels), len(temps))
m = sm + (20 * GAIN if plus20 else 0)
preds = []
for i in range(n):
    loss = 0.18 + 0.035 * max(temps[i] - 18, 0) + 0.004 * max(60 - hums[i], 0)  # % per hour
    m = float(np.clip(m - loss + rains[i] * 3.0, 0, 100))
    preds.append(m)

chart = pd.DataFrame({"Predicted moisture (%)": preds, f"Irrigation limit ({lo}%)": [lo] * n}, index=labels[:n])
st.line_chart(chart)

below = [i for i, v in enumerate(preds) if v < lo]
stress_h = len(below)
c1, c2, c3 = st.columns(3)
if below:
    i0 = below[0]
    mins = max(5, int(round((hi - preds[i0]) / GAIN / 5.0)) * 5)
    c1.metric("When to water", labels[i0], f"~{mins} min irrigation", delta_color="off")
else:
    c1.metric("When to water", "Not needed in the next 24 hours")

risk = (stress_h * 4) + (25 if t > 38 else 0) + (15 if ph < 6 or ph > 7.5 else 0)
c2.metric("Risk", "Low" if risk < 25 else "Medium" if risk < 55 else "High", f"{min(100, risk)}/100", delta_color="off")
yield_idx = max(40, 100 - stress_h * 1.2 - max(0, t - 35) * 1.5 - max(0, 6 - ph) * 8 - max(0, ph - 7.5) * 8)
c3.metric("Yield index (relative)", f"{yield_idx:.0f}%")
st.caption("These estimates use a simple formula (moisture loss from heat, humidity and rain). Not a claim about actual yield.")

st.button("🤖 AI details", type="primary", on_click=ask_with,
          args=(f"Moisture prediction for the next 24 hours: from {sm:.0f}% now to {preds[-1]:.0f}%. Limit {lo}%. "
                f"{'Moisture will drop below the limit.' if below else 'It will not drop below the limit.'} "
                "What does this mean and what should I do? Answer in short bullet points.", "pred_out"))
answer_box("pred_out")
 
