import streamlit as st
import streamlit.components.v1 as components
from common import (CHIPS, H, alerts_html, answer_box, ask_chip, ask_from, decision_html,
                    get_state, health_html, hero_html, metrics_html, sensors_html, toggle_irr)

# ---- Apni farm ke asli coordinates yahan likhein ----
FARM_LAT, FARM_LON = 24.8607, 67.0011


def _color(m):
    return "#ef4b5a" if m < 20 else "#f0a82a" if m < 40 else "#3ddc84"


def _status(m):
    return "Critical" if m < 20 else "Needs attention" if m < 40 else "Healthy"


def live_field(zones, irr, height=330):
    """zones = [(name, crop, moisture), ...]  irr = True/False (pump chal raha hai ya nahi)"""
    cards = ""
    for i, (name, crop, m) in enumerate(zones):
        c = _color(m)
        cards += f"""
        <div class="zone" style="border-color:{c}">
          <div class="rows"></div>
          <div class="water" style="height:{max(m, 3)}%"></div>
          {'<div class="drops"></div><div class="badge">💧 Irrigating</div>' if irr else ''}
          <div class="dot" style="left:20%;top:22%"></div>
          <div class="dot" style="left:76%;top:68%;animation-delay:.9s"></div>
          <div class="lab"><b>{name}</b><span>({crop})</span>
            <em style="color:{c}">{round(m)}%</em><small style="color:{c}">{_status(m)}</small></div>
        </div>"""
    html = """
    <style>
      body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;color:#e8f5ec}
      .field{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:12px;
             background:#07190f;border-radius:14px;border:1px solid #1d5a3a}
      .zone{position:relative;height:__H__px;border-radius:12px;overflow:hidden;border:2px solid;background:#2a1d12}
      .rows{position:absolute;inset:0;background:
            repeating-linear-gradient(90deg,transparent 0 22px,rgba(90,150,60,.45) 22px 27px),
            repeating-linear-gradient(0deg,rgba(0,0,0,.2) 0 3px,transparent 3px 9px)}
      .water{position:absolute;left:0;right:0;bottom:0;
             background:linear-gradient(180deg,rgba(74,168,255,.6),rgba(30,100,200,.5))}
      .water:before{content:"";position:absolute;top:-3px;left:0;right:0;height:6px;
             background:rgba(160,215,255,.55);filter:blur(2px)}
      .drops{position:absolute;inset:0;opacity:.85;
             background:radial-gradient(circle,rgba(170,220,255,.95) 1.5px,transparent 2px) 0 0/16px 22px;
             animation:rain .7s linear infinite}
      @keyframes rain{to{background-position:0 22px}}
      .badge{position:absolute;top:8px;right:8px;font-size:11px;background:rgba(0,0,0,.65);
             padding:3px 8px;border-radius:99px;color:#7fc4ff}
      .dot{position:absolute;width:10px;height:10px;border-radius:50%;background:#fff;
           animation:pulse 2.4s infinite}
      @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,255,255,.7)}70%,100%{box-shadow:0 0 0 12px rgba(255,255,255,0)}}
      .lab{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
           background:rgba(10,15,8,.85);padding:10px 14px;border-radius:10px;text-align:center;min-width:96px}
      .lab b{display:block;font-size:14px}.lab span{font-size:12px;color:#8fb7a0}
      .lab em{display:block;font-style:normal;font-size:24px;font-weight:700;margin-top:2px}
      .lab small{font-size:11px}
      .legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:10px;color:#8fb7a0;font-size:13px}
      .legend i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:-1px}
      @media(max-width:600px){.lab{padding:6px 8px;min-width:0}.lab em{font-size:18px}}
    </style>
    <div class="field">__CARDS__</div>
    <div class="legend">
      <span><i style="background:#3ddc84"></i>Healthy (40%+)</span>
      <span><i style="background:#f0a82a"></i>Needs attention (20-40%)</span>
      <span><i style="background:#ef4b5a"></i>Critical (under 20%)</span>
    </div>
    """
    components.html(html.replace("__H__", str(height)).replace("__CARDS__", cards), height=height + 90)


def satellite_map(sm, lat=FARM_LAT, lon=FARM_LON, height=430):
    color = _color(sm)
    html = """
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <div id="map" style="height:__H__px;border-radius:12px"></div>
    <script>
      var lat=__LAT__, lon=__LON__;
      var map=L.map('map').setView([lat,lon],17);
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {maxZoom:19, attribution:'Imagery © Esri'}).addTo(map);
      for (var i=0;i<3;i++){
        var x = lon - 0.0006 + i*0.0006;
        L.rectangle([[lat-0.0002,x],[lat+0.0002,x+0.00055]],
          {color:'__C__', fillColor:'__C__', fillOpacity:.35, weight:2})
          .addTo(map).bindTooltip('Zone '+(i+1)+' · moisture __SM__%');
      }
    </script>
    """
    html = (html.replace("__H__", str(height)).replace("__LAT__", str(lat))
                .replace("__LON__", str(lon)).replace("__C__", color)
                .replace("__SM__", str(round(sm))))
    components.html(html, height=height + 10)


S = get_state()
sm, t, h, rain, ph, crop, stage = (S[k] for k in ("sm", "t", "h", "rain", "ph", "crop", "stage"))
res, weather, n_al = S["res"], S["weather"], S["n_al"]

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
        satellite_map(sm)
    else:
        # Agar har zone ki alag moisture hai to yahan alag values likhein
        live_field([("Zone 1", crop, sm), ("Zone 2", crop, sm), ("Zone 3", crop, sm)],
                   st.session_state.irr)
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
