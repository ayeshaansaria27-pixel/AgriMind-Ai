
from datetime import date, timedelta
import base64
import json
import re
 
import streamlit as st
from groq import Groq
 
from common import H, answer_box
from farm_utils import ask_with, num, readings
 
 
# ==========================================================
# GROQ AI
# ==========================================================
 
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
 
# Qwen 3.8 27B is multimodal (image + text) and supports JSON mode
VISION_MODEL = "qwen/qwen3.8-27b"
 
 
def _parse_json(text: str) -> dict:
    """Extracts JSON from the model response (works even with thinking/extra text)."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise
 
 
def analyze_leaf(image_bytes: bytes, crop: str) -> dict:
    b64 = base64.b64encode(image_bytes).decode()
 
    prompt = (
        f"You are a plant pathologist. This is a {crop} leaf/plant photo. "
        "Analyze the visible symptoms carefully. "
        "Reply ONLY with JSON: "
        '{"status":"Healthy|Needs Attention|Critical",'
        '"disease":"name or None",'
        '"confidence":0,'
        '"symptoms":"short",'
        '"advice":"short, practical, for a Pakistani farmer"}'
        " confidence must be a number from 0 to 100."
    )
 
    resp = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ],
        temperature=0.2,
        max_tokens=900,
        response_format={"type": "json_object"},
    )
 
    return _parse_json(resp.choices[0].message.content)
 
 
# ==========================================================
# FARM DATA
# ==========================================================
 
S, sm, t, h, rain, ph = readings()
crop, stage = str(S["crop"]), S["stage"]
 
STAGES = [
    "Germination",
    "Seedling",
    "Vegetative",
    "Flowering",
    "Fruiting",
    "Maturity",
]
 
PROFILES = {
    "wheat": ((30, 60), (12, 25), (6.0, 7.5), 140),
    "rice": ((60, 90), (20, 35), (5.5, 7.0), 130),
    "cotton": ((35, 65), (21, 35), (5.8, 8.0), 180),
    "maize": ((40, 70), (18, 32), (5.8, 7.5), 110),
    "sugarcane": ((50, 80), (20, 35), (6.0, 7.5), 330),
    "tomato": ((50, 75), (18, 30), (6.0, 6.8), 110),
}
 
DEFAULT_PROFILE = ((35, 65), (18, 32), (6.0, 7.5), 120)
 
prof = next(
    (v for k, v in PROFILES.items() if k in crop.lower()),
    DEFAULT_PROFILE
)
 
(m_lo, m_hi), (t_lo, t_hi), (p_lo, p_hi), total_days = prof
 
 
# ==========================================================
# GROWTH STAGE PROGRESS
# ==========================================================
 
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
    return (
        "✅ OK"
        if lo_ <= v <= hi_
        else ("⬇️ Low" if v < lo_ else "⬆️ High")
    )
 
 
# ==========================================================
# CROP INTELLIGENCE HEADER
# ==========================================================
 
H(
    f'<div class="card"><h3>🌾 Crop Intelligence</h3>'
    f'Crop: <b>{crop}</b> • Stage: <b>{stage}</b></div>'
)
 
 
# ==========================================================
# OPTIMAL RANGES
# ==========================================================
 
c1, c2 = st.columns(2)
 
with c1:
    H('<div class="card"><h3>📏 Optimal ranges vs current</h3></div>')
 
    st.dataframe(
        [
            {
                "Parameter": "Soil moisture (%)",
                "Current": f"{sm:.0f}",
                "Optimal": f"{m_lo}–{m_hi}",
                "Status": status(sm, m_lo, m_hi),
            },
            {
                "Parameter": "Temperature (°C)",
                "Current": f"{t:.1f}",
                "Optimal": f"{t_lo}–{t_hi}",
                "Status": status(t, t_lo, t_hi),
            },
            {
                "Parameter": "Soil pH",
                "Current": f"{ph:.1f}",
                "Optimal": f"{p_lo}–{p_hi}",
                "Status": status(ph, p_lo, p_hi),
            },
        ],
        hide_index=True,
    )
 
 
# ==========================================================
# GROWTH PROGRESS
# ==========================================================
 
with c2:
    H('<div class="card"><h3>📈 Growth progress</h3></div>')
 
    st.progress(
        min(1.0, max(0.0, progress)),
        text=f"{int(progress * 100)}% complete"
    )
 
    st.metric(
        "Estimated harvest",
        harvest.strftime("%d %b %Y"),
        f"~{days_left} days left",
        delta_color="off",
    )
 
    st.caption("Estimate is based on the crop's typical growth cycle.")
 
 
# ==========================================================
# DISEASE RISK
# ==========================================================
 
fungal = (
    "High"
    if (h >= 80 and 18 <= t <= 30)
    else ("Medium" if h >= 65 else "Low")
)
 
H('<div class="card"><h3>🧪 Fertilizer & Disease risk</h3></div>')
 
d1, d2 = st.columns(2)
 
d1.metric(
    "Fungal disease risk (from humidity/temp)",
    fungal
)
 
d2.metric(
    "Soil pH status",
    status(ph, p_lo, p_hi)
)
 
 
# ==========================================================
# AI FERTILIZER + DISEASE ADVICE
# ==========================================================
 
ctx = (
    f"Crop: {crop}, stage: {stage}, "
    f"soil moisture {sm:.0f}%, temperature {t:.1f}C, "
    f"humidity {h:.0f}%, pH {ph:.1f}."
)
 
b1, b2 = st.columns(2)
 
with b1:
    st.button(
        "🧴 AI Fertilizer advice",
        type="primary",
        on_click=ask_with,
        args=(
            ctx
            + " Which fertilizer (NPK) should be applied at this stage, "
              "in what quantity, and when? Answer in short bullet points.",
            "ci_fert",
        ),
    )
 
    answer_box("ci_fert")
 
 
with b2:
    st.button(
        "🦠 AI Disease risk",
        type="primary",
        on_click=ask_with,
        args=(
            ctx
            + " Which diseases or pests are a risk in this weather, "
              "and how can they be prevented? Answer in short bullet points.",
            "ci_dis",
        ),
    )
 
    answer_box("ci_dis")
 
 
# ==========================================================
# AI LEAF PHOTO DETECTION
# ==========================================================
 
H(
    '<div class="card"><h3>📷 Detect disease from a leaf photo</h3>'
    'Upload a photo or take one with the camera, then press Detect.</div>'
)
 
src = st.radio(
    "Source",
    ["Upload photo", "Camera"],
    horizontal=True,
    label_visibility="collapsed",
)
 
if src == "Upload photo":
    img = st.file_uploader(
        "Leaf photo",
        type=["jpg", "jpeg", "png"],
        key="leaf_up",
    )
else:
    img = st.camera_input(
        "Camera",
        key="leaf_cam",
    )
 
 
# ==========================================================
# ANALYZE LEAF
# ==========================================================
 
if img is not None:
 
    st.image(img, width=320)
 
    if st.button(
        "🔍 Analyze",
        type="primary",
        key="leaf_btn",
    ):
 
        with st.spinner("AI is analyzing the photo…"):
 
            try:
                result = analyze_leaf(
                    img.getvalue(),
                    crop
                )
 
                st.session_state["ci_leaf_result"] = result
 
                # Save status for Field View
                st.session_state[f"status_{crop}"] = result["status"]
 
            except Exception as e:
 
                st.error(
                    "There was a problem with the AI analysis. "
                    "Please check the API key and the image."
                )
                st.caption(f"Detail: {e}")
 
                st.session_state["ci_leaf_result"] = None
 
 
# ==========================================================
# DETECTION RESULT
# ==========================================================
 
result = st.session_state.get("ci_leaf_result")
 
if result:
 
    H(
        '<div class="card"><h3>🔎 AI Detection Result</h3></div>'
    )
 
    r1, r2 = st.columns(2)
 
    with r1:
        st.metric(
            "Status",
            result.get("status", "Unknown")
        )
 
    with r2:
        st.metric(
            "Confidence",
            f"{result.get('confidence', 0)}%"
        )
 
    st.write(
        f"**🦠 Disease:** "
        f"{result.get('disease', 'None')}"
    )
 
    st.write(
        f"**🔍 Symptoms:** "
        f"{result.get('symptoms', 'Not available')}"
    )
 
    st.info(
        f"💡 **Advice:** "
        f"{result.get('advice', 'No advice available')}"
    )
 
