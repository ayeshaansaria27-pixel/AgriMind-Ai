"""Shared helpers for the new AgriMind pages (views/page7.py - views/page13.py).

Sirf common.py ke maujooda functions (get_state, ask_from) use hote hain,
baqi sab kuch yahin hai. Is file ko app.py ke saath (project root mein) rakhein.
"""
import base64
import json
import os
import time
import urllib.request

import numpy as np
import pandas as pd
import streamlit as st

from common import ask_from, client, get_state

GREEN, AMBER, RED = "#2ee27a", "#ffb020", "#ff5c5c"
DEFAULT_LOC = ("Karachi", 24.8607, 67.0011)
# Groq vision model (patte ki photo ke liye). Agar model ka naam badal jaye to yahan update karein.
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


# ----------------------------------------------------------------- basics
def num(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def readings():
    """(S, soil_moisture, temp, humidity, rain, ph) -- live values."""
    S = get_state()
    return S, num(S["sm"]), num(S["t"]), num(S["h"]), num(S["rain"]), num(S["ph"])


def thresholds():
    """(low, high) moisture rules. Settings page se 'thr_low' / 'thr_high' set kiye ja sakte hain."""
    return int(st.session_state.get("thr_low", 35)), int(st.session_state.get("thr_high", 60))


def card_html(title, body=""):
    return f'<div class="card"><h3>{title}</h3>{body}</div>'


def ask_with(prompt, out_key):
    """Ek tayyar sawal Groq assistant ko bhejta hai (common.ask_from ke zariye)."""
    k = f"_prompt_{out_key}"
    st.session_state[k] = prompt
    ask_from(k, out_key)


# ------------------------------------------------------- weather (Open-Meteo)
def _get_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "AgriMind/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def current_location():
    """(shehar ka naam, lat, lon) -- common.py ki session state se (Settings page)."""
    name = str(st.session_state.get("location_name") or DEFAULT_LOC[0]).split(",")[0].strip()
    return (name, float(st.session_state.get("lat", DEFAULT_LOC[1])),
            float(st.session_state.get("lon", DEFAULT_LOC[2])))


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_forecast(lat, lon):
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
           "precipitation_probability_max,wind_speed_10m_max"
           "&hourly=temperature_2m,relative_humidity_2m,precipitation"
           "&forecast_days=7&timezone=auto" % (lat, lon))
    d = _get_json(url)
    hourly = pd.DataFrame(d["hourly"])
    hourly["time"] = pd.to_datetime(hourly["time"])
    daily = pd.DataFrame(d["daily"])
    daily["time"] = pd.to_datetime(daily["time"])
    hum = hourly.groupby(hourly["time"].dt.normalize())["relative_humidity_2m"].mean().round(0)
    daily["humidity"] = daily["time"].map(hum)
    daily["precipitation_probability_max"] = daily["precipitation_probability_max"].fillna(0)
    return daily, hourly, int(d.get("utc_offset_seconds", 0))


def get_forecast():
    """(daily_df, hourly_df, utc_offset) ya None agar internet/API na chale."""
    try:
        _, lat, lon = current_location()
        return _fetch_forecast(lat, lon)
    except Exception:
        return None


def next_24h(fc):
    _, hourly, off = fc
    now = pd.Timestamp.now(tz="UTC").tz_localize(None) + pd.Timedelta(seconds=off)
    now = now.replace(minute=0, second=0, microsecond=0)
    return hourly[hourly["time"] >= now].head(24).reset_index(drop=True)


def wx_icon(code):
    try:
        c = int(code)
    except Exception:
        return "🌦️"
    if c == 0:
        return "☀️"
    if c in (1, 2):
        return "🌤️"
    if c == 3:
        return "☁️"
    if c in (45, 48):
        return "🌫️"
    if 51 <= c <= 67 or 80 <= c <= 82:
        return "🌧️"
    if 71 <= c <= 77 or c in (85, 86):
        return "❄️"
    if c >= 95:
        return "⛈️"
    return "🌦️"


# ------------------------------------------------------------------ history
def get_history(S=None):
    """Soil moisture / temperature / humidity ki rolling history (session mein)."""
    if S is None:
        S = get_state()
    sm, t, h = num(S["sm"]), num(S["t"]), num(S["h"])
    now = time.time()
    hist = st.session_state.get("_farm_hist")
    if hist is None:
        rng = np.random.default_rng(42)
        n = 48
        walk = lambda scale: rng.normal(0, scale, n).cumsum()
        wm, wt, wh = walk(0.6), walk(0.25), walk(0.8)
        hist = []
        for i in range(n):
            hist.append({
                "ts": now - (n - i) * 1800,
                "Soil Moisture (%)": float(np.clip(sm + wm[i] - wm[-1], 5, 95)),
                "Temperature (°C)": float(t + wt[i] - wt[-1]),
                "Humidity (%)": float(np.clip(h + wh[i] - wh[-1], 5, 100)),
            })
    if now - hist[-1]["ts"] > 20:
        hist.append({"ts": now, "Soil Moisture (%)": sm, "Temperature (°C)": t, "Humidity (%)": h})
    hist = hist[-300:]
    st.session_state["_farm_hist"] = hist
    df = pd.DataFrame(hist)
    df.index = pd.to_datetime(df.pop("ts"), unit="s")
    return df


# ------------------------------------------------------------------ devices
SENSOR_DEFS = [
    ("SM-01", "Soil Moisture", "Zone 1"), ("SM-02", "Soil Moisture", "Zone 2"), ("SM-03", "Soil Moisture", "Zone 3"),
    ("TP-01", "Temperature", "Zone 1"), ("TP-02", "Temperature", "Zone 3"),
    ("HM-01", "Humidity", "Zone 1"), ("HM-02", "Humidity", "Zone 2"),
    ("PH-01", "Soil pH", "Zone 2"), ("RN-01", "Rain Gauge", "Zone 1"), ("FL-01", "Flow Meter", "Zone 2"),
    ("LS-01", "Leaf Wetness", "Zone 3"), ("WS-01", "Wind Speed", "Zone 1"),
]
EXTRA_DEFS = [("PM-01", "Pump Controller", "Zone 2"), ("GW-01", "Gateway", "Farm")]
DEVICE_TYPES = ["Soil Moisture", "Temperature", "Humidity", "Soil pH", "Rain Gauge", "Flow Meter",
                "Leaf Wetness", "Wind Speed", "Pump Controller", "Gateway"]


def get_devices():
    if "_devices" not in st.session_state:
        rng = np.random.default_rng(7)
        devs = []
        for did, typ, zone in SENSOR_DEFS + EXTRA_DEFS:
            devs.append({"id": did, "type": typ, "zone": zone, "status": "Online",
                         "battery": int(rng.integers(45, 100)), "signal": int(rng.integers(-88, -48)),
                         "calibrated": "Factory", "offset": int(rng.integers(1, 40))})
        for d in devs:
            if d["id"] == "LS-01":
                d["status"], d["battery"] = "Offline", 8
            if d["id"] == "WS-01":
                d["battery"] = 18
            if d["type"] in ("Pump Controller", "Gateway"):
                d["battery"] = 100
        st.session_state["_devices"] = devs
    return st.session_state["_devices"]


def _reading(d, sm, t, h, ph, rain):
    if d["status"] != "Online":
        return "—"
    try:
        z = int(d["zone"].split()[-1]) - 2
    except Exception:
        z = 0
    typ, irr = d["type"], bool(st.session_state.get("irr", False))
    if typ == "Soil Moisture":
        return f"{min(100, max(0, sm + z * 2.0)):.0f} %"
    if typ == "Temperature":
        return f"{t + z * 0.6:.1f} °C"
    if typ == "Humidity":
        return f"{min(100, max(0, h + z * 1.5)):.0f} %"
    if typ == "Soil pH":
        return f"{ph:.1f}"
    if typ == "Rain Gauge":
        return f"{rain:.0f}% prob"
    if typ == "Flow Meter":
        return "12.4 L/min" if irr else "0 L/min"
    if typ == "Pump Controller":
        return "ON" if irr else "OFF"
    return "—"


def devices_df(only_sensors=False):
    _, sm, t, h, rain, ph = readings()
    bucket = int(time.time() // 5)
    rows = []
    for d in get_devices():
        if only_sensors and d["type"] in ("Pump Controller", "Gateway"):
            continue
        online = d["status"] == "Online"
        sig = d["signal"]
        quality = "Strong" if sig >= -60 else ("Fair" if sig >= -75 else "Weak")
        rows.append({
            "ID": d["id"], "Device": d["type"], "Zone": d["zone"],
            "Status": "🟢 Online" if online else "🔴 Offline",
            "Reading": _reading(d, sm, t, h, ph, rain),
            "Battery (%)": d["battery"], "Signal": f"{sig} dBm ({quality})",
            "Last Seen": f"{(bucket + d['offset']) % 45 + 1}s ago" if online else "3 h ago",
            "Calibrated": d["calibrated"],
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------- Groq AI
def ai_vision(img_bytes, prompt, mime="image/jpeg"):
    """Patte ki photo + prompt Groq vision model ko bhejta hai, jawab text mein."""
    if client is None:
        return "⚠️ GROQ_API_KEY set nahi hai, isliye AI photo detect nahi kar sakta."
    b64 = base64.b64encode(img_bytes).decode()
    try:
        r = client.chat.completions.create(
            model=VISION_MODEL, temperature=0.2, max_tokens=700,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]}])
        return r.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI error: {e}"
