import streamlit as st
from common import H, answer_box
from farm_utils import ask_with, current_location, get_forecast, readings, thresholds, wx_icon

S, sm, t, h, rain, ph = readings()
lo, hi = thresholds()
place = current_location()[0]
fc = get_forecast()

H(f'<div class="card"><h3>⛅ Weather & Forecast</h3>7 din ki forecast: <b>{place}</b> (Open-Meteo)</div>')

if fc is None:
    H('<div class="card"><h3>⚠️ Forecast load nahi ho saki</h3>Internet connection check karein, phir page dobara kholen.</div>')
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
    H('<div class="card"><h3>🌧️ Barish (mm)</h3></div>')
    st.bar_chart(daily.set_index(idx)[["precipitation_sum"]].rename(columns={"precipitation_sum": "Rain (mm)"}))

# ---- irrigation advice (rules)
tips = []
p = [int(x) for x in daily["precipitation_probability_max"]]
if len(p) > 2:
    if p[1] < 50:
        line = "Kal subah (6–9 baje) irrigation karein"
        line += f", {daily['time'].iloc[2].strftime('%A')} ko barish ka imkaan {p[2]}% hai isliye uske baad pani na dein." if p[2] >= 60 else "."
        tips.append(line)
    else:
        tips.append(f"Kal barish ka imkaan {p[1]}% hai — kal irrigation na karein.")
    if sm < lo and p[0] < 50:
        tips.append(f"Aaj moisture {sm:.0f}% (limit {lo}%) se kam hai aur barish ka imkaan kam hai — aaj shaam irrigation karein.")
    first_rain = next((i for i, x in enumerate(p) if x >= 60), None)
    if first_rain is not None:
        tips.append(f"{daily['time'].iloc[first_rain].strftime('%A')} ko barish ka imkaan {p[first_rain]}% hai — us se pehle zyada pani na dein.")
    if daily["wind_speed_10m_max"].max() >= 30:
        tips.append("Tez hawa ka imkaan hai — sprinkler ki jagah drip/flood irrigation behtar rahegi.")
    if daily["temperature_2m_max"].max() >= 40:
        tips.append("Garmi 40°C se oopar jaa sakti hai — irrigation sirf subah sawere ya shaam ko karein.")
tips_html = "<br>".join("• " + x for x in tips)
H(f'<div class="card"><h3>💡 Irrigation salah</h3>{tips_html}</div>')

summary = "; ".join(f"{r['time'].strftime('%a')}: {r['temperature_2m_min']:.0f}-{r['temperature_2m_max']:.0f}C, barish {int(r['precipitation_probability_max'])}%"
                    for _, r in daily.iterrows())
st.button("🤖 AI se detailed salah", type="primary", on_click=ask_with,
          args=(f"{place} ki 7 din ki forecast: {summary}. Meri fasal {S['crop']} hai aur soil moisture {sm:.0f}% hai. "
                "Agle 7 din ke liye irrigation ka plan chhote bullet points mein batayen.", "wx_out"))
answer_box("wx_out")
