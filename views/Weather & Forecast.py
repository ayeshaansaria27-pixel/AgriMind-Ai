
import streamlit as st
from common import H, answer_box
from farm_utils import ask_with, current_location, get_forecast, readings, thresholds, wx_icon

S, sm, t, h, rain, ph = readings()
lo, hi = thresholds()
place = current_location()[0]
fc = get_forecast()

H(f'<div class="card"><h3>⛅ Weather & Forecast</h3>7-day forecast: <b>{place}</b> (Open-Meteo)</div>')

if fc is None:
    H('<div class="card"><h3>⚠️ Could not load the forecast</h3>Check your internet connection, then reopen the page.</div>')
    st.stop()

daily = fc[0]
cols = st.columns(7)
for col, (_, r) in zip(cols, daily.iterrows()):
    with col:
        H(f'<div class="card" style="text-align:center;padding:10px"><b>{r["time"].strftime("%a")}</b><br>'
          f'<span style="font-size:11px;opacity:.7">{r["time"].strftime("%d %b")}</span>'
          f'<div style="font-size:28px">{wx_icon(r["weather_code"])}</div>'
          f'<b>{r["temperature_2m_max"]:.0f}°</b> / {r["temperature_2m_min"]:.0f}°<br>'
          f'🌧 {int(r["precipitation_probability_max"])}%<br>'
          f'💨 {r["wind_speed_10m_max"]:.0f} km/h<br>💧 {r["humidity"]:.0f}%</div>')

idx = daily["time"].dt.strftime("%a %d")
a, b = st.columns(2)
with a:
    H('<div class="card"><h3>🌡️ Temperature (°C)</h3></div>')
    st.line_chart(daily.set_index(idx)[["temperature_2m_max", "temperature_2m_min"]]
                  .rename(columns={"temperature_2m_max": "Max", "temperature_2m_min": "Min"}))
with b:
    H('<div class="card"><h3>🌧️ Rain (mm)</h3></div>')
    st.bar_chart(daily.set_index(idx)[["precipitation_sum"]].rename(columns={"precipitation_sum": "Rain (mm)"}))

# ---- irrigation advice (rules)
tips = []
p = [int(x) for x in daily["precipitation_probability_max"]]
if len(p) > 2:
    if p[1] < 50:
        line = "Irrigate tomorrow morning (6–9 AM)"
        line += f", but there is a {p[2]}% chance of rain on {daily['time'].iloc[2].strftime('%A')}, so do not water after that." if p[2] >= 60 else "."
        tips.append(line)
    else:
        tips.append(f"There is a {p[1]}% chance of rain tomorrow — do not irrigate tomorrow.")
    if sm < lo and p[0] < 50:
        tips.append(f"Moisture today is {sm:.0f}%, below the limit ({lo}%), and the chance of rain is low — irrigate this evening.")
    first_rain = next((i for i, x in enumerate(p) if x >= 60), None)
    if first_rain is not None:
        tips.append(f"There is a {p[first_rain]}% chance of rain on {daily['time'].iloc[first_rain].strftime('%A')} — do not over-water before then.")
    if daily["wind_speed_10m_max"].max() >= 30:
        tips.append("Strong winds are possible — drip/flood irrigation is better than sprinklers.")
    if daily["temperature_2m_max"].max() >= 40:
        tips.append("Heat may exceed 40°C — irrigate only early in the morning or in the evening.")
tips_html = "<br>".join("• " + x for x in tips)
H(f'<div class="card"><h3>💡 Irrigation advice</h3>{tips_html}</div>')

summary = "; ".join(f"{r['time'].strftime('%a')}: {r['temperature_2m_min']:.0f}-{r['temperature_2m_max']:.0f}C, rain {int(r['precipitation_probability_max'])}%"
                    for _, r in daily.iterrows())
st.button("🤖 Detailed AI advice", type="primary", on_click=ask_with,
          args=(f"7-day forecast for {place}: {summary}. My crop is {S['crop']} and soil moisture is {sm:.0f}%. "
                "Give an irrigation plan for the next 7 days in short bullet points.", "wx_out"))
answer_box("wx_out")
 
