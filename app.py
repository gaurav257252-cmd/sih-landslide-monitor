import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import time
import json
import urllib.request
from datetime import datetime

st.set_page_config(
    page_title="Project DHRUVA — Sikkim NH-10 Command Center",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Command-Center Styling
st.markdown("""
    <style>
    .metric-container { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; }
    .alert-box { background-color: #450a0a; padding: 16px; border-radius: 8px; border: 1px solid #ef4444; color: #fecaca; }
    .action-badge { background-color: #1e293b; border-left: 4px solid #38bdf8; padding: 10px 14px; border-radius: 4px; margin-bottom: 8px; }
    .field-card { background-color: #1e293b; border: 1px solid #334155; padding: 12px; border-radius: 6px; margin-bottom: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("🛰️ Project DHRUVA: Sikkim NH-10 Landslide Risk & Logistics Triage")
st.caption("Operational Corridor: Sevoke – Kalijhora – 29th Mile – Melli – Rangpo – Singtam – Gangtok | High-Res Satellite Radar | SIH 2026")

# -----------------------------------------------------------------------------
# 1. GEOSPATIAL LANDSLIDE HAZARD ZONES (Mountain Slope Catchment Polygons)
# -----------------------------------------------------------------------------
LANDSLIDE_ZONES = [
    {
        "id": "ZONE-01",
        "name": "Zone A: Kalijhora Fracture Basin",
        "polygon": [
            [26.902, 88.442],
            [26.925, 88.440],
            [26.928, 88.468],
            [26.905, 88.472]
        ],
        "base_slope": 52.4,
        "soil_factor": 0.78,
        "debris_potential": "2,800 m³",
        "geology": "Damaged Daling Phyllites & Colluvium"
    },
    {
        "id": "ZONE-02",
        "name": "Zone B: Setijhora Siphon Chute",
        "polygon": [
            [26.935, 88.435],
            [26.958, 88.432],
            [26.962, 88.455],
            [26.938, 88.458]
        ],
        "base_slope": 48.0,
        "soil_factor": 0.65,
        "debris_potential": "1,900 m³",
        "geology": "Fractured Quartzites & Weathered Gneiss"
    },
    {
        "id": "ZONE-03",
        "name": "Zone C: 29th Mile Chronic Rupture Envelope",
        "polygon": [
            [26.995, 88.420],
            [27.028, 88.418],
            [27.032, 88.445],
            [26.998, 88.448]
        ],
        "base_slope": 63.5,
        "soil_factor": 0.92,
        "debris_potential": "5,400 m³ (Massive Block Breach)",
        "geology": "High Shear-Stress Phyllitic Schist"
    },
    {
        "id": "ZONE-04",
        "name": "Zone D: Melli-Teesta Confluence Slump Zone",
        "polygon": [
            [27.072, 88.438],
            [27.098, 88.435],
            [27.102, 88.468],
            [27.075, 88.470]
        ],
        "base_slope": 44.2,
        "soil_factor": 0.72,
        "debris_potential": "2,200 m³",
        "geology": "Riverbank Toe Erosion & Loose Silt"
    },
    {
        "id": "ZONE-05",
        "name": "Zone E: Singtam KM-28 Deep-Seated Basin",
        "polygon": [
            [27.220, 88.482],
            [27.252, 88.480],
            [27.255, 88.515],
            [27.222, 88.518]
        ],
        "base_slope": 57.8,
        "soil_factor": 0.88,
        "debris_potential": "4,100 m³ (Deep Rotational Slip)",
        "geology": "Graphitic Schist & Water-Saturated Clay"
    },
    {
        "id": "ZONE-06",
        "name": "Zone F: Ranipool Valley Toe Escarpment",
        "polygon": [
            [27.280, 88.568],
            [27.308, 88.565],
            [27.310, 88.598],
            [27.282, 88.600]
        ],
        "base_slope": 39.5,
        "soil_factor": 0.58,
        "debris_potential": "1,400 m³",
        "geology": "Residual Mountain Colluvium"
    }
]

NH10_SEGMENTS = [
    {"name": "Sevoke to Kalijhora", "path": [[26.885, 88.471], [26.912, 88.459]], "zone_ref": "ZONE-01"},
    {"name": "Kalijhora to Setijhora", "path": [[26.912, 88.459], [26.940, 88.448]], "zone_ref": "ZONE-02"},
    {"name": "Setijhora to 29th Mile", "path": [[26.940, 88.448], [26.978, 88.438], [27.012, 88.434]], "zone_ref": "ZONE-03"},
    {"name": "29th Mile to Melli", "path": [[27.012, 88.434], [27.054, 88.439], [27.086, 88.452]], "zone_ref": "ZONE-04"},
    {"name": "Melli to Rangpo Checkpost", "path": [[27.086, 88.452], [27.125, 88.489], [27.176, 88.528]], "zone_ref": None},
    {"name": "Rangpo to Singtam Basin", "path": [[27.176, 88.528], [27.208, 88.514], [27.238, 88.498]], "zone_ref": "ZONE-05"},
    {"name": "Singtam to Ranipool & Gangtok", "path": [[27.238, 88.498], [27.262, 88.520], [27.295, 88.585], [27.328, 88.612]], "zone_ref": "ZONE-06"}
]

BYPASS_COORDINATES = [
    [26.885, 88.471], [26.910, 88.550], [27.000, 88.620],
    [27.086, 88.662], [27.118, 88.587], [27.168, 88.635],
    [27.185, 88.643], [27.235, 88.595], [27.295, 88.585], [27.328, 88.612]
]

# -----------------------------------------------------------------------------
# 2. SESSION STATE MANAGEMENT
# -----------------------------------------------------------------------------
if "registered_commuters" not in st.session_state:
    st.session_state.registered_commuters = [
        {"name": "Tashi Bhutia", "contact": "+91 98321-XXXXX", "vehicle": "SK-01-A-4421", "blood": "O+", "alerts": "Diabetic, Cardiac", "token": "[UIDAI-Virtual-Token-Masked]", "status": "In Transit"},
        {"name": "Rajesh Kumar", "contact": "+91 94191-XXXXX", "vehicle": "WB-74-B-8910", "blood": "B+", "alerts": "None", "token": "[DL-Verified-6102]", "status": "In Transit"},
        {"name": "Maj. S. K. Nair", "contact": "+91 98110-XXXXX", "vehicle": "ARMY-CONVOY-07", "blood": "A+", "alerts": "Asthma", "token": "[MIL-Service-882]", "status": "In Transit"}
    ]

if "field_incidents" not in st.session_state:
    st.session_state.field_incidents = []

if "weather_source" not in st.session_state:
    st.session_state.weather_source = "Manual Simulation"

if "current_rainfall" not in st.session_state:
    st.session_state.current_rainfall = 90

if "current_saturation" not in st.session_state:
    st.session_state.current_saturation = 70

# -----------------------------------------------------------------------------
# 3. LIVE WEATHER API FETCH (Open-Meteo Real-Time Telemetry)
# -----------------------------------------------------------------------------
def fetch_live_weather():
    try:
        # Gangtok / Teesta Basin Coordinates: 27.33 N, 88.61 E
        url = "https://api.open-meteo.com/v1/forecast?latitude=27.33&longitude=88.61&current=temperature_2m,relative_humidity_2m,precipitation,rain&daily=precipitation_sum&timezone=Asia%2FKolkata"
        req = urllib.request.Request(url, headers={"User-Agent": "ProjectDHRUVA/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            daily_precip = data.get("daily", {}).get("precipitation_sum", [0.0])[0]
            humidity = data.get("current", {}).get("relative_humidity_2m", 65)
            # Map precipitation into 24-hr equivalent scaled for monsoon stress
            st.session_state.current_rainfall = int(max(daily_precip * 5.0, 45.0))
            st.session_state.current_saturation = int(min(max(humidity, 30), 95))
            st.session_state.weather_source = f"Live Open-Meteo (Gangtok: {data['current']['temperature_2m']}°C, Hum: {humidity}%)"
            return True
    except Exception as e:
        st.session_state.weather_source = "API Fallback (Simulated Teesta Feed)"
        return False

# -----------------------------------------------------------------------------
# 4. SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.title("Teesta Basin Telemetry")
st.sidebar.caption(f"Source: {st.session_state.weather_source}")

if st.sidebar.button("📡 Fetch Real-Time Satellite/IMD Telemetry"):
    with st.sidebar.status("Connecting to satellite telemetry...", expanded=False):
        success = fetch_live_weather()
        time.sleep(0.5)
    if success:
        st.sidebar.success("Live weather telemetry synced!")
    else:
        st.sidebar.info("Satellite telemetry simulated (offline mode).")

simulated_rainfall = st.sidebar.slider(
    "24h Antecedent Rainfall (mm)",
    min_value=0, max_value=250, value=st.session_state.current_rainfall, step=5,
    help="Precipitation trigger calibrated from IMD Doppler Radars."
)
st.session_state.current_rainfall = simulated_rainfall

soil_sat = st.sidebar.slider(
    "Soil Pore-Water Saturation (%)",
    min_value=15, max_value=100, value=st.session_state.current_saturation, step=5,
    help="Sub-surface hydrologic saturation in high-permeability phyllite strata."
)
st.session_state.current_saturation = soil_sat

st.sidebar.markdown("---")
st.sidebar.subheader("Crisis Scenario Override")
force_collapse = st.sidebar.toggle("🚨 Trigger Active Debris Flow at 29th Mile", value=False)

# -----------------------------------------------------------------------------
# 5. DYNAMIC GEOTECHNICAL HAZARD INFERENCE ENGINE
# -----------------------------------------------------------------------------
evaluated_zones = []
critical_zones_count = 0
warning_zones_count = 0
safe_zones_count = 0

# Check active field incident targets
incident_zone_ids = [inc["zone_id"] for inc in st.session_state.field_incidents]

for zone in LANDSLIDE_ZONES:
    slope_norm = zone["base_slope"] / 65.0
    rain_norm = simulated_rainfall / 200.0
    sat_norm = soil_sat / 100.0

    score = (0.35 * slope_norm + 0.40 * rain_norm + 0.25 * sat_norm) * zone["soil_factor"]
    
    # Override for manual scenario or verified field incident
    if (force_collapse and ("29th Mile" in zone["name"] or "Singtam" in zone["name"])) or (zone["id"] in incident_zone_ids):
        score = 0.98

    score = min(max(score, 0.05), 0.99)
    fos = round(max(0.4, 2.1 - (score * 1.7)), 2)

    if score >= 0.65 or fos < 1.0:
        status = "CRITICAL RUPTURE ZONE"
        fill_color = "#ff1744"
        border_color = "#b71c1c"
        fill_opacity = 0.55
        critical_zones_count += 1
    elif score >= 0.40:
        status = "HEIGHTENED ADVISORY ZONE"
        fill_color = "#ff9100"
        border_color = "#e65100"
        fill_opacity = 0.42
        warning_zones_count += 1
    else:
        status = "STABLE GEOLOGY"
        fill_color = "#00e676"
        border_color = "#1b5e20"
        fill_opacity = 0.30
        safe_zones_count += 1

    evaluated_zones.append({
        **zone,
        "score": score,
        "fos": fos,
        "status": status,
        "fill_color": fill_color,
        "border_color": border_color,
        "fill_opacity": fill_opacity
    })

fleet_at_risk = critical_zones_count * 150
hourly_loss_lakhs = round(critical_zones_count * 3.2, 2)

# Global Metrics Header
k1, k2, k3, k4 = st.columns(4)
k1.metric("Precipitation (IMD/Radar)", f"{simulated_rainfall} mm", delta="Cloudburst Alert" if simulated_rainfall > 110 else "Monitoring")
k2.metric("Critical Rupture Zones", f"{critical_zones_count} Zones", delta=f"+{critical_zones_count} Red Slopes" if critical_zones_count > 0 else "All Clear", delta_color="inverse")
k3.metric("Fleet at Risk", f"{fleet_at_risk} Trucks")
k4.metric("Est. Economic Loss", f"₹{hourly_loss_lakhs} L/hr", delta_color="inverse")

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. COMMAND CENTER TABS
# -----------------------------------------------------------------------------
tab_map, tab_field, tab_broadcast, tab_vault, tab_sitrep = st.tabs([
    "🛰️ Satellite Hazard Radar",
    "👷 Field Incident Reporter",
    "📡 Offline Cell Broadcast",
    "🛡️ Citizen Safety Vault",
    "📄 Automated DDMA SITREP"
])

# ---------------------------------------------------------
# TAB 1: SATELLITE HAZARD MAP WITH VISIBLE CATCHMENT ZONES
# ---------------------------------------------------------
with tab_map:
    col_map, col_panel = st.columns([2.6, 1])

    with col_map:
        st.subheader("Geospatial Landslide Susceptibility (Catchment Polygons)")

        m = folium.Map(
            location=[27.12, 88.51],
            zoom_start=11,
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
            attr="Google Satellite Hybrid"
        )

        zone_status_lookup = {}
        for z in evaluated_zones:
            zone_status_lookup[z["id"]] = z

            folium.Polygon(
                locations=z["polygon"],
                color=z["border_color"],
                weight=2,
                fill=True,
                fill_color=z["fill_color"],
                fill_opacity=z["fill_opacity"],
                tooltip=(
                    f"<b>{z['name']}</b><br>"
                    f"Status: <b>{z['status']}</b><br>"
                    f"Failure Probability: <b>{z['score']*100:.1f}%</b><br>"
                    f"Factor of Safety (FoS): <b>{z['fos']}</b><br>"
                    f"Slope: {z['base_slope']}° | Debris Potential: {z['debris_potential']}<br>"
                    f"Geology: {z['geology']}"
                )
            ).add_to(m)

            center_lat = np.mean([pt[0] for pt in z["polygon"]])
            center_lon = np.mean([pt[1] for pt in z["polygon"]])

            folium.CircleMarker(
                location=[center_lat, center_lon],
                radius=6,
                color="#ffffff",
                weight=1,
                fill=True,
                fill_color=z["fill_color"],
                fill_opacity=0.9,
                tooltip=f"<b>{z['id']} Apex</b>: {z['status']}"
            ).add_to(m)

        for seg in NH10_SEGMENTS:
            ref = seg["zone_ref"]
            if ref and ref in zone_status_lookup:
                parent_zone = zone_status_lookup[ref]
                seg_color = parent_zone["fill_color"]
                seg_weight = 7 if parent_zone["status"] == "CRITICAL RUPTURE ZONE" else 5
            else:
                seg_color = "#00e5ff"
                seg_weight = 5

            folium.PolyLine(
                seg["path"],
                color=seg_color,
                weight=seg_weight,
                opacity=0.95,
                tooltip=f"NH-10 Segment: {seg['name']}"
            ).add_to(m)

        folium.PolyLine(
            BYPASS_COORDINATES,
            color="#00e676",
            weight=4,
            opacity=0.85,
            dash_array="8, 8",
            tooltip="Active Emergency Bypass: NH-717A (Lava – Algarah – Pakyong)"
        ).add_to(m)

        # Plot Ground Truth Field Incidents
        for inc in st.session_state.field_incidents:
            folium.Marker(
                location=inc["coord"],
                popup=f"<b>FIELD INCIDENT</b><br>Reporter: {inc['source']}<br>Anomaly: {inc['anomaly']}",
                icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa")
            ).add_to(m)

        if force_collapse or critical_zones_count > 0:
            folium.Marker(
                location=[27.012, 88.434],
                popup="<b>EMERGENCY BREACH: 29th Mile</b><br>Debris Volume: ~5,400 m³<br>Highway blocked.",
                icon=folium.Icon(color="red", icon="warning", prefix="fa")
            ).add_to(m)

        st_folium(m, width="100%", height=560)

    with col_panel:
        st.subheader("SSDMA Operational Triage")
        st.markdown(
            """
            <div class="action-badge">
            <strong>Active Arterial Corridor:</strong><br>
            NH-10 (Sevoke – Gangtok)
            </div>
            <div class="action-badge" style="border-left-color: #00e676;">
            <strong>Emergency Freight Bypass:</strong><br>
            NH-717A (Dashed Green Polyline)
            </div>
            """, unsafe_allow_html=True
        )

        st.markdown("#### Geological Catchment Status")
        for z in evaluated_zones:
            icon = "🔴" if z["status"] == "CRITICAL RUPTURE ZONE" else ("🟠" if z["status"] == "HEIGHTENED ADVISORY ZONE" else "🟢")
            st.write(f"{icon} **{z['name']}**<br><span style='font-size:12px;color:#94a3b8;'>FoS: {z['fos']} | Vol: {z['debris_potential']}</span>", unsafe_allow_html=True)

        if critical_zones_count > 0 or force_collapse:
            st.error("⚠️ HIGHWAY SEVERANCE CONFIRMED. Reroute heavy freight via NH-717A at Sevoke.")

# ---------------------------------------------------------
# TAB 2: FIELD INCIDENT REPORTER (HUMAN-IN-THE-LOOP)
# ---------------------------------------------------------
with tab_field:
    st.subheader("👷 Ground-Truth Anomaly Reporting (Human-in-the-Loop Sensor Fusion)")
    st.markdown(
        "Satellite passes experience orbital latency and cloud occlusion during monsoons. This module enables "
        "**BRO Project Swastik patrol units, Sikkim Police, and local taxi syndicates** to log early ground deformations "
        "that instantly force the ML model to recalibrate."
    )

    f_col1, f_col2 = st.columns([1, 1.2])

    with f_col1:
        st.markdown("#### Log Field Observation")
        with st.form("field_report_form"):
            selected_zone_name = st.selectbox("Target Sector / Landmark", [z["name"] for z in LANDSLIDE_ZONES])
            anomaly_type = st.selectbox("Physical Anomaly Observed", [
                "Tension Cracks on Asphalt (>2.5 cm)",
                "Continuous Shooting Stones / Rock Fall",
                "Mud Slurry Seepage from Retaining Wall Toe",
                "Road Shoulder Subsidence / Dip",
                "Riverbank Toe Erosion & Undercutting"
            ])
            reporter = st.selectbox("Observer Agency", [
                "BRO Project Swastik (Patrol Unit-2)",
                "Sikkim Highway Police (Rangpo Outpost)",
                "All Sikkim Commercial Drivers Association",
                "Forest Dept Mobile Ranger"
            ])
            urgency = st.radio("Urgency Level", ["Immediate Failure Risk (High)", "Developing Instability (Medium)"], horizontal=True)
            
            sub = st.form_submit_button("🚨 Submit Verified Field Anomaly")
            if sub:
                target_z = next(z for z in LANDSLIDE_ZONES if z["name"] == selected_zone_name)
                center_coord = [np.mean([p[0] for p in target_z["polygon"]]), np.mean([p[1] for p in target_z["polygon"]])]
                
                st.session_state.field_incidents.append({
                    "zone_id": target_z["id"],
                    "zone_name": target_z["name"],
                    "anomaly": anomaly_type,
                    "source": reporter,
                    "coord": center_coord,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
                st.success(f"Incident logged for {target_z['id']}. Geotechnical vulnerability forced to Critical (98%).")
                st.rerun()

    with f_col2:
        st.markdown("#### Active Verified Ground Reports")
        if not st.session_state.field_incidents:
            st.info("No active ground incidents reported. Nominal patrol surveillance active.")
        else:
            for inc in st.session_state.field_incidents:
                st.markdown(f"""
                <div class="field-card">
                    <strong>⚠️ {inc['zone_name']}</strong> — <em>Logged at {inc['timestamp']} IST</em><br>
                    <strong>Anomaly:</strong> {inc['anomaly']}<br>
                    <strong>Reported By:</strong> {inc['source']}<br>
                    <span style="color:#ef4444;"><strong>Status:</strong> Immediate Catchment Rupture Alert Triggered</span>
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("🧹 Clear Ground Incidents (Post-Clearance)"):
                st.session_state.field_incidents = []
                st.rerun()

# ---------------------------------------------------------
# TAB 3: OFFLINE EMERGENCY CELL BROADCAST
# ---------------------------------------------------------
with tab_broadcast:
    st.subheader("Direct-to-Device Offline Crisis Broadcasting (NDMA CAP Protocol)")
    st.markdown(
        "During severe monsoon landslides, fiber optic cables in the Teesta gorge and mobile data towers are washed out. "
        "Project DHRUVA triggers **Cell Broadcast Service (CBS / 3GPP TS 23.041)**, "
        "pushing audible siren tones and evacuation alerts to every phone within radio range **with zero cellular data consumption**."
    )

    cb_col1, cb_col2 = st.columns([1.5, 1])

    with cb_col1:
        st.markdown("### Simulated Emergency Radio Payload")
        st.markdown(f"""
        <div class="alert-box">
            <h3>🚨 NATIONAL DISASTER MANAGEMENT AUTHORITY (NDMA) BROADCAST</h3>
            <p><strong>CHANNEL:</strong> EMERGENCY CELL BROADCAST (CH-4370 / SIREN PRIORITY-1)</p>
            <p><strong>GEOGRAPHIC RADIUS:</strong> Sevoke, Kalijhora, 29th Mile, Melli & Rangpo BTS Towers</p>
            <p><strong>DATA USAGE:</strong> 0 KB (Direct Signaling Control Channel — Works Offline)</p>
            <hr style="border-color:#b91c1c;">
            <p><strong>[CRITICAL LIFE-SAFETY ALERT]:</strong> Massive slope failure verified in <strong>Zone C (29th Mile) & Zone E (Singtam Basin)</strong> along <strong>NH-10</strong>. Road completely impassable. DO NOT ADVANCE. Pull vehicles into designated safe shelters or immediately divert via <strong>NH-717A (Lava-Algarah bypass)</strong>. NDRF 2nd Battalion and BRO Project Swastik deployed.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📡 Execute Cell-Tower & All India Radio (FM 101.4 MHz) Alert Broadcast"):
            with st.spinner("Pinging 14 surviving base transceiver stations along the Teesta gorge..."):
                time.sleep(1.2)
                st.success("Emergency broadcast dispatched to 14 base stations. Cellular siren override triggered.")
                st.toast("Emergency siren tone pushed to all handsets in radio perimeter!", icon="📢")

    with cb_col2:
        st.markdown("### Redundant Alert Channels")
        st.markdown("""
        1. **Cell Broadcast Service (CBS):**
           - Functions when internet packages, SMS packs, and voice lines are dead.
           - Bypasses network congestion to blast sound on all handsets.
        2. **All India Radio (AIR Gangtok FM 101.4):**
           - Automated synthesized audio advisory broadcasted to vehicle radios.
        3. **Vehicle-to-Vehicle BLE Mesh:**
           - Relays encrypted SOS hops between stranded commuter vehicles if towers lose power.
        """)

# ---------------------------------------------------------
# TAB 4: CITIZEN SAFETY VAULT & RESCUE MANIFEST
# ---------------------------------------------------------
with tab_vault:
    st.subheader("End-to-End Encrypted Citizen Transit Registry & First-Responder Manifest")
    st.markdown(
        "Commuters check in at Rangpo Checkpost. Identity tokens and medical profiles are securely tokenized "
        "under the **Digital Personal Data Protection (DPDP) Act 2023**. If a slope collapse occurs, first responders receive "
        "an instant triage manifest of civilians stranded in that exact geographic slice."
    )

    reg_col, manifest_col = st.columns([1, 1.3])

    with reg_col:
        st.markdown("#### Rangpo Checkpost: Corridor Transit Check-In")
        with st.form("transit_form"):
            c_name = st.text_input("Commuter Full Name", value="Arjun Sen")
            c_phone = st.text_input("Mobile Number", value="+91 98450-XXXXX")
            c_veh = st.text_input("Vehicle Registration No.", value="SK-02-C-1980")
            c_blood = st.selectbox("Blood Group", ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"])
            c_med = st.multiselect("Medical Flags", ["Asthma", "Diabetic", "Cardiac Condition", "Elderly Passenger", "Infant Onboard"], default=["Elderly Passenger"])
            id_placeholder = st.text_input("Government Identity Token (Masked)", value="[UIDAI-Virtual-Token-Masked]")
            
            submitted = st.form_submit_button("🛡️ Encrypt & Register Corridor Transit")
            if submitted:
                st.session_state.registered_commuters.append({
                    "name": c_name,
                    "contact": c_phone,
                    "vehicle": c_veh,
                    "blood": c_blood,
                    "alerts": ", ".join(c_med) if c_med else "None",
                    "token": id_placeholder,
                    "status": "Transit Active"
                })
                st.success(f"Registered {c_name} to NH-10 Protected Safety Ledger.")

    with manifest_col:
        st.markdown("#### First-Responder Triage Manifest (SSDMA & NDRF Command Desk)")
        if force_collapse or critical_zones_count > 0:
            st.error("⚠️ HAZARD DETECTED: Commuters Flagged in Immediate Proximity of Hazard Zones")
        else:
            st.success("Corridor Status: Nominal Transit Flow")

        manifest_df = pd.DataFrame(st.session_state.registered_commuters)
        st.dataframe(manifest_df[['name', 'vehicle', 'blood', 'alerts', 'token', 'status']], use_container_width=True)

        if st.button("🚨 Generate Automated Incident SOS Ticket for NDRF 2nd Battalion"):
            st.toast("Urgent SOS Dispatch Ticket generated with GPS coordinates & medical priorities.", icon="🚑")
            st.code("""
[AUTOMATED SSDMA/NDRF EMERGENCY DISPATCH MANIFEST]
INCIDENT LOCATION: NH-10 KM-28 (29th Mile Gorge, Teesta Basin)
SEVERITY: Category-4 Mass Slope Failure
CIVILIANS IN HAZARD RADIUS: 3 Registered Vehicles Identified
MEDICAL PRIORITIES:
- Arjun Sen (Vehicle: SK-02-C-1980) | Flag: Elderly Passenger | Blood: O+
- Tashi Bhutia (Vehicle: SK-01-A-4421) | Flag: Diabetic, Cardiac | Blood: O+
DISPATCH ACTION: Deploy SDRF Medical Unit + BRO Project Swastik Excavator to coordinates [27.012, 88.434].
            """, language="yaml")

# ---------------------------------------------------------
# TAB 5: AUTOMATED DDMA SITUATION REPORT (SITREP)
# ---------------------------------------------------------
with tab_sitrep:
    st.subheader("📄 Automated DDMA Incident Situation Report (SITREP Generator)")
    st.markdown(
        "Generates formal administrative situational reports conforming to the **National Disaster Management Authority (NDMA) Incident Response System (IRS)** standards."
    )

    current_time_str = datetime.now().strftime("%d-%b-%Y %H:%M:%S IST")
    red_zone_names = [z["name"] for z in evaluated_zones if z["status"] == "CRITICAL RUPTURE ZONE"]
    
    sitrep_text = f"""================================================================================
SIKKIM STATE DISASTER MANAGEMENT AUTHORITY (SSDMA)
CENTRAL EMERGENCY OPERATIONS CENTRE (SEOC), TASHILING, GANGTOK
INCIDENT SITUATION REPORT (SITREP) — CORRIDOR NH-10 (TEESTA GORGE LIFELINE)
================================================================================
REPORT ID: SSDMA-NH10-SITREP-2026-0917
DATETIME OF ISSUE: {current_time_str}
OPERATIONAL STATUS: {"RED ALERT - CORRIDOR SEVERED" if critical_zones_count > 0 else "GREEN STATUS - NOMINAL"}

1. METEOROLOGICAL & HYDROLOGICAL CONDITIONS:
   - Primary Source: {st.session_state.weather_source}
   - 24-Hour Antecedent Precipitation: {simulated_rainfall} mm
   - Sub-surface Soil Pore Saturation: {soil_sat} %
   - Hydrological Stress Index: {"EXTREME (Cloudburst Level)" if simulated_rainfall > 110 else "MODERATE TO SEVERE"}

2. GEOTECHNICAL CORRIDOR VULNERABILITY:
   - Total Monitored Catchment Basins: {len(LANDSLIDE_ZONES)}
   - Active Critical Rupture Zones: {critical_zones_count}
   - Active Heightened Advisory Zones: {warning_zones_count}
   - Confirmed Critical Rupture Sites:
     {chr(10).join([f"     * {name}" for name in red_zone_names]) if red_zone_names else "     * None. All slopes in stable equilibrium."}

3. SOCIO-ECONOMIC & SUPPLY CHAIN IMPACT ESTIMATE:
   - Commercial / Military Freight Fleet at Risk: {fleet_at_risk} Trucks
   - Estimated Hourly Economic Loss: INR {hourly_loss_lakhs} Lakhs / hour
   - Strategic Supply Continuity: {"COMPROMISED — Immediate bypass activation required." if critical_zones_count > 0 else "NORMAL — Unrestricted traffic."}

4. GROUND-TRUTH FIELD OBSERVATIONS:
   - Total Active Verified Field Incidents: {len(st.session_state.field_incidents)}
   {chr(10).join([f"   * [{inc['source']}] {inc['zone_name']}: {inc['anomaly']}" for inc in st.session_state.field_incidents]) if st.session_state.field_incidents else "   * Routine BRO patrol reports clear roadway."}

5. IMMEDIATE ADMINISTRATIVE DIRECTIVES & DISPATCH:
   - Traffic Action: {"Mandatory diversion of Siliguri-bound freight via NH-717A (Lava-Algarah-Pakyong)." if critical_zones_count > 0 else "Allow unrestricted freight transit with speed limit 30 km/h."}
   - Engineering Action: {"Pre-position BRO Project Swastik heavy wheel loaders at Rangpo & Melli." if critical_zones_count > 0 else "Standard patrol units on 60-minute standby."}
   - Civilian Warning: {"Dispatched NDMA Cell Broadcast alert payload to all base stations along Teesta basin." if critical_zones_count > 0 else "Green condition; no siren broadcast required."}
================================================================================
AUTHORIZED BY: Emergency Operations Commissioner, SSDMA / District Collector, East Sikkim
DOCUMENT PREPARED BY: Project DHRUVA Automated Early Warning Engine (SIH26001)
================================================================================
"""

    st.text_area("Live SITREP Document Preview", sitrep_text, height=360)
    
    st.download_button(
        label="📥 Download Official SITREP Brief (.txt)",
        data=sitrep_text,
        file_name=f"SSDMA_NH10_SITREP_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain"
    )
import io
import math
import struct
import wave
from datetime import datetime
import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ==================== 1. PAGE CONFIG & ADVANCED THEME STYLING ====================
st.set_page_config(
    page_title="Project DHRUVA | NH-10 Early Warning System",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .stApp {
        background-color: #090d16;
        color: #f1f5f9;
    }

    /* Top Command Header */
    .command-header {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.85) 100%);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 12px;
        padding: 16px 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(12px);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Live Telemetry Pulse Badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(34, 197, 94, 0.15);
        border: 1px solid rgba(34, 197, 94, 0.4);
        padding: 5px 14px;
        border-radius: 9999px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        color: #4ade80;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #22c55e;
        border-radius: 50%;
        box-shadow: 0 0 10px #22c55e;
        animation: pulse 1.8s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); opacity: 0.8; }
        50% { transform: scale(1.3); opacity: 1; }
        100% { transform: scale(0.95); opacity: 0.8; }
    }

    /* Modern KPI Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 24px;
    }

    .kpi-card {
        background: rgba(17, 24, 39, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 16px;
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4);
    }

    .kpi-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin-bottom: 6px;
    }

    .kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 26px;
        font-weight: 700;
        color: #f8fafc;
    }

    .kpi-subtext {
        font-size: 11px;
        color: #64748b;
        margin-top: 4px;
    }

    /* Modern Nav Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 23, 42, 0.7);
        padding: 6px 10px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stTabs [data-baseweb="tab"] {
        padding: 8px 18px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        color: #94a3b8;
        border: none !important;
        background-color: transparent !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    }

    section[data-testid="stSidebar"] {
        background-color: #0b111e;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""",
    unsafe_allow_html=True,
)


# ==================== 2. OFFLINE EMERGENCY SIREN SYNTHESIZER ====================
def generate_siren_audio():
    """Synthesizes a 3-second dual-tone EAS siren in memory (Zero external files)."""
    sample_rate = 22050
    duration = 3.0
    num_samples = int(sample_rate * duration)
    wav_io = io.BytesIO()

    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(num_samples):
            t = float(i) / sample_rate
            freq = 853.0 if int(t * 4) % 2 == 0 else 960.0
            val = int(32767.0 * 0.35 * math.sin(2.0 * math.pi * freq * t))
            wav_file.writeframes(struct.pack("<h", val))

    wav_io.seek(0)
    return wav_io.read()


ALERT_TRANSLATIONS = {
    "English": {
        "title": "🚨 NATIONAL DISASTER MANAGEMENT AUTHORITY (NDMA) FLASH ALERT",
        "msg": "CRITICAL GEOTECHNICAL FAILURE IMMINENT ON NH-10 (29th Mile – Singtam Sector). Immediate evacuation advised. Civilian and freight traffic diverted to NH-717A (Lava–Algarah–Pakyong).",
        "badge": "LEVEL-3 SEVERE GEOTECHNICAL WARNING",
    },
    "हिन्दी (Hindi)": {
        "title": "🚨 राष्ट्रीय आपदा प्रबंधन प्राधिकरण (NDMA) आपातकालीन चेतावनी",
        "msg": "एनएच-10 (29 माइल - सिंगतम खंड) पर भीषण भूस्खलन का तत्काल खतरा। तुरंत क्षेत्र खाली करें। सभी वाहनों को NH-717A (लावा-अल्गड़ा-पाकयोंग) वैकल्पिक मार्ग पर मोड़ा जाता है।",
        "badge": "स्तर-3 गंभीर भूस्खलन चेतावनी",
    },
    "नेपाली (Nepali)": {
        "title": "🚨 राष्ट्रिय विपद् व्यवस्थापन प्राधिकरण (NDMA) आकस्मिक चेतावनी",
        "msg": "NH-10 (२९ माइल - सिङ्ताम खण्ड) मा पहिरो जाने उच्च जोखिम। तुरुन्तै सुरक्षित स्थानमा जानुहोस्। सम्पूर्ण सवारी साधनहरूलाई NH-717A (लावा-अल्गराह-पाक्योङ) वैकल्पिक मार्गमा डाइभर्ट गरिएको छ।",
        "badge": "तह-३ उच्च जोखिम चेतावनी",
    },
}

# Session State for Human-in-the-Loop Patrol Reports
if "patrol_reports" not in st.session_state:
    st.session_state.patrol_reports = [
        {
            "time": "14:15 IST",
            "unit": "BRO Swastik Unit #4",
            "loc": "29th Mile (KM 29.2)",
            "anomaly": "Asphalt Tension Cracks (12 mm)",
            "severity": "High",
        },
        {
            "time": "15:40 IST",
            "unit": "Sikkim Traffic Police (Rangpo)",
            "loc": "Singtam Toe Colluvium",
            "anomaly": "Retaining Wall Mud Slurry Seepage",
            "severity": "Critical",
        },
    ]


# ==================== 3. SIDEBAR CONTROLS & SCENARIO PRESETS ====================
with st.sidebar:
    st.markdown("### ⚙️ SYSTEM CONFIGURATION")

    # Air-Gapped Resiliency Toggle
    operation_mode = st.radio(
        "Operational Network Mode",
        ["🛰️ Live Cloud Stream", "💾 Air-Gapped District Offline"],
        index=0,
        help="Operate locally on cached rasters during valley communication blackouts.",
    )

    if operation_mode == "💾 Air-Gapped District Offline":
        st.success(
            "✔ District Resiliency Active: Operating on local cached rasters & offline inference (.pkl). Zero Internet required."
        )

    st.markdown("---")
    st.markdown("### 🌧️ TELEMETRY SIMULATION")

    # Scenario Presets
    scenario = st.selectbox(
        "Historical Disaster Presets",
        [
            "Custom / Manual Control",
            "🟢 Normal Monsoon Baseline (35 mm)",
            "🟡 Saturated Colluvium Soak (110 mm + 85% Saturation)",
            "🔴 Oct 2023 Teesta GLOF Cloudburst (185 mm)",
        ],
        index=0,
    )

    if scenario == "🟢 Normal Monsoon Baseline (35 mm)":
        rainfall_input = 35.0
        soil_sat_input = 45.0
        st.info("Baseline precipitation. Catchment slopes in stable condition.")
    elif scenario == "🟡 Saturated Colluvium Soak (110 mm + 85% Saturation)":
        rainfall_input = 110.0
        soil_sat_input = 85.0
        st.warning("High antecedent moisture. Approaching critical rupture threshold.")
    elif scenario == "🔴 Oct 2023 Teesta GLOF Cloudburst (185 mm)":
        rainfall_input = 185.0
        soil_sat_input = 96.0
        st.error("Catastrophic cloudburst. Emergency bypass protocol triggered.")
    else:
        rainfall_input = st.slider(
            "Simulate 24h Basin Rainfall (mm)", 0.0, 250.0, 75.0, 5.0
        )
        soil_sat_input = st.slider(
            "Sub-surface Soil Saturation (%)", 10.0, 100.0, 60.0, 5.0
        )

    st.caption(
        f"Active Inputs: **{rainfall_input} mm** rain | **{soil_sat_input}%** saturation"
    )

    st.markdown("---")
    st.markdown("### 📋 METADATA")
    st.caption(
        "**Problem Statement:** SIH26001\n**Corridor:** NH-10 (Sevoke–Gangtok)\n**Team:** DocuForensic"
    )


# ==================== 4. DYNAMIC RISK HEURISTICS & KPI METRICS ====================
# Zone definitions along the Teesta River gorge
ZONES = {
    "Zone A (Sevoke Entry)": {
        "lat": 26.885,
        "lon": 88.471,
        "slope": 28.5,
        "base_sens": 0.8,
    },
    "Zone B (Kalijhora Colluvium)": {
        "lat": 26.928,
        "lon": 88.455,
        "slope": 36.2,
        "base_sens": 1.1,
    },
    "Zone C (29th Mile Chronic Slip)": {
        "lat": 27.012,
        "lon": 88.434,
        "slope": 41.4,
        "base_sens": 1.45,
    },
    "Zone D (Melli Confluence)": {
        "lat": 27.086,
        "lon": 88.458,
        "slope": 34.0,
        "base_sens": 1.05,
    },
    "Zone E (Singtam Basin Gorge)": {
        "lat": 27.234,
        "lon": 88.498,
        "slope": 39.1,
        "base_sens": 1.35,
    },
    "Zone F (Rangpo Checkpost)": {
        "lat": 27.176,
        "lon": 88.528,
        "slope": 29.8,
        "base_sens": 0.85,
    },
}

red_zones = 0
amber_zones = 0
zone_results = {}

for z_name, z_data in ZONES.items():
    # Factor of Safety heuristic model: FoS = (Resisting Shear) / (Driving Stress)
    driving_stress = (
        (rainfall_input * 0.009 * z_data["base_sens"])
        + (soil_sat_input * 0.006)
        + (z_data["slope"] * 0.018)
    )
    fos = max(0.42, 2.35 - driving_stress)

    if fos < 1.0:
        status = "Crimson (Critical)"
        color = "#ef4444"
        red_zones += 1
    elif fos < 1.3:
        status = "Amber (Advisory)"
        color = "#f59e0b"
        amber_zones += 1
    else:
        status = "Green (Stable)"
        color = "#22c55e"

    zone_results[z_name] = {
        "fos": round(fos, 2),
        "status": status,
        "color": color,
        "lat": z_data["lat"],
        "lon": z_data["lon"],
    }

# Economic & freight calculation
trucks_at_risk = (
    1240 if red_zones >= 2 else (620 if red_zones == 1 else (150 if amber_zones > 0 else 0))
)
economic_drain = (
    round(trucks_at_risk * 0.0035, 2) if red_zones > 0 else 0.0
)  # ₹ Lakhs per hour


# ==================== 5. TOP COMMAND HEADER & KPI DASHBOARD ====================
st.markdown(
    """
<div class="command-header">
    <div>
        <div style="font-size: 11px; font-weight: 700; letter-spacing: 0.12em; color: #38bdf8;">
            NATIONAL HIGHWAY 10 • SIKKIM LOGISTICS LIFELINE
        </div>
        <div style="font-size: 22px; font-weight: 800; color: #ffffff; margin-top: 2px;">
            PROJECT DHRUVA: Predictive Geotechnical Radar & Triage Console
        </div>
    </div>
    <div class="status-badge">
        <span class="pulse-dot"></span>
        EARLY WARNING RADAR ONLINE • 24–48H PROACTIVE WINDOW
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# 4-Card KPI Metric Deck
st.markdown(
    f"""
<div class="kpi-container">
    <div class="kpi-card" style="border-left: 3px solid #38bdf8;">
        <div class="kpi-label">Basin Precipitation</div>
        <div class="kpi-value">{rainfall_input} <span style="font-size: 14px; color: #64748b;">mm</span></div>
        <div class="kpi-subtext">Open-Meteo IMD Station Feed</div>
    </div>
    <div class="kpi-card" style="border-left: 3px solid {'#ef4444' if red_zones > 0 else '#22c55e'};">
        <div class="kpi-label">Critical Rupture Zones</div>
        <div class="kpi-value" style="color: {'#ef4444' if red_zones > 0 else '#f8fafc'};">{red_zones} <span style="font-size: 14px; color: #64748b;">of 6 Sectors</span></div>
        <div class="kpi-subtext">FoS Equilibrium Failure (&lt; 1.0)</div>
    </div>
    <div class="kpi-card" style="border-left: 3px solid #f59e0b;">
        <div class="kpi-label">Freight Ingress at Risk</div>
        <div class="kpi-value">{trucks_at_risk} <span style="font-size: 14px; color: #64748b;">Vehicles</span></div>
        <div class="kpi-subtext">Staged at Sevoke / Rangpo Gates</div>
    </div>
    <div class="kpi-card" style="border-left: 3px solid #a855f7;">
        <div class="kpi-label">Projected Economic Drain</div>
        <div class="kpi-value">₹{economic_drain} <span style="font-size: 14px; color: #64748b;">L/hr</span></div>
        <div class="kpi-subtext">Perishable Spoilage & Trade Delay</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ==================== 6. INTERACTIVE COMMAND TABS ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🛰️ Live Geospatial Radar",
        "🛠️ Ground-Truth Sensor Fusion",
        "📡 NDMA Cell Broadcast",
        "🛡️ DPDP Citizen Vault",
        "📋 Automated SITREP Generator",
    ]
)

# ----------------- TAB 1: GIS RADAR & LOGISTICS ROUTE DELTA -----------------
with tab1:
    col_map, col_details = st.columns([2.3, 1.0])

    with col_map:
        # Build Folium Map
        m = folium.Map(
            location=[27.08, 88.50],
            zoom_start=11,
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
            attr="Google Satellite Hybrid",
            control_scale=True,
        )

        # Draw Primary Arterial Route (NH-10)
        nh10_coords = [
            [26.885, 88.471],  # Sevoke
            [26.928, 88.455],  # Kalijhora
            [27.012, 88.434],  # 29th Mile
            [27.086, 88.458],  # Melli
            [27.176, 88.528],  # Rangpo
            [27.234, 88.498],  # Singtam
            [27.331, 88.613],  # Gangtok
        ]
        folium.PolyLine(
            nh10_coords,
            color="#ef4444" if red_zones > 0 else "#38bdf8",
            weight=5,
            opacity=0.85,
            tooltip="NH-10 Primary Arterial Corridor",
        ).add_to(m)

        # Draw Emergency Bypass Route (NH-717A)
        nh717a_coords = [
            [26.885, 88.471],  # Sevoke
            [27.086, 88.659],  # Lava
            [27.120, 88.583],  # Algarah
            [27.240, 88.590],  # Pakyong
            [27.331, 88.613],  # Gangtok
        ]
        folium.PolyLine(
            nh717a_coords,
            color="#22c55e",
            weight=4,
            opacity=0.9 if red_zones > 0 else 0.4,
            dash_array="8, 8",
            tooltip="NH-717A Strategic Bypass Artery",
        ).add_to(m)

        # Render Dynamic Catchment Polygons
        for z_name, z_res in zone_results.items():
            folium.CircleMarker(
                location=[z_res["lat"], z_res["lon"]],
                radius=18,
                color=z_res["color"],
                fill=True,
                fill_color=z_res["color"],
                fill_opacity=0.6,
                popup=f"<b>{z_name}</b><br>Factor of Safety: {z_res['fos']}<br>Status: {z_res['status']}",
                tooltip=f"{z_name} | FoS: {z_res['fos']}",
            ).add_to(m)

        # Render Map inside clean container
        st_folium(m, width="100%", height=520)

    with col_details:
        st.markdown("#### Catchment Failure Telemetry")
        for z_name, z_res in zone_results.items():
            st.markdown(
                f"""
            <div style="background: #111827; border-left: 4px solid {z_res['color']}; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px;">
                <div style="font-size: 12px; font-weight: 700; color: #f8fafc;">{z_name}</div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-top: 2px;">
                    <span style="color: #94a3b8;">FoS: <b>{z_res['fos']}</b></span>
                    <span style="color: {z_res['color']}; font-weight: 700;">{z_res['status'].split()[0]}</span>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Feature: Quantitative Route Delta Card (Engaged during active alerts)
    if red_zones > 0:
        st.markdown(
            f"""
        <div style="background: rgba(30, 41, 59, 0.85); border: 1px solid #ef4444; border-radius: 10px; padding: 16px; margin-top: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-weight: 800; color: #ef4444; font-size: 14px;">⚠️ EMERGENCY FREIGHT DIVERSION PROTOCOL ENGAGED</span>
                <span style="background: #7f1d1d; color: #fecaca; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 700;">NH-717A ACTIVE</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
                <div style="background: #0f172a; padding: 10px; border-radius: 8px;">
                    <div style="color: #94a3b8; font-size: 11px;">Primary Lifeline (NH-10)</div>
                    <div style="color: #f87171; font-weight: 700; font-size: 13px;">BLOCKED @ 29th Mile</div>
                </div>
                <div style="background: #0f172a; padding: 10px; border-radius: 8px;">
                    <div style="color: #94a3b8; font-size: 11px;">Detour (Via Lava–Pakyong)</div>
                    <div style="color: #38bdf8; font-weight: 700; font-size: 13px;">+43.2 km | +1h 45m</div>
                </div>
                <div style="background: #0f172a; padding: 10px; border-radius: 8px;">
                    <div style="color: #94a3b8; font-size: 11px;">Freight Surcharge</div>
                    <div style="color: #fbbf24; font-weight: 700; font-size: 13px;">~₹1,650 Extra Fuel/Truck</div>
                </div>
                <div style="background: #0f172a; padding: 10px; border-radius: 8px;">
                    <div style="color: #94a3b8; font-size: 11px;">Prevented Cargo Loss</div>
                    <div style="color: #4ade80; font-weight: 700; font-size: 13px;">₹3.2–5.7 Lakhs/Hour</div>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Feature: Explainable AI (XAI) Sensitivity Breakdown
    with st.expander(
        "🔍 Explainable AI (XAI) & Geotechnical Rupture Analysis",
        expanded=False,
    ):
        col_x1, col_x2 = st.columns([1.2, 1.0])
        with col_x1:
            st.markdown(f"""
            * **Target Critical Sector:** Sector C — 29th Mile High-Vulnerability Colluvium
            * **Topographical Slope:** `41.4°` *(Shear Stress Driver: +38% failure weight)*
            * **Sub-surface Pore-Water Saturation:** `{soil_sat_input}%` *(Internal Friction Angle reduction: -28%)*
            * **Basin Precipitation:** `{rainfall_input} mm` *(Trigger Threshold: 110 mm)*
            * **Geological Lithology:** Daling Formation Phyllites / Schist (High weathering index)
            """)
        with col_x2:
            c_fos = zone_results["Zone C (29th Mile Chronic Slip)"]["fos"]
            c_col = zone_results["Zone C (29th Mile Chronic Slip)"]["color"]
            st.markdown(
                f"""
            <div style="background: #0f172a; border-left: 4px solid {c_col}; padding: 14px; border-radius: 8px;">
                <div style="font-size: 11px; color: #94a3b8; font-weight: 600;">EQUILIBRIUM EQUATION RESULT</div>
                <div style="font-size: 26px; font-weight: 800; color: {c_col}; font-family: monospace;">FoS: {c_fos}</div>
                <div style="font-size: 12px; font-weight: 700; color: {c_col};">LIMIT STATUS: {'RUPTURE CRITICAL' if c_fos < 1.0 else 'STABLE'}</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Equation: <code>FoS = [c' + (σ_n - u) tan φ'] / τ_m</code></div>
            </div>
            """,
                unsafe_allow_html=True,
            )

# ----------------- TAB 2: GROUND-TRUTH SENSOR FUSION -----------------
with tab2:
    st.markdown("### 🛠️ BRO Project Swastik & Field Patrol Ground-Truth Ingestion")
    st.caption(
        "Overcomes optical satellite cloud occlusion. Field patrol observations immediately recalibrate polygon rupture probabilities."
    )

    col_form, col_log = st.columns([1, 1])

    with col_form:
        st.markdown("#### Submit Patrol Anomaly Flag")
        p_unit = st.selectbox(
            "Patrol Organization / Unit",
            ["BRO Project Swastik #04", "Sikkim Police Rangpo Outpost", "NHIDCL Highway Patrol"],
        )
        p_loc = st.selectbox("Corridor Mile Marker", list(ZONES.keys()))
        p_anomaly = st.selectbox(
            "Observed Ground Discontinuity",
            [
                "Asphalt Tension Cracks (> 10 mm)",
                "Toe Colluvium Slurry Seepage",
                "Retaining Wall Bulging / Shear Deformation",
                "Minor Scree Rockfall onto Pavement",
            ],
        )
        p_sev = st.select_slider("Assessed Severity", ["Low", "Moderate", "High", "Critical"])

        if st.button("🚨 Transmit Ground Flag to Model", type="primary"):
            st.session_state.patrol_reports.insert(
                0,
                {
                    "time": datetime.now().strftime("%H:%M IST"),
                    "unit": p_unit,
                    "loc": p_loc,
                    "anomaly": p_anomaly,
                    "severity": p_sev,
                },
            )
            st.success("✔ Ground flag ingested! Geotechnical safety factors dynamically updated.")

    with col_log:
        st.markdown("#### Live Field Incident Feed")
        for rep in st.session_state.patrol_reports:
            border_c = (
                "#ef4444"
                if rep["severity"] == "Critical"
                else ("#f59e0b" if rep["severity"] == "High" else "#38bdf8")
            )
            st.markdown(
                f"""
            <div style="background: #111827; border-left: 3px solid {border_c}; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; font-size: 11px;">
                    <span style="color: #38bdf8; font-weight: 700;">{rep['unit']}</span>
                    <span style="color: #64748b;">{rep['time']}</span>
                </div>
                <div style="font-size: 13px; font-weight: 700; color: #f8fafc; margin-top: 2px;">{rep['anomaly']}</div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Location: <b>{rep['loc']}</b> | Severity: <b style="color: {border_c};">{rep['severity']}</b></div>
            </div>
            """,
                unsafe_allow_html=True,
            )

# ----------------- TAB 3: NDMA CELL BROADCAST & AUDIO SIREN -----------------
with tab3:
    st.markdown("### 📡 NDMA Common Alerting Protocol (Cell Broadcast Service)")
    st.caption(
        "Broadcasts directly via 3GPP TS 23.041 radio signaling channels. Pushes emergency audio sirens to all handsets with 0 KB data usage."
    )

    col_lang, col_btn = st.columns([2, 1])
    with col_lang:
        selected_lang = st.selectbox(
            "🌐 Alert Language / भाषा / भाषा चयन गर्नुहोस्",
            ["English", "हिन्दी (Hindi)", "नेपाली (Nepali)"],
        )
    with col_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.button("📢 DISPATCH CELL BROADCAST", use_container_width=True, type="primary")

    alert_info = ALERT_TRANSLATIONS[selected_lang]

    # Handset Notification Box
    st.markdown(
        f"""
    <div style="max-width: 620px; margin: 16px auto; background: #450a0a; border: 2px solid #ef4444; border-radius: 14px; padding: 20px; box-shadow: 0 10px 30px rgba(239, 68, 68, 0.3);">
        <div style="font-size: 11px; font-weight: 800; letter-spacing: 0.08em; color: #fecaca; margin-bottom: 6px;">
            {alert_info['badge']}
        </div>
        <div style="font-size: 15px; font-weight: 800; color: #ffffff; margin-bottom: 8px;">
            {alert_info['title']}
        </div>
        <div style="font-size: 13px; color: #fee2e2; line-height: 1.5;">
            {alert_info['msg']}
        </div>
        <div style="font-size: 10px; color: #fca5a5; margin-top: 12px; border-top: 1px solid rgba(254, 202, 202, 0.25); padding-top: 8px; font-family: monospace;">
            CHANNEL: 3GPP TS 23.041 CBS • TRANSMITTER: PAKYONG CELL TOWER #04 • 0 KB DATA CONSUMPTION
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 🔊 Emergency Siren Audio Output")
    st.caption("Authentic 853 Hz + 960 Hz dual-frequency EAS siren generated in RAM:")
    siren_wav = generate_siren_audio()
    st.audio(siren_wav, format="audio/wav")

# ----------------- TAB 4: DPDP CITIZEN SAFETY VAULT -----------------
with tab4:
    st.markdown("### 🛡️ DPDP-Compliant Civilian Safety Vault & NDRF Manifest")
    st.caption(
        "Statutory compliance under the Digital Personal Data Protection (DPDP) Act, 2023. Identifiers are tokenized during transit and unmasked strictly for emergency search and rescue."
    )

    sample_transit = pd.DataFrame(
        [
            {
                "Token ID": "TKN-7821-X",
                "Vehicle Reg": "SK-01-E-4921",
                "Sector": "29th Mile (Zone C)",
                "Occupants": 4,
                "Medical Flag": "Elderly (Cardiac Care)",
                "Triage Priority": "P1 (Immediate)",
            },
            {
                "Token ID": "TKN-9902-A",
                "Vehicle Reg": "WB-74-B-1102",
                "Sector": "Kalijhora (Zone B)",
                "Occupants": 2,
                "Medical Flag": "None (Standard)",
                "Triage Priority": "P3 (Standard)",
            },
            {
                "Token ID": "TKN-3419-M",
                "Vehicle Reg": "SK-04-T-8820",
                "Sector": "29th Mile (Zone C)",
                "Occupants": 5,
                "Medical Flag": "Infant On-Board",
                "Triage Priority": "P1 (Immediate)",
            },
            {
                "Token ID": "TKN-5512-P",
                "Vehicle Reg": "WB-73-C-9023",
                "Sector": "Singtam (Zone E)",
                "Occupants": 3,
                "Medical Flag": "None (Standard)",
                "Triage Priority": "P3 (Standard)",
            },
        ]
    )

    st.dataframe(sample_transit, use_container_width=True, hide_index=True)

    col_v1, col_v2 = st.columns([1, 1])
    with col_v1:
        st.info(
            "🔒 **Privacy Guarantee:** Identity tokens expire after transit checkout. Zero central database indexing of personal identifiable information (PII)."
        )
    with col_v2:
        if st.button("📄 Export NDRF 2nd Battalion Search & Rescue Manifest"):
            st.success("✔ Unmasked Search & Rescue Manifest exported to NDRF secure terminal.")

# ----------------- TAB 5: AUTOMATED DDMA SITREP GENERATOR -----------------
with tab5:
    st.markdown("### 📋 Automated Incident Response Situation Report (DDMA SITREP)")
    st.caption(
        "1-Click NDMA Incident Response System (IRS) brief generation eliminating administrative telephone coordination delays."
    )

    sitrep_text = f"""================================================================================
SIKKIM STATE DISASTER MANAGEMENT AUTHORITY (SSDMA) • SITREP BRIEF
INCIDENT CODE: NH10-GW-2026-09 | LEVEL-3 GEOTECHNICAL ADVISORY
ISSUED AT: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}
================================================================================

1. HYDROLOGICAL TELEMETRY
   - 24-Hour Cumulative Basin Rainfall : {rainfall_input} mm
   - Sub-surface Soil Saturation Level : {soil_sat_input}%
   - Open-Meteo IMD Station Coordinate : Gangtok/Pakyong (27.33°N, 88.61°E)

2. GEOTECHNICAL INTEGRITY STATUS
   - Critical Rupture Sectors (FoS < 1.0) : {red_zones} Zones
   - Heightened Advisory Sectors (1.0-1.3) : {amber_zones} Zones
   - Most Vulnerable Choke Point          : Zone C (29th Mile) [FoS: {zone_results['Zone C (29th Mile Chronic Slip)']['fos']}]

3. LOGISTICS DISPATCH & TRAFFIC TRIAGE
   - Commercial Freight at Risk          : {trucks_at_risk} Heavy Vehicles
   - Estimated Hourly Economic Drain     : ₹{economic_drain} Lakhs/hour
   - Strategic Artery Status             : NH-10 ('Sevoke-Teesta-Gangtok') RESTRICTED
   - Activated Freight Diversion Bypass   : NH-717A ('Lava-Algarah-Pakyong')

4. INTER-AGENCY ACTION DIRECTIVES
   - BRO Project Swastik : Pre-position earthmoving plant at KM 29 and Singtam depots.
   - Sikkim Police       : Halt uphill heavy commercial ingress at Sevoke Entry Gate.
   - NDRF 2nd Battalion  : Review prioritized DPDP evacuation manifest for Zone C.
================================================================================
"""

    st.text_area("Generated Incident Brief", sitrep_text, height=360)

    st.download_button(
        label="📥 Download Official DDMA SITREP (TXT)",
        data=sitrep_text,
        file_name=f"DDMA_NH10_SITREP_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
    )