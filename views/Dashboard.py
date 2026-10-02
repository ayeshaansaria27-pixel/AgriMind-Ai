import streamlit as st
import streamlit.components.v1 as components
from common import (CHIPS, WORKFLOW, H, alerts_html, answer_box, ask_chip, ask_from, decision_html,
                    field_html, get_state, health_html, hero_html, metrics_html, sensors_html, toggle_irr)

# ---- Apni farm ke asli coordinates yahan likhein ----
FARM_LAT, FARM_LON = 24.8607, 67.0011


def satellite_map(sm, lat=FARM_LAT, lon=FARM_LON, height=430):
    color = "#ef4b5a" if sm < 20 else "#f0a82a" if sm < 40 else "#3ddc84"
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

    # ---- Satellite mode mein asli map, warna purana field view ----
    if mode == "Satellite View":
        satellite_map(sm)
    else:
        H(field_html(sm, crop, mode, st.session_state.irr, S["sat_url"], st.session_state.location_name))

    H(WORKFLOW)
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
