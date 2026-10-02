import time
from datetime import datetime

import streamlit as st
from common import H, answer_box, ask_from, toggle_irr
from farm_utils import AMBER, GREEN, RED, card_html, get_forecast, num, readings, thresholds

S, sm, t, h, rain, ph = readings()
lo, hi = thresholds()
fc = get_forecast()
irr = bool(st.session_state.get("irr", False))
n_al = int(num(S["n_al"]))

if "_cmd_log" not in st.session_state:
    st.session_state["_cmd_log"] = [f"{datetime.now():%H:%M:%S} System ready — saare agents standby par hain"]


def log(msg):
    st.session_state["_cmd_log"] = (st.session_state["_cmd_log"] + [f"{datetime.now():%H:%M:%S} {msg}"])[-40:]


def conf_from(dist, scale=0.9):
    return int(min(97, 62 + dist * scale))


def run_all():
    st.session_state["_cmd_run"] = True


# ---- tomorrow ki barish ka imkaan
rain_prob = None
if fc is not None and len(fc[0]) > 1:
    rain_prob = int(fc[0]["precipitation_probability_max"].iloc[1])
rain_hold = rain_prob is not None and rain_prob >= 60

# ---- 1. Crop Health Agent
score = 100 - max(0, lo - sm) * 1.2 - max(0, sm - 85) * 0.8 - max(0, t - 35) * 2 - max(0, 12 - t) * 2 \
    - max(0, 6.0 - ph) * 10 - max(0, ph - 7.5) * 10
score = int(max(0, min(100, score)))
if score >= 75:
    crop_dec, crop_col = f"Healthy (score {score})", GREEN
elif score >= 50:
    crop_dec, crop_col = f"Needs attention (score {score})", AMBER
else:
    crop_dec, crop_col = f"Stress detected (score {score})", RED
crop_conf = conf_from(abs(score - 62))

# ---- 2. Weather Agent
if rain_prob is None:
    wx_dec, wx_col, wx_conf = "Forecast unavailable", AMBER, 40
elif rain_hold:
    wx_dec, wx_col = f"Barish ka imkaan {rain_prob}% — irrigation rokein", AMBER
    wx_conf = int(min(95, 50 + abs(rain_prob - 50) * 0.9))
else:
    wx_dec, wx_col = f"Mausam saaf (barish {rain_prob}%)", GREEN
    wx_conf = int(min(95, 50 + abs(rain_prob - 50) * 0.9))

# ---- 3. Irrigation Agent
if sm < lo and rain_hold and sm > lo - 10:
    action, irr_dec, irr_col = "hold", "Wait — barish aane wali hai", AMBER
elif sm < lo:
    action, irr_dec, irr_col = "start", f"Start irrigation (moisture {sm:.0f}% < {lo}%)", RED
elif sm >= hi:
    action, irr_dec, irr_col = "stop", f"Irrigation band (moisture {sm:.0f}% ≥ {hi}%)", GREEN
else:
    action, irr_dec, irr_col = "hold", f"Hold — moisture theek ({sm:.0f}%)", GREEN
irr_conf = conf_from(min(abs(sm - lo), abs(sm - hi)) * 2)

# ---- 4. Risk Agent
risk = (35 if sm < lo else 0) + (25 if t > 38 else 0) + (15 if ph < 6 or ph > 7.5 else 0) \
    + (10 if h < 30 else 0) + min(30, n_al * 10)
if risk < 25:
    risk_dec, risk_col = f"Low risk ({risk}/100)", GREEN
elif risk < 55:
    risk_dec, risk_col = f"Medium risk ({risk}/100)", AMBER
else:
    risk_dec, risk_col = f"High risk ({risk}/100)", RED
risk_conf = conf_from(abs(risk - 40) * 0.8)

# ---- 5. Farm Assistant
ast_dec = "Sab theek hai" if (score >= 75 and risk < 25) else "Action zaroori hai"
ast_col = GREEN if ast_dec == "Sab theek hai" else AMBER
ast_conf = int((crop_conf + wx_conf + irr_conf + risk_conf) / 4)

agents = [
    ("🌱", "Crop Health", crop_dec, crop_conf, crop_col),
    ("⛅", "Weather", wx_dec, wx_conf, wx_col),
    ("💧", "Irrigation", irr_dec, irr_conf, irr_col),
    ("⚠️", "Risk", risk_dec, risk_conf, risk_col),
    ("🤖", "Farm Assistant", ast_dec, ast_conf, ast_col),
]

# ---- Auto Mode
auto = bool(st.session_state.get("auto_mode", False))
if auto:
    if action == "start" and not irr:
        toggle_irr()
        irr = True
        log("Auto Mode: Irrigation Agent ne irrigation SHURU kar di")
    elif action == "stop" and irr:
        toggle_irr()
        irr = False
        log("Auto Mode: Irrigation Agent ne irrigation BAND kar di")

# ---- Run all agents
if st.session_state.pop("_cmd_run", False):
    steps = [("Crop Health Agent", "sensor data analyse kar raha hai…"),
             ("Weather Agent", "forecast check kar raha hai…"),
             ("Irrigation Agent", "moisture aur rules compare kar raha hai…"),
             ("Risk Agent", "risk score nikal raha hai…"),
             ("Farm Assistant", "final mashwara tayyar kar raha hai…")]
    with st.spinner("Agents chal rahe hain…"):
        for n_, m_ in steps:
            log(f"{n_}: {m_}")
            time.sleep(0.3)
    for _, name, dec, conf, _ in agents:
        log(f"{name} → {dec} ({conf}%)")

# ---- UI
H('<div class="card"><h3>🧠 AI Command Center</h3>5 AI agents aapke farm ke live data par faisle lete hain. '
  "Auto Mode on karein to AI khud irrigation shuru ya band karega.</div>")

c1, c2, c3 = st.columns([2, 2, 3])
with c1:
    st.toggle("🤖 Auto Mode", key="auto_mode")
with c2:
    st.button("▶ Run all agents now", type="primary", on_click=run_all)
with c3:
    st.caption(f"Irrigation abhi: {'ON 💧' if irr else 'OFF'}  •  Rules: start < {lo}%, stop ≥ {hi}%")

cols = st.columns(5)
for col, (icon, name, dec, conf, color) in zip(cols, agents):
    with col:
        H(card_html(
            f"{icon} {name}",
            f'<div style="font-weight:700;color:{color};margin:6px 0;min-height:56px">{dec}</div>'
            f'<div style="font-size:12px;opacity:.8">Confidence: {conf}%</div>'
            f'<div style="background:rgba(255,255,255,.12);border-radius:8px;height:6px;margin-top:4px">'
            f'<div style="width:{conf}%;height:6px;border-radius:8px;background:{color}"></div></div>'))

lines = "<br>".join(reversed(st.session_state["_cmd_log"][-12:]))
H(card_html("📜 Live Activity Log",
            f'<div style="font-family:monospace;font-size:12px;line-height:1.7">{lines}</div>'))

H(card_html("💬 Command Center se poochen", "Koi bhi sawal poochen, jawab current sensor values ke hisaab se aayega."))
st.text_input("Command", key="cmd_in", placeholder="Kya aaj irrigation karni chahiye?", label_visibility="collapsed",
              on_change=ask_from, args=("cmd_in", "cmd_out"))
st.button("➤ Ask", key="cmd_btn", type="primary", on_click=ask_from, args=("cmd_in", "cmd_out"))
answer_box("cmd_out")
