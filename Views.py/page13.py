import time

import streamlit as st
from common import H
from farm_utils import DEVICE_TYPES, devices_df, get_devices

devs = get_devices()
ids = [d["id"] for d in devs]
pumps = [d["id"] for d in devs if d["type"] == "Pump Controller"]


def msg(text):
    st.session_state["dm_msg"] = text


def log_pump(text):
    old = str(st.session_state.get("pump_log", ""))
    st.session_state["pump_log"] = f"{time.strftime('%H:%M:%S')}  {text}\n" + old


def add_device():
    typ = st.session_state.get("dm_type", DEVICE_TYPES[0])
    zone = st.session_state.get("dm_zone", "Zone 1")
    prefix = "".join(w[0] for w in typ.split())[:2].upper()
    n = sum(1 for d in devs if d["id"].startswith(prefix)) + 1
    new_id = f"{prefix}-{n:02d}"
    while new_id in ids:
        n += 1
        new_id = f"{prefix}-{n:02d}"
    devs.append({"id": new_id, "type": typ, "zone": zone, "status": "Online", "battery": 100, "signal": -60,
                 "calibrated": "Not yet", "offset": 5})
    msg(f"✅ {new_id} ({typ}, {zone}) add ho gaya")


def remove_device():
    did = st.session_state.get("dm_remove")
    st.session_state["_devices"] = [d for d in devs if d["id"] != did]
    msg(f"🗑️ {did} hata diya gaya")


def calibrate():
    did = st.session_state.get("dm_cal")
    for d in devs:
        if d["id"] == did:
            d["calibrated"] = time.strftime("%d %b %H:%M")
    msg(f"🎯 {did} calibrate ho gaya")


def pump_test(on):
    did = st.session_state.get("dm_pump")
    log_pump(f"Pump test {did}: {'ON' if on else 'OFF'}")
    msg(f"{'▶' if on else '⏹'} {did} test {'ON' if on else 'OFF'} bheja gaya")


H('<div class="card"><h3>🔌 Device Management</h3>Devices ki list, add/remove, calibrate aur pump test. '
  "Baad mein asli ESP32 yahin se jurega.</div>")

if st.session_state.get("dm_msg"):
    st.info(st.session_state.pop("dm_msg"))

st.dataframe(
    devices_df(), hide_index=True,
    column_config={"Battery (%)": st.column_config.ProgressColumn("Battery", min_value=0, max_value=100, format="%d%%")},
)

a, b = st.columns(2)
with a:
    H('<div class="card"><h3>➕ Device add karein</h3></div>')
    st.selectbox("Type", DEVICE_TYPES, key="dm_type")
    st.selectbox("Zone", ["Zone 1", "Zone 2", "Zone 3", "Farm"], key="dm_zone")
    st.button("➕ Add device", type="primary", on_click=add_device)
with b:
    H('<div class="card"><h3>🛠️ Calibrate / Remove</h3></div>')
    if ids:
        st.selectbox("Device (calibrate)", ids, key="dm_cal")
        st.button("🎯 Calibrate", on_click=calibrate)
        st.selectbox("Device (remove)", ids, key="dm_remove")
        st.button("🗑️ Remove", on_click=remove_device)
    else:
        st.write("Koi device nahi hai.")

H('<div class="card"><h3>💧 Pump test</h3></div>')
if pumps:
    st.selectbox("Pump", pumps, key="dm_pump")
    p1, p2 = st.columns(2)
    p1.button("▶ Test ON", type="primary", on_click=pump_test, args=(True,))
    p2.button("⏹ Test OFF", on_click=pump_test, args=(False,))
    st.caption("Test ka record Irrigation Automation ke log mein bhi likha jata hai.")
else:
    st.write("Koi Pump Controller add nahi hai.")
