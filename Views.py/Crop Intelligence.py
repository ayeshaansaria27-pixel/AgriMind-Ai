from datetime import date, timedelta

import streamlit as st
from common import H, answer_box
from farm_utils import ai_vision, ask_with, num, readings

S, sm, t, h, rain, ph = readings()
crop, stage = str(S["crop"]), S["stage"]

STAGES = ["Germination", "Seedling", "Vegetative", "Flowering", "Fruiting", "Maturity"]
# crop: (moisture range, temp range, ph range, total days)
PROFILES = {
    "wheat": ((30, 60), (12, 25), (6.0, 7.5), 140),
    "rice": ((60, 90), (20, 35), (5.5, 7.0), 130),
    "cotton": ((35, 65), (21, 35), (5.8, 8.0), 180),
    "maize": ((40, 70), (18, 32), (5.8, 7.5), 110),
    "sugarcane": ((50, 80), (20, 35), (6.0, 7.5), 330),
    "tomato": ((50, 75), (18, 30), (6.0, 6.8), 110),
}
DEFAULT_PROFILE = ((35, 65), (18, 32), (6.0, 7.5), 120)
prof = next((v for k, v in PROFILES.items() if k in crop.lower()), DEFAULT_PROFILE)
(m_lo, m_hi), (t_lo, t_hi), (p_lo, p_hi), total_days = prof

# ---- growth stage progress
progress = 0.5
try:
    v = float(stage)
    progress = v if 0 <= v <= 1 else min(1.0, v / 100)
except (TypeError, ValueError):
    sname = str(stage).strip().lower()
    for i, s in enumerate(STAGES):
        if sname and (s.lower() in sname or sname in s.lower()):
            progress = (i + 0.5) / len(STAGES)
            break
days_left = max(0, round(total_days * (1 - progress)))
harvest = date.today() + timedelta(days=days_left)


def status(v, lo_, hi_):
    return "✅ OK" if lo_ <= v <= hi_ else ("⬇️ Low" if v < lo_ else "⬆️ High")


H(f'<div class="card"><h3>🌾 Crop Intelligence</h3>Fasal: <b>{crop}</b> • Stage: <b>{stage}</b></div>')

c1, c2 = st.columns(2)
with c1:
    H('<div class="card"><h3>📏 Optimal ranges vs current</h3></div>')
    st.dataframe(
        [{"Parameter": "Soil moisture (%)", "Current": f"{sm:.0f}", "Optimal": f"{m_lo}–{m_hi}", "Status": status(sm, m_lo, m_hi)},
         {"Parameter": "Temperature (°C)", "Current": f"{t:.1f}", "Optimal": f"{t_lo}–{t_hi}", "Status": status(t, t_lo, t_hi)},
         {"Parameter": "Soil pH", "Current": f"{ph:.1f}", "Optimal": f"{p_lo}–{p_hi}", "Status": status(ph, p_lo, p_hi)}],
        hide_index=True)
with c2:
    H('<div class="card"><h3>📈 Growth progress</h3></div>')
    st.progress(min(1.0, max(0.0, progress)), text=f"{int(progress * 100)}% complete")
    st.metric("Harvest ka andaza", harvest.strftime("%d %b %Y"), f"~{days_left} din baqi", delta_color="off")
    st.caption("Andaza fasal ke aam growth cycle par mabni hai.")

# ---- disease risk (rule based) + AI advice
fungal = "High" if (h >= 80 and 18 <= t <= 30) else ("Medium" if h >= 65 else "Low")
H('<div class="card"><h3>🧪 Fertilizer & Disease risk</h3></div>')
d1, d2 = st.columns(2)
d1.metric("Fungal disease risk (humidity/temp se)", fungal)
d2.metric("Soil pH status", status(ph, p_lo, p_hi))

ctx = (f"Fasal: {crop}, stage: {stage}, soil moisture {sm:.0f}%, temperature {t:.1f}C, "
       f"humidity {h:.0f}%, pH {ph:.1f}.")
b1, b2 = st.columns(2)
with b1:
    st.button("🧴 AI Fertilizer advice", type="primary", on_click=ask_with,
              args=(ctx + " Is stage par kaun si khaad (NPK), kitni miqdar mein aur kab dalni chahiye? Chhote bullet points mein batayen.", "ci_fert"))
    answer_box("ci_fert")
with b2:
    st.button("🦠 AI Disease risk", type="primary", on_click=ask_with,
              args=(ctx + " Is mausam mein kin bimariyon ya keeron ka khatra hai aur bachao kaise karein? Chhote bullet points mein batayen.", "ci_dis"))
    answer_box("ci_dis")

# ---- leaf photo detection
H('<div class="card"><h3>📷 Patte ki photo se bimari detect karein</h3>Photo upload karein ya camera se len, phir Detect dabayen.</div>')
src = st.radio("Source", ["Upload photo", "Camera"], horizontal=True, label_visibility="collapsed")
img = st.file_uploader("Leaf photo", type=["jpg", "jpeg", "png"], key="leaf_up") if src == "Upload photo" \
    else st.camera_input("Camera", key="leaf_cam")
if img is not None:
    st.image(img, width=320)
    if st.button("🔍 Detect", type="primary", key="leaf_btn"):
        prompt = (f"You are an expert agronomist. This is a photo of a plant leaf (farm crop: {crop}). "
                  "Identify the crop, whether it is healthy or has a disease/pest/nutrient deficiency, the likely cause, "
                  "your confidence in %, and the treatment (organic and chemical). Answer in simple Roman Urdu with short bullet points.")
        with st.spinner("AI photo ka tajziya kar raha hai…"):
            st.session_state["ci_leaf"] = ai_vision(img.getvalue(), prompt, getattr(img, "type", None) or "image/jpeg")
if st.session_state.get("ci_leaf"):
    H('<div class="card"><h3>🔎 Detection result</h3></div>')
    st.markdown(st.session_state["ci_leaf"])
