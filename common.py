
import os
import re
import json
import base64
import random
 
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
 
import streamlit as st
from groq import Groq
 
 
DEFAULT_FARMER_NAME = "Ayesha Khan"
DEFAULT_LOCATION = "Karachi, Pakistan"
DEFAULT_LAT, DEFAULT_LON = 24.8607, 67.0011
 
BASE = os.path.dirname(os.path.abspath(__file__))
 
HERO_IMG, FIELD_IMG, AVATAR_IMG = (
    os.path.join(BASE, f)
    for f in ("hero.jpg", "field.jpg", "avatar.jpg")
)
 
 
# ==========================================================
# GROQ API CONFIGURATION
# ==========================================================
 
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
 
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
 
 
# ==========================================================
# GROQ AI
# ==========================================================
 
def ask_ai(prompt):
    """Send prompt to Groq AI."""
 
    if client is None:
        raise RuntimeError("GROQ_API_KEY is not configured.")
 
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AgriMind AI, an intelligent "
                    "agriculture assistant. "
                    "Give practical, concise and "
                    "data-driven agricultural advice."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
 
    return response.choices[0].message.content
 
 
def ctx(sm, t, h, rain, ph, crop, stage):
 
    loc = st.session_state.get("location_name", DEFAULT_LOCATION)
 
    return (
        f"Farm location: {loc}. "
        f"Crop: {crop} ({stage}), "
        f"soil moisture {sm}%, "
        f"temperature {t}°C, "
        f"humidity {h}%, "
        f"rain probability {rain}%, "
        f"soil pH {ph}."
    )
 
 
# ==========================================================
# RULE-BASED FARM ANALYSIS
# ==========================================================
 
def rule_based(sm, t, h, rain, ph):
 
    score = 100
    alerts = []
 
    if sm < 35:
        score -= 20
        alerts.append(f"Low Soil Moisture|{sm:.0f}% detected (Critical)")
 
    elif sm > 60:
        score -= 10
        alerts.append(f"Soil Too Wet|{sm:.0f}% detected")
 
    if t > 30:
        score -= 12
        alerts.append(
            f"High Temperature|{t:.0f}°C detected (above optimal range)"
        )
 
    elif t < 20:
        score -= 8
        alerts.append(f"Low Temperature|{t:.0f}°C detected")
 
    if h < 40 or h > 70:
        score -= 6
        alerts.append(f"Humidity Alert|{h:.0f}% out of range")
 
    if ph < 6.0 or ph > 7.5:
        score -= 8
        alerts.append(f"pH Alert|pH {ph} out of range")
 
    if rain > 60:
        alerts.append(
            f"Rain Expected|{rain:.0f}% probability in next 12 hours"
        )
 
    need_irrigation = sm < 45 and rain < 50
 
    return {
        "crop_health": max(score, 0),
 
        "irrigation": (
            "Irrigation Recommended"
            if need_irrigation
            else "No Irrigation Needed"
        ),
 
        "irrigation_reason": (
            "Soil moisture is slightly low and temperature is high. "
            "No significant rainfall is expected in the next 24 hours."
            if need_irrigation
            else "Soil moisture is acceptable or rain is likely soon."
        ),
 
        "risk_level": (
            "Low" if score >= 80
            else "Medium" if score >= 60
            else "High"
        ),
 
        "alerts": alerts,
 
        "confidence": 92 if need_irrigation else 88,
 
        "source": "Rule engine",
 
        "recommendations": [
            "Maintain soil moisture between 35% - 60%.",
            "Avoid excessive irrigation during high temperature.",
            "Monitor crop condition regularly.",
            "Consider organic fertilizer when appropriate.",
        ],
    }
 
 
# ==========================================================
# AI FARM ANALYSIS
# ==========================================================
 
@st.cache_data(show_spinner="🤖 AI is analyzing the farm...", ttl=900)
def analyze_farm(sm, t, h, rain, ph, crop, stage, ai_on=True):
 
    # Always create safe rule-based result first
    base = rule_based(sm, t, h, rain, ph)
 
    # If AI is disabled
    if not ai_on:
        return base
 
    # If Groq API is unavailable
    if client is None:
        base["source"] = "Rule engine"
        base["ai_error"] = "GROQ_API_KEY is not configured."
        return base
 
    # AI Prompt
    prompt = (
        ctx(sm, t, h, rain, ph, crop, stage)
        + """
 
You are analyzing a farm for AgriMind AI.
 
Use the supplied farm data.
 
Return ONLY valid JSON.
Do not use markdown.
Do not add explanations outside JSON.
 
Return exactly:
 
{
    "crop_health": 0,
    "irrigation": "Irrigation Recommended",
    "irrigation_reason": "Short explanation.",
    "risk_level": "Low",
    "confidence": 0,
    "alerts": [
        "Alert Title|Short detail"
    ],
    "recommendations": [
        "Short practical recommendation"
    ]
}
 
Rules:
 
- crop_health = integer from 0 to 100
- confidence = integer from 0 to 100
 
irrigation MUST be exactly:
 
"Irrigation Recommended"
 
OR
 
"No Irrigation Needed"
 
risk_level MUST be exactly:
 
"Low"
"Medium"
"High"
 
alerts must be a list.
 
Each alert must use:
 
"Title|short detail"
 
recommendations must contain maximum 4 items.
"""
    )
 
    # Call Groq
    try:
 
        raw = ask_ai(prompt)
 
        if not raw:
            raise ValueError("Groq returned an empty response.")
 
        raw = raw.strip()
 
        # Remove ```json
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
 
        # Remove closing ```
        raw = re.sub(r"\s*```$", "", raw)
 
        # Extract JSON
        match = re.search(r"\{[\s\S]*\}", raw)
 
        if not match:
            raise ValueError("Groq did not return valid JSON.")
 
        data = json.loads(match.group(0))
 
        # Validate crop health
        crop_health = int(data.get("crop_health", base["crop_health"]))
        crop_health = max(0, min(100, crop_health))
 
        # Validate confidence
        confidence = int(data.get("confidence", base["confidence"]))
        confidence = max(0, min(100, confidence))
 
        # Validate irrigation
        irrigation = data.get("irrigation", base["irrigation"])
        if irrigation not in ["Irrigation Recommended", "No Irrigation Needed"]:
            irrigation = base["irrigation"]
 
        # Validate risk
        risk_level = data.get("risk_level", base["risk_level"])
        if risk_level not in ["Low", "Medium", "High"]:
            risk_level = base["risk_level"]
 
        # Irrigation reason
        irrigation_reason = str(
            data.get("irrigation_reason", base["irrigation_reason"])
        ).strip()
 
        # Alerts
        alerts = data.get("alerts", base["alerts"])
        if not isinstance(alerts, list):
            alerts = base["alerts"]
        alerts = [str(x).strip() for x in alerts if str(x).strip()]
 
        # Recommendations
        recommendations = data.get("recommendations", base["recommendations"])
        if not isinstance(recommendations, list):
            recommendations = base["recommendations"]
        recommendations = [
            str(x).strip() for x in recommendations if str(x).strip()
        ][:4]
 
        # Final AI result
        return {
            **base,
            "crop_health": crop_health,
            "irrigation": irrigation,
            "irrigation_reason": irrigation_reason,
            "risk_level": risk_level,
            "confidence": confidence,
            "alerts": alerts,
            "recommendations": recommendations,
            "source": "Groq AI",
            "ai_error": "",
        }
 
    # Fallback
    except Exception as e:
 
        print("Groq error, fallback:", type(e).__name__, str(e))
 
        base["source"] = "Rule engine"
        base["ai_error"] = f"{type(e).__name__}: {e}"
 
        return base
 
 
# ==========================================================
# DEFAULT SESSION STATE
# ==========================================================
 
DEFAULTS = dict(
    sm=42,
    t=34,
    h=58,
    rain=20,
    ph=6.8,
 
    crop="Tomato",
    stage="Vegetative",
 
    # Irrigation controls
    zone="Zone 2",
    mins=15,
 
    # Farmer & location
    farmer_name=DEFAULT_FARMER_NAME,
    location_query=DEFAULT_LOCATION,
    location_name=DEFAULT_LOCATION,
    lat=DEFAULT_LAT,
    lon=DEFAULT_LON,
    location_error="",
 
    # Navigation
    goto=None,
 
    # Irrigation state
    irr=False,
    pump_log="",
 
    # Search
    ask=None,
    search="",
    search_ans="",
 
    # AI Assistant
    chat_in="",
    chat_out="",
 
    # Crop Intelligence
    q2="",
    a2="",
 
    # Reports
    rep_out="",
 
    # Data mode
    data_mode="🌐 Live Weather",
 
    # AI Command Center
    cmd_in="",
    cmd_out="",
 
    # Crop Intelligence inputs
    ci_fert="",
    ci_dis="",
 
    # Weather
    wx_out="",
 
    # Predictive Analytics
    pred_out="",
 
    # Plant Info
    pi_out="",
)
 
 
# ==========================================================
# HELPERS  (NOTE: these were missing in your pasted code,
# basic versions added so the app runs - replace with yours)
# ==========================================================
 
def init_state():
    for k, v in DEFAULTS.items():
        st.session_state.setdefault(k, v)
 
 
def farm():
    s = st.session_state
    return s.sm, s.t, s.h, s.rain, s.ph, s.crop, s.stage
 
 
@st.cache_data(ttl=600, show_spinner=False)
def _fetch_weather(lat, lon):
    params = urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m",
        "hourly": "precipitation_probability,soil_moisture_0_to_1cm",
        "forecast_days": 1,
        "timezone": "auto",
    })
    req = Request(
        f"https://api.open-meteo.com/v1/forecast?{params}",
        headers={"User-Agent": "AgriMindAI"},
    )
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())
 
 
def weather_summary():
    try:
        d = _fetch_weather(st.session_state.lat, st.session_state.lon)
        cur = d["current"]
        hourly = d.get("hourly", {})
 
        rain_vals = (hourly.get("precipitation_probability") or [0])[:12]
        soil_vals = hourly.get("soil_moisture_0_to_1cm") or []
 
        soil = None
        if soil_vals and soil_vals[0] is not None:
            # volumetric fraction (m3/m3) -> approx percent
            soil = soil_vals[0] * 100
 
        return {
            "temperature": cur["temperature_2m"],
            "humidity": cur["relative_humidity_2m"],
            "rain": max(v for v in rain_vals if v is not None),
            "soil_moisture": soil,
            "time": cur.get("time", datetime.now().isoformat()),
        }
    except Exception:
        return None
 
 
def satellite_url(lat, lon, date_str):
    d = 0.25
    params = urlencode({
        "REQUEST": "GetSnapshot",
        "LAYERS": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "CRS": "EPSG:4326",
        "TIME": str(date_str)[:10],
        "BBOX": f"{lat - d},{lon - d},{lat + d},{lon + d}",
        "FORMAT": "image/jpeg",
        "WIDTH": 800,
        "HEIGHT": 500,
    })
    return f"https://wvs.earthdata.nasa.gov/api/v1/snapshot?{params}"
 
 
# ==========================================================
# CALLBACKS
# ==========================================================
 
def refresh_analysis():
    """
    Clear cached farm analysis so the next run
    performs a fresh AI analysis.
    """
    analyze_farm.clear()
 
 
def ask_from(key, target):
    st.session_state.ask = (target, st.session_state[key])
 
 
def ask_chip(q):
    st.session_state.ask = ("chat_out", q)
 
 
def ask_report():
    st.session_state.ask = ("rep_out", "__report__")
 
 
# ==========================================================
# GET STATE
# ==========================================================
 
def get_state():
    init_state()
 
    # Get live weather
    weather = weather_summary()
 
    # Current data mode
    mode = st.session_state.get("data_mode", "🌐 Live Weather")
 
    # Update farm values from live weather
    if weather and mode != "✍️ Manual":
 
        st.session_state.t = round(weather["temperature"])
        st.session_state.h = round(weather["humidity"])
        st.session_state.rain = round(weather["rain"])
 
        # Use Open-Meteo soil moisture if available
        if (
            mode == "🌐 Live Weather"
            and weather.get("soil_moisture") is not None
        ):
            st.session_state.sm = round(weather["soil_moisture"])
 
    # Get current farm values
    sm, t, h, rain, ph, crop, stage = farm()
 
    # Run AI / Rule Engine Analysis
    res = analyze_farm(sm, t, h, rain, ph, crop, stage, client is not None)
 
    # Satellite date
    sat_date = (
        weather.get("time", datetime.now().isoformat())
        if weather
        else datetime.now().isoformat()
    )
 
    # Final state
    return {
        "weather": weather,
 
        "sm": sm,
        "t": t,
        "h": h,
        "rain": rain,
        "ph": ph,
 
        "crop": crop,
        "stage": stage,
 
        "res": res,
 
        "n_al": len(res["alerts"]),
 
        "sat_url": satellite_url(
            st.session_state.lat,
            st.session_state.lon,
            sat_date,
        ),
    }
 
