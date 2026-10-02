# ==========================================================
# COMMON - shared constants, backend (weather / Groq AI), HTML builders,
# page registry (PAGES) and helpers used by app.py, sidebar.py and views/*.py
# NOTE: this module is imported once per server process, so it only DEFINES
# things. Per-session state is created in init_state() / get_state().
# It must never import app.py, sidebar.py or anything from views/.
# ==========================================================

import os, re, json, base64, random
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


# API key: Streamlit secrets -> environment variable
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ==========================================================
# LIVE LOCATION + WEATHER
# ==========================================================

WEATHER_CODES = {
    0: ("Clear", "☀️"),
    1: ("Mainly Clear", "🌤️"),
    2: ("Partly Cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Rime Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy Drizzle", "🌧️"),
    56: ("Freezing Drizzle", "🌧️"),
    57: ("Freezing Drizzle", "🌧️"),
    61: ("Light Rain", "🌦️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy Rain", "🌧️"),
    66: ("Freezing Rain", "🌧️"),
    67: ("Freezing Rain", "🌧️"),
    71: ("Light Snow", "🌨️"),
    73: ("Snow", "❄️"),
    75: ("Heavy Snow", "❄️"),
    77: ("Snow Grains", "❄️"),
    80: ("Rain Showers", "🌦️"),
    81: ("Rain Showers", "🌧️"),
    82: ("Heavy Showers", "⛈️"),
    85: ("Snow Showers", "🌨️"),
    86: ("Heavy Snow Showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm + Hail", "⛈️"),
    99: ("Thunderstorm + Hail", "⛈️")
}


def _get_json(url):
    req = Request(
        url,
        headers={"User-Agent": "AgriMind-AI/1.0"}
    )

    with urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))


@st.cache_data(ttl=3600, show_spinner=False)
def geocode_location(query):
    if not query.strip():
        return []

    params = urlencode({
        "name": query.strip(),
        "count": 5,
        "language": "en",
        "format": "json"
    })

    try:
        data = _get_json(
            "https://geocoding-api.open-meteo.com/v1/search?" + params
        )
        return data.get("results", [])

    except Exception as e:
        print("Geocoding error:", e)
        return []


@st.cache_data(ttl=600, show_spinner=False)
def get_live_weather(lat, lon):

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,precipitation,"
            "weather_code,wind_speed_10m,soil_moisture_0_to_7cm"
        ),
        "hourly": (
            "precipitation_probability,temperature_2m,"
            "relative_humidity_2m,weather_code"
        ),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "forecast_days": 4,
        "timezone": "auto"
    }

    try:
        data = _get_json(
            "https://api.open-meteo.com/v1/forecast?"
            + urlencode(params)
        )

        cur = data["current"]
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})

        h_times = hourly.get("time", [])
        probs = hourly.get("precipitation_probability", [])

        try:
            start_idx = h_times.index(cur.get("time"))
        except ValueError:
            start_idx = 0

        rain_probs = [
            x
            for x in probs[start_idx:start_idx + 24]
            if x is not None
        ]

        soil_raw = cur.get("soil_moisture_0_to_7cm")

        soil_pct = (
            max(0, min(100, float(soil_raw) * 100))
            if soil_raw is not None
            else None
        )

        code = int(cur.get("weather_code", 0))

        condition, icon = WEATHER_CODES.get(
            code,
            ("Current Conditions", "🌤️")
        )

        forecasts = []

        for i in range(min(4, len(daily.get("time", [])))):

            dcode = int(daily["weather_code"][i])

            dname, dicon = WEATHER_CODES.get(
                dcode,
                ("Weather", "🌤️")
            )

            forecasts.append({
                "date": daily["time"][i],
                "max": daily["temperature_2m_max"][i],
                "min": daily["temperature_2m_min"][i],
                "rain": daily["precipitation_probability_max"][i],
                "icon": dicon,
                "condition": dname
            })

        return {
            "temperature": float(cur["temperature_2m"]),
            "humidity": float(cur["relative_humidity_2m"]),
            "rain": float(max(rain_probs) if rain_probs else 0),
            "weather_code": code,
            "condition": condition,
            "icon": icon,
            "wind": float(cur.get("wind_speed_10m") or 0),
            "soil_moisture": soil_pct,
            "time": cur.get("time", ""),
            "timezone": data.get("timezone", "auto"),
            "forecasts": forecasts,
            "source": "Open-Meteo"
        }

    except Exception as e:
        print("Weather API error:", e)
        return None


# ==========================================================
# SATELLITE VIEW
# ==========================================================

# Esri World Imagery - recommended satellite source
ESRI_SATELLITE_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/export?"
    "bbox=66.9757,24.8487,67.0265,24.8727&"
    "bboxSR=4326&"
    "imageSR=4326&"
    "size=1000,520&"
    "format=jpg&"
    "f=image"
)


# NASA GIBS - October 1, 2026 imagery for Karachi
NASA_SATELLITE_URL = (
    "https://wvs.earthdata.nasa.gov/api/v1/snapshot?"
    "REQUEST=GetSnapshot&"
    "TIME=2026-10-01T00:00:00Z&"
    "BBOX=66.9,24.76,67.1,24.96&"
    "CRS=EPSG:4326&"
    "LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor&"
    "WRAP=day&"
    "FORMAT=image/jpeg&"
    "WIDTH=1000&"
    "HEIGHT=520"
)


def satellite_url(lat, lon, date_str):

    try:
        # Use the provided Esri satellite image for the default Karachi location.
        if (
            abs(float(lat) - DEFAULT_LAT) < 0.01
            and abs(float(lon) - DEFAULT_LON) < 0.01
        ):
            return ESRI_SATELLITE_URL

        # For other locations, use the dynamic NASA satellite image.
        d = date_str[:10]

        pad = 0.10

        bbox = (
            f"{float(lon) - pad},"
            f"{float(lat) - pad},"
            f"{float(lon) + pad},"
            f"{float(lat) + pad}"
        )

        params = {
            "REQUEST": "GetSnapshot",
            "TIME": f"{d}T00:00:00Z",
            "BBOX": bbox,
            "CRS": "EPSG:4326",
            "LAYERS": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "WRAP": "day",
            "FORMAT": "image/jpeg",
            "WIDTH": 1000,
            "HEIGHT": 520
        }

        return (
            "https://wvs.earthdata.nasa.gov/api/v1/snapshot?"
            + urlencode(params)
        )

    except Exception:
        return ""


def apply_location():

    q = st.session_state.location_query.strip()

    results = geocode_location(q)

    if not results:
        st.session_state.location_error = (
            "Location not found. Please try the city/country again."
        )
        return

    r = results[0]

    country = r.get("country", "")
    admin = r.get("admin1", "")
    label = r.get("name", q)

    parts = [label]

    if admin and admin != label:
        parts.append(admin)

    if country:
        parts.append(country)

    st.session_state.location_name = ", ".join(parts)

    st.session_state.lat = float(r["latitude"])
    st.session_state.lon = float(r["longitude"])

    st.session_state.location_error = ""


def reset_location():

    st.session_state.location_query = DEFAULT_LOCATION
    st.session_state.location_name = DEFAULT_LOCATION
    st.session_state.lat = DEFAULT_LAT
    st.session_state.lon = DEFAULT_LON
    st.session_state.location_error = ""


def weather_summary():
    return get_live_weather(
        st.session_state.lat,
        st.session_state.lon
    )


# ==========================================================
# GROQ AI
# ==========================================================

def ask_ai(prompt):

    r = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AgriMind AI, an intelligent agriculture "
                    "assistant."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return r.choices[0].message.content


def ctx(sm, t, h, rain, ph, crop, stage):

    loc = st.session_state.get(
        "location_name",
        DEFAULT_LOCATION
    )

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
# ANALYSIS (Groq + fallback)
# ==========================================================

def rule_based(sm, t, h, rain, ph):

    score, al = 100, []

    if sm < 35:
        score -= 20
        al.append(
            f"Low Soil Moisture|{sm:.0f}% detected (Critical)"
        )

    elif sm > 60:
        score -= 10
        al.append(
            f"Soil Too Wet|{sm:.0f}% detected"
        )

    if t > 30:
        score -= 12
        al.append(
            f"High Temperature|{t:.0f}°C detected "
            f"(above optimal range)"
        )

    elif t < 20:
        score -= 8
        al.append(
            f"Low Temperature|{t:.0f}°C detected"
        )

    if h < 40 or h > 70:
        score -= 6
        al.append(
            f"Humidity Alert|{h:.0f}% out of range"
        )

    if ph < 6.0 or ph > 7.5:
        score -= 8
        al.append(
            f"pH Alert|pH {ph} out of range"
        )

    if rain > 60:
        al.append(
            f"Rain Expected|{rain:.0f}% probability "
            f"in next 12 hours"
        )

    need = sm < 45 and rain < 50

    return {
        "crop_health": max(score, 0),

        "irrigation": (
            "Irrigation Recommended"
            if need
            else "No Irrigation Needed"
        ),

        "irrigation_reason": (
            "Soil moisture is slightly low and temperature is high. "
            "No significant rainfall is expected in the next 24 hours."
            if need
            else
            "Soil moisture is acceptable or rain is likely soon."
        ),

        "risk_level": (
            "Low"
            if score >= 80
            else "Medium"
            if score >= 60
            else "High"
        ),

        "alerts": al,

        "confidence": 92 if need else 88,

        "source": "Rule engine",

        "recommendations": [
            "Maintain soil moisture between 35% - 60%.",
            "Avoid excessive irrigation due to high temperature.",
            "Consider adding organic fertilizer in 5-7 days."
        ]
    }


@st.cache_data(
    show_spinner="🤖 AI is analyzing the farm...",
    ttl=900
)
def analyze_farm(
    sm,
    t,
    h,
    rain,
    ph,
    crop,
    stage,
    ai_on=True
):

    base = rule_based(
        sm,
        t,
        h,
        rain,
        ph
    )

    if client is None:
        return base

    prompt = ctx(
        sm,
        t,
        h,
        rain,
        ph,
        crop,
        stage
    ) + """
Return ONLY valid JSON (no markdown) with exactly these keys:
{"crop_health": <int 0-100>,
"irrigation": "Irrigation Recommended" or "No Irrigation Needed",
"irrigation_reason": "<1-2 sentences>",
"risk_level": "Low" or "Medium" or "High",
"confidence": <int 0-100>,
"alerts": ["<Title>|<short detail>", ...],
"recommendations": ["<short advice>", ... max 4]}
"""

    try:

        data = json.loads(
            re.search(
                r"\{.*\}",
                ask_ai(prompt),
                re.S
            ).group(0)
        )

        out = {
            **base,
            **{
                k: v
                for k, v in data.items()
                if k in base
            }
        }

        out["crop_health"] = int(
            out["crop_health"]
        )

        out["confidence"] = int(
            out["confidence"]
        )

        out["source"] = "Groq AI"

        return out

    except Exception as e:

        print(
            "Groq error, fallback:",
            e
        )

        return base


# ==========================================================
# HTML BUILDERS
# ==========================================================

def b64(p):

    try:

        with open(p, "rb") as f:

            return (
                "data:image/jpeg;base64,"
                + base64.b64encode(f.read()).decode()
            )

    except Exception:

        return None


def spark(seed, color):

    r = random.Random(seed)

    pts = " ".join(
        f"{i * 10},{30 - r.randint(3, 26)}"
        for i in range(11)
    )

    return (
        f'<svg viewBox="0 0 100 32" '
        f'preserveAspectRatio="none">'
        f'<polyline points="{pts}" fill="none" '
        f'stroke="{color}" stroke-width="1.6"/>'
        f'</svg>'
    )


def badge(v, lo, hi):

    return (
        ("low", "Low")
        if v < lo
        else ("high", "High")
        if v > hi
        else ("good", "Good")
    )


def header_html():

    farmer_name = st.session_state.get(
        "farmer_name",
        DEFAULT_FARMER_NAME
    )

    first_name = (
        farmer_name.split()[0]
        if farmer_name.strip()
        else "Farmer"
    )

    av = b64(AVATAR_IMG)

    a = (
        f'<div class="av" '
        f'style="background-image:url({av})"></div>'
        if av
        else
        f'<div class="av">{first_name[0].upper()}</div>'
    )

    return (
        f"""
        <div class="top">
            <div style="font-size:34px">🌿</div>
            <div class="brand">
                <b>AgriMind AI</b>
                <small>From Farm Data to Intelligent Action</small>
            </div>
        </div>
        """,

        f"""
        <div class="top" style="justify-content:flex-end">
            <div>🔔</div>

            <div style="color:var(--mut)">
                <span class="up">●</span> System Online<br>
                <small>Live weather connected</small>
            </div>

            <div class="user">
                {a}

                <div>
                    <b>{farmer_name}</b><br>
                    <small style="color:var(--mut)">Farmer</small>
                </div>
            </div>
        </div>
        """
    )


def overview_html(n_al):

    return f"""
    <div class="card">
        <h3>🌿 System Overview</h3>

        <div class="hl">
            <div class="ring" style="--p:98">
                <div>98%</div>
            </div>

            <div>
                <small style="color:var(--mut)">
                    Overall Health
                </small>
                <br>
                <b class="up" style="font-size:17px">
                    Excellent
                </b>
            </div>
        </div>

        <div class="row">
            <span>IoT Devices</span>
            <span class="up">12/12 Online</span>
        </div>

        <div class="row">
            <span>Automations</span>
            <span class="up">3 Active</span>
        </div>

        <div class="row">
            <span>Critical Alerts</span>
            <span class="dn">{n_al}</span>
        </div>

        <div class="row">
            <span>Data Freshness</span>
            <span>2 min ago</span>
        </div>
    </div>

    <div class="card">
        <h3>🌄 Smarter Farms<br>Greener Tomorrow</h3>
    </div>

    <small style="color:var(--mut)">
        AgriMind AI v1.0.0<br>
        Hackathon Edition · {datetime.now():%b %Y}
    </small>
    """


def hero_html(n_al, weather):

    bg = b64(HERO_IMG)

    bg_style = (
        f"background-image:"
        f"linear-gradient("
        f"100deg,"
        f"rgba(4,30,18,.92) 28%,"
        f"rgba(4,30,18,.05)"
        f"),url({bg})"
        if bg
        else
        "background:linear-gradient("
        "100deg,"
        "rgba(4,30,18,.95) 30%,"
        "rgba(40,120,50,.6)"
        "),repeating-linear-gradient("
        "115deg,"
        "#2d6a2f 0 14px,"
        "#3c8a3a 14px 28px)"
    )

    farmer_name = st.session_state.get(
        "farmer_name",
        DEFAULT_FARMER_NAME
    )

    first_name = (
        farmer_name.split()[0]
        if farmer_name.strip()
        else "Farmer"
    )

    if weather:

        fc = weather.get("forecasts", [])

        forecast_text = " · ".join(
            f"{x['date'][5:]} "
            f"{x['max']:.0f}°/"
            f"{x['min']:.0f}°"
            for x in fc[:3]
        )

        wx = f"""
        <b>
            {weather['icon']}
            {weather['temperature']:.0f}°C
        </b>
        <br>
        {weather['condition']}
        <br>

        <small>
            📍 {st.session_state.get(
                'location_name',
                DEFAULT_LOCATION
            )}
        </small>

        <br>

        <small>{forecast_text}</small>
        """

    else:

        wx = f"""
        <b>🌤️ Weather unavailable</b>
        <br>

        <small>
            📍 {st.session_state.get(
                'location_name',
                DEFAULT_LOCATION
            )}
        </small>

        <br>

        <small>
            Check your internet connection.
        </small>
        """

    return f"""
    <div class="hero" style="{bg_style}">

        <div>
            <small style="color:var(--mut)">
                🌾 AI + Live Weather + Farm Intelligence
            </small>

            <h1>Hello {first_name}! 👋</h1>

            <div style="max-width:420px">
                Your farm is being monitored with live weather
                data and AI-powered agricultural insights.
            </div>

            <div>
                <span class="pill">
                    🌐 Live Weather
                </span>

                <span class="pill">
                    🛰️ Satellite Ready
                </span>

                <span class="pill r">
                    🔺 {n_al} Alerts
                </span>
            </div>
        </div>

        <div class="wx">
            {wx}
        </div>

    </div>
    """


def metrics_html(sm, t, h, rain, ph):

    c = []

    x, l = badge(sm, 35, 60)

    c.append((
        "💧",
        "Soil Moisture",
        f"{sm:.0f}%",
        x,
        l,
        "Optimal: 35% - 60%",
        "#2ee27a"
    ))

    x, l = badge(t, 20, 30)

    c.append((
        "🌡️",
        "Temperature",
        f"{t:.0f}°C",
        x,
        l,
        "Optimal: 20°C - 30°C",
        "#f5a524"
    ))

    x, l = badge(h, 40, 70)

    c.append((
        "💦",
        "Humidity",
        f"{h:.0f}%",
        x,
        l,
        "Optimal: 40% - 70%",
        "#34b7ff"
    ))

    x, l = (
        ("low", "Low")
        if rain < 40
        else
        ("high", "High")
    )

    c.append((
        "🌧️",
        "Rain Probability",
        f"{rain:.0f}%",
        x,
        l,
        "Next 24h",
        "#9b7bff"
    ))

    x, l = badge(ph, 6.0, 7.5)

    c.append((
        "🧪",
        "pH Level",
        f"{ph}",
        x,
        l,
        "Optimal: 6.0 - 7.5",
        "#2ee27a"
    ))

    return (
        '<div class="mets">'
        +
        "".join(
            f'''
            <div class="m">
                <small>{i} {n}</small>
                <div class="v">{v}</div>
                <span class="bd {x}">{l}</span>
                <br>
                <small>{o}</small>
                {spark(k * 11 + int(sm), col)}
            </div>
            '''
            for k, (i, n, v, x, l, o, col)
            in enumerate(c)
        )
        +
        "</div>"
    )


def sensors_html(sm, t, h, ph, weather=None):

    rain_label = (
        f"{weather['rain']:.0f}%"
        if weather
        else "—"
    )

    soil_label = (
        f"{sm:.0f}%"
        if sm is not None
        else "—"
    )

    rows = [
        (
            "💧",
            "Soil Moisture",
            soil_label,
            (
                "Live model"
                if weather
                and weather.get("soil_moisture") is not None
                else
                "Estimated"
            ),
            "up"
        ),

        (
            "🌡️",
            "Temperature",
            f"{t:.0f}°C",
            "Live weather",
            "up"
        ),

        (
            "💦",
            "Humidity",
            f"{h:.0f}%",
            "Live weather",
            "up"
        ),

        (
            "🌧️",
            "Rain Probability",
            rain_label,
            "Next 24h",
            "up"
        ),

        (
            "🧪",
            "Soil pH",
            f"{ph:.1f}",
            "Needs soil sensor",
            "low"
        )
    ]

    return (
        f'''
        <div class="card">
            <h3>
                📊 Farm Intelligence Data
                <span class="tag">
                    ● Live {datetime.now():%H:%M}
                </span>
            </h3>
        '''
        +
        "".join(
            f'''
            <div class="row">
                <span>{i} {n}</span>
                <b>{v}</b>
                <span class="{c}"
                      style="font-size:11px">
                    {d}
                </span>
            </div>
            '''
            for i, n, v, d, c in rows
        )
        +
        "</div>"
    )


def health_html(r, crop, stage):

    hp = r["crop_health"]

    c, t = (
        ("good", "Good")
        if hp >= 80
        else
        ("high", "Fair")
        if hp >= 60
        else
        ("crit", "Poor")
    )

    recs = "".join(
        f'<div style="margin:5px 0">✅ {x}</div>'
        for x in r["recommendations"]
    )

    return f"""
    <div class="card">

        <h3>
            🌿 Crop Health Analysis
            <span class="tag">AI Decision</span>
        </h3>

        <div class="hl">

            <div style="text-align:center">

                <div class="ring"
                     style="--p:{hp};--s:118px">

                    <div>{hp}%</div>

                </div>

                <small>Overall Health</small>
                <br>

                <span class="bd {c}">
                    {t}
                </span>

            </div>

            <div style="flex:1">

                <div class="row">
                    <span>🍅 Crop Type</span>
                    <b>{crop}</b>
                </div>

                <div class="row">
                    <span>🌱 Growth Stage</span>
                    <b>{stage}</b>
                </div>

                <div class="row">
                    <span>🔍 Last Analysis</span>
                    <b>Just now</b>
                </div>

            </div>

        </div>

        <h3 style="margin-top:12px">
            📍 Recommendations
        </h3>

        {recs}

    </div>
    """


def field_html(
    sm,
    crop,
    mode="Live View",
    irrigating=False,
    sat_url="",
    location=""
):

    bg = b64(FIELD_IMG)

    if mode == "Satellite View" and sat_url:

        bg_style = (
            f"background-image:"
            f"linear-gradient("
            f"rgba(0,0,0,.18),"
            f"rgba(0,0,0,.18)"
            f"),url('{sat_url}')"
        )

        if sat_url == ESRI_SATELLITE_URL:
            source = "Esri World Imagery"

        else:
            source = "NASA GIBS Satellite Observation"

    else:

        bg_style = (
            f"background-image:url({bg})"
            if bg
            else
            "background:#0a2a1a"
        )

        source = "Farm Field View"

    irr = (
        '<div class="irr">'
        '💧 Irrigation ON<br>'
        '<small>Zone 2 - 15 min</small>'
        '</div>'
        if irrigating
        else ""
    )

    if mode == "Satellite View":

        z1 = (
            '<span>🛰️ Farm Area<br>'
            'Satellite Observation</span>'
        )

        z2 = (
            '<span>📍 Selected Location<br>'
            'Not live video</span>'
        )

        z3 = (
            '<span>☁️ Land / Cloud View<br>'
            'Latest available image</span>'
        )

    else:

        z1 = (
            f'<span>Zone 1<br>'
            f'({crop})<br>'
            f'{sm:.0f}%</span>'
        )

        z2 = (
            f'<span>Zone 2<br>'
            f'({crop})<br>'
            f'{max(sm - 4, 0):.0f}%</span>'
        )

        z3 = (
            '<span>Zone 3<br>'
            '(Lettuce)<br>'
            '65%</span>'
        )

    return f"""
    <div class="card">

        <h3>
            📍 Field View
            <span class="tag">{mode}</span>
        </h3>

        <div class="field"
             style="{bg_style}">

            <div class="z z1">
                {z1}
            </div>

            <div class="z z2">
                {z2}
            </div>

            <div class="z z3">
                {z3}
            </div>

            {irr}

        </div>

        <div style="
            display:flex;
            gap:18px;
            margin-top:8px;
            flex-wrap:wrap
        ">

            <span>🟢 Healthy</span>
            <span>🟠 Needs Attention</span>
            <span>🔴 Critical</span>

            <span style="
                margin-left:auto;
                color:var(--mut)
            ">
                Source: {source} · {location}
            </span>

        </div>

    </div>
    """


# ==========================================================
# AI AGENT WORKFLOW
# ==========================================================

WORKFLOW = """
<div class="card">

    <h3>🤖 AI Agent Workflow</h3>

    <div class="flow">

        <div>
            <b>📡</b>
            1. Data Collection
            <br>
            <small>IoT Sensors + Weather</small>
        </div>

        <div>
            <b>🧠</b>
            2. Multi-Agent Analysis
            <br>
            <small>Crop + Weather + Risk</small>
        </div>

        <div>
            <b>⚙️</b>
            3. Decision Making
            <br>
            <small>Irrigation / Alerts</small>
        </div>

        <div>
            <b>💧</b>
            4. Automation
            <br>
            <small>Pump / Sprinkler</small>
        </div>

        <div>
            <b>📱</b>
            5. Farmer Notification
            <br>
            <small>Dashboard + Alerts</small>
        </div>

    </div>

</div>
"""


def decision_html(r, rain):

    hp = r["crop_health"]
    conf = r["confidence"]

    hs = (
        "Healthy"
        if hp >= 80
        else "Fair"
        if hp >= 60
        else "Poor"
    )

    rc = {
        "Low": "good",
        "Medium": "high",
        "High": "crit"
    }.get(
        r["risk_level"],
        "good"
    )

    go = (
        "Recommend"
        if "Recommended" in r["irrigation"]
        else "Hold"
    )

    ag = [
        (
            "🌿 Crop Health Agent",
            f"{hs} ({hp}%)"
        ),

        (
            "⛅ Weather Agent",
            (
                "No rain expected (78%)"
                if rain < 40
                else
                f"Rain likely ({rain:.0f}%)"
            )
        ),

        (
            "💧 Irrigation Agent",
            f"{go} ({conf}%)"
        ),

        (
            "🎯 Risk Agent",
            f'{r["risk_level"]} Risk (88%)'
        ),

        (
            "🤖 Farm Assistant",
            "Ready to guide (95%)"
        )
    ]

    return (
        f"""
        <div class="card">

            <h3>
                🧠 AI Decision Center
                <span class="tag">
                    Powered by {r["source"]}
                </span>
            </h3>

            <small style="color:var(--mut)">
                AI Decision
            </small>

            <br>

            <div class="dec">
                ✔ {r["irrigation"]}
            </div>

            <div style="margin-bottom:10px">
                {r["irrigation_reason"]}
            </div>

            <span class="bd good">
                ● {conf}% Confidence
            </span>

            <small>Risk:</small>

            <span class="bd {rc}">
                {r["risk_level"]}
            </span>

            <h3 style="margin-top:14px">
                🤖 AI Agent Analysis
            </h3>
        """
        +
        "".join(
            f'''
            <div class="ag">
                <span>{a}</span>
                <span>{b}</span>
            </div>
            '''
            for a, b in ag
        )
        +
        "</div>"
    )


def alerts_html(r, full=False):

    icons = [
        "🌡️",
        "💧",
        "📍",
        "🌧️"
    ]

    times = [
        "2 hours ago",
        "4 hours ago",
        "6 hours ago",
        "12 hours ago"
    ]

    items = (
        r["alerts"]
        if full
        else
        r["alerts"][:4]
    )

    body = ""

    for i, a in enumerate(items):

        t, _, d = a.partition("|")

        body += f"""
        <div class="al">

            <i>
                {icons[i % 4]}
            </i>

            <div>
                <b>{t}</b>
                <small>{d}</small>
            </div>

            <em>
                {times[i % 4]}
            </em>

        </div>
        """

    body = (
        body
        or
        """
        <div class="al">
            <div>
                <b>No active alerts</b>
                <small>All sensors normal</small>
            </div>
        </div>
        """
    )

    return f"""
    <div class="card">

        <h3>
            🔔
            {
                "All Alerts & Incidents"
                if full
                else
                "Recent Alerts"
            }

            <span class="tag">
                {len(r["alerts"])} total
            </span>

        </h3>

        {body}

    </div>
    """


STATUSBAR = lambda n: (
    f'<div class="status">'
    f'<span>📟 Connected Devices '
    f'<b class="up">12/12</b></span>'

    f'<span>⚙️ Active Automations '
    f'<b>3</b></span>'

    f'<span>🚨 Critical Alerts '
    f'<b>{n}</b></span>'

    f'<span style="margin-left:auto">'
    f'Last Updated: '
    f'{datetime.now():%b %d, %Y, %H:%M}'
    f'</span>'

    f'</div>'
)


# ==========================================================
# CSS
# ==========================================================

CSS = """<style>

.stApp{
    background:radial-gradient(
        circle at 15% 0,
        #0b3a24,
        #04140d 55%
    )
}

header[data-testid="stHeader"]{
    background:transparent
}

footer,#MainMenu{
    visibility:hidden
}

.block-container{
    max-width:1500px;
    padding-top:2.2rem
}

section[data-testid="stSidebar"]{
    background:#061d12;
    border-right:1px solid rgba(60,200,120,.2)
}

.stButton>button{
    width:100%;
    border-radius:12px;
    border:1px solid rgba(60,200,120,.25);
    background:rgba(9,40,26,.6);
    color:#e9fff2
}

.stButton>button:hover{
    border-color:#2ee27a;
    color:#fff
}

.stButton>button[kind="primary"]{
    background:linear-gradient(
        90deg,
        rgba(46,226,122,.35),
        rgba(46,226,122,.08)
    );
    border:1px solid #2ee27a;
    color:#fff
}

section[data-testid="stSidebar"] .stButton>button{
    justify-content:flex-start;
    text-align:left;
    font-size:13.5px
}

.am{
    --mut:#8fbfa3;
    --amb:#f5a524;
    --red:#ff4d4d;
    --blu:#34b7ff;
    --g:#2ee27a;
    font-size:13px;
    color:#e9fff2;
    font-family:'Segoe UI',system-ui,sans-serif
}

.am .card{
    background:rgba(9,40,26,.78);
    border:1px solid rgba(60,200,120,.28);
    border-radius:14px;
    padding:12px;
    margin-bottom:10px
}

.am h3{
    margin:0 0 8px;
    font-size:15px;
    display:flex;
    align-items:center;
    gap:8px;
    color:#e9fff2
}

.am .top{
    display:flex;
    align-items:center;
    gap:14px;
    padding:4px 6px
}

.am .brand b{
    font-size:26px;
    display:block;
    line-height:1;
    color:#fff
}

.am .brand small{
    color:var(--mut)
}

.am .user{
    display:flex;
    gap:10px;
    align-items:center
}

.am .av{
    width:40px;
    height:40px;
    border-radius:50%;
    background:#1a7a45 center/cover;
    display:grid;
    place-items:center;
    font-weight:700
}

.am .ring{
    width:var(--s,80px);
    height:var(--s,80px);
    border-radius:50%;
    background:conic-gradient(
        #2ee27a calc(var(--p)*1%),
        rgba(255,255,255,.1) 0
    );
    display:grid;
    place-items:center;
    flex:none
}

.am .ring div{
    width:calc(var(--s,80px) - 16px);
    height:calc(var(--s,80px) - 16px);
    border-radius:50%;
    background:#072516;
    display:grid;
    place-items:center;
    font-size:calc(var(--s,80px)/3.6);
    font-weight:700
}

.am .hero{
    border-radius:14px;
    border:1px solid rgba(60,200,120,.28);
    padding:18px;
    display:flex;
    justify-content:space-between;
    min-height:175px;
    margin-bottom:12px;
    background-size:cover;
    background-position:center
}

.am .hero h1{
    margin:6px 0;
    font-size:32px;
    color:#fff;
    padding:0
}

.am .pill{
    display:inline-block;
    padding:6px 11px;
    border-radius:10px;
    background:rgba(0,0,0,.45);
    border:1px solid rgba(60,200,120,.28);
    margin:8px 6px 0 0
}

.am .pill.r{
    border-color:var(--amb);
    color:#ffd08a
}

.am .wx{
    background:rgba(0,0,0,.5);
    border:1px solid rgba(60,200,120,.28);
    border-radius:14px;
    padding:12px 14px;
    height:fit-content;
    min-width:185px
}

.am .wx b{
    font-size:26px
}

.am .mets{
    display:grid;
    grid-template-columns:repeat(5,1fr);
    gap:10px;
    margin-bottom:12px
}

.am .m{
    background:rgba(9,40,26,.78);
    border:1px solid rgba(60,200,120,.28);
    border-radius:14px;
    padding:11px
}

.am .m small{
    color:var(--mut)
}

.am .m .v{
    font-size:28px;
    font-weight:700;
    margin:4px 0
}

.am .bd{
    display:inline-block;
    padding:2px 14px;
    border-radius:8px;
    font-size:12px;
    font-weight:600
}

.am .good{
    background:rgba(46,226,122,.25);
    color:#2ee27a
}

.am .high{
    background:rgba(245,165,36,.25);
    color:#f5a524
}

.am .low{
    background:rgba(52,183,255,.25);
    color:#34b7ff
}

.am .crit{
    background:rgba(255,77,77,.25);
    color:#ff4d4d
}

.am .m svg{
    width:100%;
    height:32px;
    margin-top:6px
}

.am .card .row{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:9px 4px;
    border-bottom:1px solid rgba(255,255,255,.06)
}

.am .up{
    color:#2ee27a
}

.am .dn{
    color:#ff4d4d
}

.am .hl{
    display:flex;
    gap:14px;
    align-items:center
}

.am .tag{
    margin-left:auto;
    background:rgba(46,226,122,.2);
    color:#2ee27a;
    font-size:10px;
    padding:2px 8px;
    border-radius:8px;
    font-weight:600
}

.am .dec{
    background:rgba(46,226,122,.22);
    border:1px solid #2ee27a;
    display:inline-block;
    padding:6px 16px;
    border-radius:10px;
    font-weight:700;
    margin:4px 0 10px;
    font-size:15px
}

.am .ag{
    display:flex;
    justify-content:space-between;
    padding:9px 10px;
    margin-top:5px;
    background:rgba(0,0,0,.25);
    border-radius:10px;
    font-size:12.5px
}

.am .ag span:last-child{
    color:#2ee27a
}

.am .al{
    display:flex;
    gap:10px;
    align-items:center;
    padding:8px 0
}

.am .al i{
    width:34px;
    height:34px;
    border-radius:50%;
    display:grid;
    place-items:center;
    font-style:normal;
    flex:none;
    background:rgba(255,77,77,.25)
}

.am .al small{
    color:var(--mut);
    display:block
}

.am .al em{
    margin-left:auto;
    color:var(--mut);
    font-size:11px;
    white-space:nowrap
}

.am .field{
    position:relative;
    display:grid;
    grid-template-columns:1fr 1fr 1fr;
    gap:8px;
    height:250px;
    border-radius:12px;
    padding:8px;
    background-size:cover;
    background-position:center
}

.am .z{
    border-radius:12px;
    border:2px solid #2ee27a;
    display:grid;
    place-items:center;
    text-align:center;
    font-weight:600
}

.am .z1{
    background:rgba(28,107,42,.45)
}

.am .z2{
    border-color:#f5a524;
    background:rgba(154,122,28,.35)
}

.am .z3{
    background:rgba(58,168,58,.35)
}

.am .z span{
    background:rgba(0,0,0,.6);
    padding:7px 11px;
    border-radius:10px
}

.am .irr{
    position:absolute;
    right:14px;
    bottom:14px;
    background:rgba(0,0,0,.75);
    border:1px solid #2ee27a;
    border-radius:12px;
    padding:8px 12px;
    font-weight:700
}

.am .flow{
    display:flex;
    justify-content:space-between;
    text-align:center;
    gap:6px;
    font-size:12px
}

.am .flow div{
    flex:1
}

.am .flow b{
    display:grid;
    place-items:center;
    width:44px;
    height:44px;
    margin:0 auto 6px;
    border-radius:50%;
    background:rgba(46,226,122,.2);
    border:1px solid #2ee27a;
    font-size:19px
}

.am .status{
    display:flex;
    gap:26px;
    padding:10px 16px;
    color:var(--mut);
    background:rgba(9,40,26,.78);
    border:1px solid rgba(60,200,120,.28);
    border-radius:12px;
    flex-wrap:wrap
}

@media(max-width:1100px){
    .am .mets{
        grid-template-columns:repeat(2,1fr)
    }
}

</style>"""


# ==========================================================
# PAGE REGISTRY
# ==========================================================

# (icon, title, views/<file>.py without extension, url slug)

PAGES = [
    ("🏠", "Dashboard", "Dashboard", "dashboard"),

    (
        "🧠",
        "AI Command Center",
        "AI Command Center",
        "ai-command-center"
    ),

    (
        "📡",
        "Live IoT Monitoring",
        "Live IoT Monitoring",
        "live-iot-monitoring"
    ),

    (
        "🌱",
        "Crop Intelligence",
        "Crop Intelligence",
        "crop-intelligence"
    ),

    (
        "💧",
        "Irrigation Automation",
        "💧 Irrigation Automation",
        "irrigation-automation"
    ),

    (
        "⛅",
        "Weather & Forecast",
        "Weather & Forecast",
        "weather-forecast"
    ),

    (
        "🗺️",
        "Field Digital Twin",
        "Field Digital Twin (Beta)",
        "field-digital-twin"
    ),

    (
        "📈",
        "Predictive Analytics",
        "Predictive Analytics",
        "predictive-analytics"
    ),

    (
        "🚨",
        "Alerts & Incidents",
        "Alerts & Incidents",
        "alerts-incidents"
    ),

    (
        "📄",
        "Reports & Insights",
        "Reports & Insights",
        "reports-insights"
    ),

    (
        "🤖",
        "AI Farm Assistant",
        "AI Farm Assistant",
        "ai-farm-assistant"
    ),

    (
        "📟",
        "Device Management",
        "Device Management",
        "device-management"
    )
]


NAV = [
    (ic, n)
    for ic, n, _, _ in PAGES
]

CHIPS = [
    "Why is my soil moisture low?",
    "When will it rain?",
    "How much water do I need?",
    "What is the crop health status?"
]

FARM_KEYS = (
    "sm",
    "t",
    "h",
    "rain",
    "ph",
    "crop",
    "stage"
)

DEFAULTS = dict(
    sm=42,
    t=34,
    h=58,
    rain=20,
    ph=6.8,
    crop="Tomato",
    stage="Vegetative",

    farmer_name=DEFAULT_FARMER_NAME,

    location_query=DEFAULT_LOCATION,
    location_name=DEFAULT_LOCATION,

    lat=DEFAULT_LAT,
    lon=DEFAULT_LON,

    location_error="",

    goto=None,

    irr=False,

    pump_log="",

    ask=None,

    search="",
    search_ans="",

    chat_in="",
    chat_out="",

    q2="",
    a2="",

    rep_out="",

    data_mode="🌐 Live Weather",

    # AI answer boxes for additional pages
    cmd_in="",
    cmd_out="",
    ci_fert="",
    ci_dis="",
    wx_out="",
    pred_out=""
)


def init_state():
    """
    Create per-session defaults.
    Call at the top of every rerun from app.py.
    """

    for k, v in DEFAULTS.items():
        st.session_state.setdefault(k, v)


def H(html):
    """
    Render a block of custom HTML inside the .am style scope.
    """

    st.html(
        f'<div class="am">{html}</div>'
    )


def farm():

    return tuple(
        st.session_state[k]
        for k in FARM_KEYS
    )


# ==========================================================
# AI Q&A
# ==========================================================

def chat_fn(q):

    if not q or not q.strip():
        return "Please enter a question first."

    if client is None:
        return (
            "GROQ_API_KEY is not configured, "
            "so AI cannot respond."
        )

    try:

        return ask_ai(
            ctx(*farm())
            + "\nAnswer briefly and practically."
            + "\nQuestion: "
            + q
        )

    except Exception as e:

        return f"Error: {e}"


def make_report():

    if client is None:
        return "GROQ_API_KEY is not configured."

    try:

        return ask_ai(
            ctx(*farm())
            + "\nWrite a short farm report with sections: "
            "Summary, Risks, Actions for next 7 days. "
            "Use markdown."
        )

    except Exception as e:

        return f"Error: {e}"


def answer_box(target):
    """
    Run a pending AI request with a spinner for this box,
    then show its stored answer.
    """

    pend = st.session_state.ask

    if pend and pend[0] == target:

        with st.spinner(
            "🤖 AI is thinking..."
        ):

            q = pend[1]

            if q == "__report__":

                res = make_report()

            elif target == "search_ans":

                res = (
                    "**🔍 AI answer:** "
                    + chat_fn(q)
                )

            else:

                res = chat_fn(q)

        st.session_state[target] = res
        st.session_state.ask = None

    if st.session_state[target]:

        with st.container(border=True):

            st.markdown(
                st.session_state[target]
            )


# ==========================================================
# CALLBACKS
# ==========================================================

def do_search():
    """
    Search box: jump to a matching page
    via app.py -> st.switch_page or ask the AI.
    """

    q = st.session_state.search.strip()

    ql = q.lower()

    st.session_state.search_ans = ""

    st.session_state.goto = PAGES[0][2]

    if not ql:
        return

    for _, n, f, _slug in PAGES:

        if ql in n.lower():

            st.session_state.goto = f
            return

    st.session_state.ask = (
        "search_ans",
        q
    )


def toggle_irr():

    st.session_state.irr = (
        not st.session_state.irr
    )


def start_pump():

    s = st.session_state

    s.pump_log = (
        f"[{datetime.now():%H:%M:%S}] "
        f"✅ {s.zone} irrigation started "
        f"for {int(s.mins)} min\n"
        + s.pump_log
    )


def refresh_analysis():

    analyze_farm.clear()


def ask_from(key, target):

    st.session_state.ask = (
        target,
        st.session_state[key]
    )


def ask_chip(q):

    st.session_state.ask = (
        "chat_out",
        q
    )


def ask_report():

    st.session_state.ask = (
        "rep_out",
        "__report__"
    )


# ==========================================================
# LIVE FARM DATA
# ==========================================================

def get_state():
    """
    Sync live weather into session state
    and return everything a page needs.
    """

    init_state()

    weather = weather_summary()

    if (
        weather
        and st.session_state.get(
            "data_mode",
            "🌐 Live Weather"
        ) == "🌐 Live Weather"
    ):

        st.session_state.t = round(
            weather["temperature"]
        )

        st.session_state.h = round(
            weather["humidity"]
        )

        st.session_state.rain = round(
            weather["rain"]
        )

        if weather.get("soil_moisture") is not None:

            st.session_state.sm = round(
                weather["soil_moisture"]
            )

    sm, t, h, rain, ph, crop, stage = farm()

    res = analyze_farm(
        sm,
        t,
        h,
        rain,
        ph,
        crop,
        stage,
        client is not None
    )

    sat_date = (
        weather.get(
            "time",
            datetime.now().isoformat()
        )
        if weather
        else
        datetime.now().isoformat()
    )

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

        # Satellite URL:
        # Esri for the default Karachi location,
        # NASA for dynamically selected locations.
        "sat_url": satellite_url(
            st.session_state.lat,
            st.session_state.lon,
            sat_date
        )
    }


def show_location_controls():

    st.subheader(
        "👨‍🌾 Farm Profile & Live Location"
    )

    st.text_input(
        "Farmer name",
        key="farmer_name"
    )

    st.text_input(
        "Farm location",
        key="location_query",
        placeholder="e.g. Karachi, Pakistan"
    )

    c1, c2 = st.columns(2)

    with c1:

        st.button(
            "📍 Use Location",
            type="primary",
            on_click=apply_location
        )

    with c2:

        st.button(
            "↩️ Reset to Karachi",
            on_click=reset_location
        )

    if st.session_state.location_error:

        st.error(
            st.session_state.location_error
        )

    st.caption(
        f"Selected: **{st.session_state.location_name}** · "
        f"Coordinates: "
        f"{st.session_state.lat:.4f}, "
        f"{st.session_state.lon:.4f}"
    )

    st.info(
        "🌐 Weather = live API · "
        "🛰️ Satellite = latest available imagery · "
        "🧪 pH = soil-sensor/demo value"
    )


def coming_soon(file):
    """
    Placeholder body for sections that are not built yet.
    """

    ic, n = next(
        (ic, n)
        for ic, n, f, _ in PAGES
        if f == file
    )

    st.markdown(
        f"## {ic} {n}\n"
        "This section is coming soon. "
        "Currently, Dashboard, Irrigation, Alerts, "
        "AI Assistant, and Reports are available."
    )