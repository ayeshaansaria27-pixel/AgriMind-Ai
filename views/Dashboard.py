
import json
import math
 
import streamlit as st
import streamlit.components.v1 as components
from common import (CHIPS, H, alerts_html, answer_box, ask_chip, ask_from, decision_html,
                    get_state, health_html, hero_html, metrics_html, sensors_html, toggle_irr)
 
# ---- Farm ki location: sirf ek point (center) likhna kaafi hai ----
# Google Maps satellite par kisi bhi kheton wali jagah par right-click karen, lat, lon copy karen.
# (Apni farm na ho to koi bhi demo khet chun len.)
FARM_CENTER = (24.8607, 67.0011)   # <-- yahan apne chune hue khet ka lat, lon likhen
 
ZONE_W_M, ZONE_H_M, GAP_M = 60, 80, 6   # har zone ki chorai, lambai aur zones ke beech gap (meter mein)
 
 
def _make_zones(center, names=("Zone 1", "Zone 2", "Zone 3")):
    """center ke ird gird teen zones barabar barabar side by side bana deta hai"""
    lat, lon = center
    dlat = lambda m: m / 111320
    dlon = lambda m: m / (111320 * math.cos(math.radians(lat)))
    total_w = len(names) * ZONE_W_M + (len(names) - 1) * GAP_M
    out = {}
    for i, n in enumerate(names):
        west = lon - dlon(total_w / 2) + dlon(i * (ZONE_W_M + GAP_M))
        east = west + dlon(ZONE_W_M)
        north, south = lat + dlat(ZONE_H_M / 2), lat - dlat(ZONE_H_M / 2)
        out[n] = [[north, west], [north, east], [south, east], [south, west]]
    return out
 
 
ZONE_COORDS = _make_zones(FARM_CENTER)
# Agar zones ki shape alag chahiye to upar wali line hata kar apne corners khud likh den:
# ZONE_COORDS = {"Zone 1": [[lat, lon], [lat, lon], [lat, lon], [lat, lon]], ...}
 
 
# ---- Har zone ki extra info (DEMO values; asli data aane par yahan se update karen) ----
# last = aakhri baar pani kab diya, trend = pichle ghante mein moisture % kitni badli (+/-)
ZONE_INFO = {
    "Zone 1": {"last": "6 hrs ago", "trend": -4},
    "Zone 2": {"last": "3 hrs ago", "trend": -1},
    "Zone 3": {"last": "1 hr ago", "trend": 2},
}
TARGET_MOISTURE = 60   # is level tak pahunchne ke liye pani chahiye
LITRES_PER_PCT = 15    # andaza: 1% moisture barhane ko kitne litre (apne zone ke size ke hisaab se badlen)
 
 
def _color(m):
    return "#ef4b5a" if m < 20 else "#f0a82a" if m < 40 else "#3ddc84"
 
 
def _status(m):
    return "Critical" if m < 20 else "Needs attention" if m < 40 else "Healthy"
 
 
def _soil(m):
    """Moisture ke hisaab se mitti ka rang: sukhi = halka bhura, geeli = gehra kala-bhura"""
    k = max(0, min(100, m)) / 100
    dry, wet = (150, 112, 72), (44, 30, 19)
    r, g, b = (round(d + (w - d) * k) for d, w in zip(dry, wet))
    return f"rgb({r},{g},{b})"
 
 
def live_field(zones, irr, height=330):
    """zones = [(name, crop, moisture), ...]  irr = True/False (pump chal raha hai ya nahi)"""
    cards = ""
    for name, crop, m in zones:
        c = _color(m)
        wilt = "wilt-hard" if m < 20 else "wilt-soft" if m < 40 else "fresh"
        alert = " alert" if m < 20 else ""
        info = ZONE_INFO.get(name, {})
        last = info.get("last", "-")
        tr = info.get("trend")
        if tr is None:
            trend = '<span class="tr">-</span>'
        else:
            trend = (f'<span class="tr" style="color:{"#3ddc84" if tr > 0 else "#ef4b5a" if tr < 0 else "#8fb7a0"}">'
                     f'{"▲" if tr > 0 else "▼" if tr < 0 else "▬"} {abs(tr)}%/hr</span>')
        need = max(0, TARGET_MOISTURE - m) * LITRES_PER_PCT
        need_txt = f"Needs ~{round(need)} L" if need > 0 else "No water needed"
        z = name.split()[-1]
        s1 = max(0, min(100, round(m + 2)))
        s2 = max(0, min(100, round(m - 2)))
        plants = "".join(
            f'<span style="animation-delay:{(i % 7) * 0.25:.2f}s">'
            f'{"🍅" if (wilt == "fresh" and crop.lower().startswith("tomato") and i % 5 == 2) else "🌿"}</span>'
            for i in range(20)
        )
        cards += f"""
        <div class="zone{alert}" style="border-color:{c};background:{_soil(m)}">
          <div class="plants {wilt}">{plants}</div>
          {'<div class="drops"></div><div class="badge">💧 Irrigating</div>' if irr else ''}
          <div class="hdr">
            <div><b>{name}</b><span>{crop}</span></div>
            <div class="pc" style="color:{c}"><em>{round(m)}%</em><small>{_status(m)}</small></div>
          </div>
          <div class="gauge" title="Soil moisture {round(m)}%">
            <div class="gfill" style="height:{max(m, 3)}%;background:{c}"></div>
          </div>
          <div class="dot tl" style="left:18%;top:42%" data-tip="Z{z}-S1 · {s1}% moisture"></div>
          <div class="dot tr2" style="left:64%;top:70%;animation-delay:.9s" data-tip="Z{z}-S2 · {s2}% moisture"></div>
          <div class="foot">
            <div><span>🕒 {last}</span>{trend}</div>
            <div class="need">💧 {need_txt}</div>
          </div>
        </div>"""
    html = """
    <style>
      body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;color:#e8f5ec}
      .field{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:12px;
             background:#07190f;border-radius:14px;border:1px solid #1d5a3a}
      .zone{position:relative;height:__H__px;border-radius:12px;overflow:hidden;border:2px solid;
            transition:background .6s}
      .zone.alert{animation:alertpulse 1.8s ease-in-out infinite}
      @keyframes alertpulse{0%,100%{box-shadow:0 0 0 0 rgba(239,75,90,0)}50%{box-shadow:0 0 14px 2px rgba(239,75,90,.65)}}
 
      /* header strip: naam + moisture upar, khet neeche nazar aata hai */
      .hdr{position:absolute;top:0;left:0;right:0;display:flex;justify-content:space-between;align-items:center;
           padding:8px 12px;background:rgba(8,14,8,.82);backdrop-filter:blur(2px);
           border-bottom:1px solid rgba(255,255,255,.08)}
      .hdr b{display:block;font-size:14px}
      .hdr span{font-size:12px;color:#9fc4ad}
      .pc{text-align:right}
      .pc em{display:block;font-style:normal;font-size:22px;font-weight:700;line-height:1}
      .pc small{font-size:11px}
 
      /* paudhe */
      .plants{position:absolute;top:58px;bottom:50px;left:10px;right:34px;display:grid;
              grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(5,1fr);place-items:center}
      .plants span{display:inline-block;font-size:26px;transform-origin:bottom center;line-height:1}
      .plants.fresh span{animation:sway 3s ease-in-out infinite}
      @keyframes sway{0%,100%{transform:rotate(-3deg)}50%{transform:rotate(3deg)}}
      .plants.wilt-soft span{filter:sepia(.45) saturate(.9);transform:rotate(14deg) scale(.92)}
      .plants.wilt-hard span{filter:sepia(.95) saturate(.7) brightness(.85);transform:rotate(38deg) scale(.8)}
 
      /* side moisture gauge */
      .gauge{position:absolute;right:8px;top:64px;bottom:54px;width:12px;border-radius:99px;
             background:rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.25);overflow:hidden;
             display:flex;align-items:flex-end}
      .gfill{width:100%;border-radius:99px;transition:height .6s}
 
      /* irrigation */
      .drops{position:absolute;inset:0;opacity:.85;
             background:radial-gradient(circle,rgba(170,220,255,.95) 1.5px,transparent 2px) 0 0/16px 22px;
             animation:rain .7s linear infinite}
      @keyframes rain{to{background-position:0 22px}}
      .badge{position:absolute;top:62px;left:8px;font-size:11px;background:rgba(0,0,0,.7);
             padding:3px 8px;border-radius:99px;color:#7fc4ff}
 
      /* sensor dots */
      .dot{position:absolute;width:11px;height:11px;border-radius:50%;background:#fff;cursor:help;z-index:5;
           animation:pulse 2.4s infinite}
      .dot:hover:after{content:attr(data-tip);position:absolute;top:-30px;white-space:nowrap;font-size:11px;
           background:rgba(0,0,0,.9);color:#e8f5ec;padding:4px 8px;border-radius:6px;border:1px solid rgba(255,255,255,.25)}
      .dot.tl:hover:after{left:0}
      .dot.tr2:hover:after{right:0}
 
      /* neeche info strip */
      .foot{position:absolute;left:0;right:0;bottom:0;padding:6px 12px;background:rgba(8,14,8,.85);
            border-top:1px solid rgba(255,255,255,.08);font-size:11px;color:#9fc4ad;
            display:flex;flex-direction:column;gap:2px}
      .foot>div{display:flex;justify-content:space-between}
      .foot .need{color:#7fc4ff}
      @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,255,255,.7)}70%,100%{box-shadow:0 0 0 12px rgba(255,255,255,0)}}
 
      .legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:10px;color:#8fb7a0;font-size:13px}
      .legend i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:-1px}
      @media(max-width:600px){.plants span{font-size:18px}.pc em{font-size:17px}.hdr{padding:6px 8px}}
    </style>
    <div class="field">__CARDS__</div>
    <div class="legend">
      <span><i style="background:#3ddc84"></i>Healthy (40%+)</span>
      <span><i style="background:#f0a82a"></i>Needs attention (20-40%)</span>
      <span><i style="background:#ef4b5a"></i>Critical (under 20%)</span>
      <span>Sukhi mitti = halka bhura &nbsp;|&nbsp; Geeli mitti = gehra</span>
    </div>
    """
    components.html(html.replace("__H__", str(height)).replace("__CARDS__", cards), height=height + 90)
 
 
def satellite_map(zones, height=430):
    """zones = [(name, crop, moisture), ...]  -- har zone ke corners ZONE_COORDS se aate hain"""
    data = [{"name": n, "crop": c, "m": round(m), "color": _color(m),
             "status": _status(m), "coords": ZONE_COORDS[n]} for n, c, m in zones]
    html = """
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <div id="map" style="height:__H__px;border-radius:12px"></div>
    <script>
      var zones = __DATA__;
      var map = L.map('map');
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {maxZoom:19, attribution:'Imagery © Esri'}).addTo(map);
      var group = L.featureGroup();
      zones.forEach(function(z){
        var p = L.polygon(z.coords, {color:z.color, fillColor:z.color, fillOpacity:.35, weight:2});
        p.bindTooltip('<b>'+z.name+'</b> ('+z.crop+')<br>Moisture: '+z.m+'% · '+z.status, {sticky:true});
        p.addTo(group);
        L.marker(p.getBounds().getCenter(), {icon: L.divIcon({
          className:'', html:'<div style="color:#fff;font:700 13px sans-serif;text-shadow:0 0 4px #000;white-space:nowrap">'
          + z.name + ' · ' + z.m + '%</div>'})}).addTo(map);
      });
      group.addTo(map);
      map.fitBounds(group.getBounds(), {padding:[30,30]});
    </script>
    """
    html = html.replace("__H__", str(height)).replace("__DATA__", json.dumps(data))
    components.html(html, height=height + 10)
 
 
S = get_state()
sm, t, h, rain, ph, crop, stage = (S[k] for k in ("sm", "t", "h", "rain", "ph", "crop", "stage"))
res, weather, n_al = S["res"], S["weather"], S["n_al"]
 
# DEMO: abhi sirf farq dikhane ke liye har zone ki moisture mein offset joda hai.
# Asli sensor values aane par is ki jagah S["z1"], S["z2"], S["z3"] use karen (ya offsets 0 kar den).
ZONE_OFFSET = {"Zone 1": 0, "Zone 2": 12, "Zone 3": 30}
zones = [(n, crop, min(100, sm + o)) for n, o in ZONE_OFFSET.items()]
 
left, right = st.columns([7, 3])
with left:
    H(hero_html(n_al, weather) + metrics_html(sm, t, h, rain, ph))
    a, b = st.columns([5, 6])
    with a:
        H(sensors_html(sm, t, h, ph, weather))
    with b:
        H(health_html(res, crop, stage))
    mode = st.radio("View", ["Live View", "Satellite View"], horizontal=True, label_visibility="collapsed")
 
    if mode == "Satellite View":
        satellite_map(zones)
    else:
        live_field(zones, st.session_state.irr)
with right:
    H(decision_html(res, rain))
    st.button("⏹ Stop Irrigation" if st.session_state.irr else "💧 Start Irrigation", key="irr_btn", type="primary", on_click=toggle_irr)
    H(alerts_html(res))
    H('<div class="card"><h3>🤖 AI Farm Assistant</h3><div style="background:rgba(46,226,122,.12);border-radius:12px;padding:10px">'
      "I'm your AgriMind AI assistant. You can ask me anything about your farm, weather, crops, or system status.</div></div>")
    for j, c in enumerate(CHIPS):
        st.button(c, key=f"chip{j}", on_click=ask_chip, args=(c,))
    st.text_input("Question", key="chat_in", placeholder="Type your question...", label_visibility="collapsed",
                  on_change=ask_from, args=("chat_in", "chat_out"))
    st.button("➤ Ask", key="chat_btn", type="primary", on_click=ask_from, args=("chat_in", "chat_out"))
    answer_box("chat_out")
 
