import streamlit as st
import requests
import pandas as pd
import numpy as np
import datetime

# --- APP CONFIGURATION ---
st.set_page_config(
    page_title="Advanced Solar Power & Weather Integration System",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INITIALIZE SESSION STATES ---
if "live_weather_data" not in st.session_state:
    st.session_state.live_weather_data = None
if "manual_weather_data" not in st.session_state:
    st.session_state.manual_weather_data = None

# --- CORE WEATHER API EXTRACTION FUNCTION ---
def fetch_open_meteo_forecast(latitude, longitude):
    """
    Direct implementation of the Open-Meteo API payload structure.
    Fetches temperature, wind speed, and cloud cover for a 3-day window.
    """
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,wind_speed_10m,cloud_cover",
        "timezone": "auto",
        "forecast_days": 3
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200:
            raw_data = response.json()
            hourly = raw_data.get("hourly", {})
            
            # Structuring into a strict Pandas DataFrame
            df = pd.DataFrame({
                "Timestamp": pd.to_datetime(hourly.get("time")),
                "Temperature": hourly.get("temperature_2m"),
                "Wind_Speed": hourly.get("wind_speed_10m"),
                "Cloud_Cover": hourly.get("cloud_cover")
            })
            # Parsing operational metrics out of timestamp
            df["Hour"] = df["Timestamp"].dt.hour
            df["Date"] = df["Timestamp"].dt.date
            return df
        else:
            st.error(f"API Error: Remote server returned status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network Connection Failed: {str(e)}")
        return None
      # --- SOLAR PHYSICS SIMULATION ENGINE ---
def compute_clear_sky_irradiance(hour):
    """
    Simulates theoretical clear-sky Global Horizontal Irradiance (GHI) in W/m²
    based on a standard diurnal solar elevation curve.
    """
    # Peak solar radiation occurs at solar noon (12:00)
    if 6 <= hour <= 18:
        # Sine wave modeling for daily sun movement
        amplitude = 1000.0  # Max peak irradiance under perfect conditions
        angle = np.pi * (hour - 6) / 12
        return amplitude * np.sin(angle)
    return 0.0

def calculate_advanced_solar_yield(temperature, wind_speed, cloud_cover, hour, config):
    """
    Executes a multi-variable engineering calculation to determine clean solar output.
    Takes into account thermal coefficients, cell heating, and atmospheric blocking.
    """
    # 1. Base Solar Irradiance Estimation
    ghi_clear = compute_clear_sky_irradiance(hour)
    if ghi_clear == 0:
        return {
            "Power_Output_kW": 0.0,
            "Cell_Temperature": temperature,
            "Effective_Irradiance": 0.0
        }
    
    # Atmospheric degradation via cloud cover percentage
    # Cloud attenuation is modeled using a non-linear scaling factor
    cloud_loss_factor = (cloud_cover / 100.0) * 0.78
    effective_irradiance = ghi_clear * (1.0 - cloud_loss_factor)
    
    # 2. Photovoltaic Cell Temperature Modeling (NOCT Formula)
    # Panels heat up from the sun, but wind speed helps cool them down
    noct = 45.0  # Nominal Operating Cell Temperature
    ambient_temp = temperature
    
    # Wind cooling adjustment factor
    wind_cooling_effect = 1.0 + (wind_speed * 0.05)
    cell_temp = ambient_temp + ((noct - 20.0) * (effective_irradiance / 800.0) / wind_cooling_effect)
    
    # 3. Efficiency Degradation Calculation
    # Standard Testing Conditions (STC) assume 25°C cell temperature
    stc_temp = 25.0
    temp_coefficient = config["temp_coef"]  # Typically -0.4% per degree C
    
    thermal_derating = 1.0
    if cell_temp > stc_temp:
        thermal_derating = 1.0 - ((cell_temp - stc_temp) * abs(temp_coefficient))
        
    # 4. Total System Capacity Integration
    total_capacity_kw = (config["panel_watt"] * config["panel_count"]) / 1000.0
    inverter_efficiency = config["inverter_eff"] / 100.0
    soiling_loss = (1.0 - (config["soiling_loss"] / 100.0))
    
    # Final Power Calculation Equation
    irradiance_ratio = effective_irradiance / 1000.0
    power_output = total_capacity_kw * irradiance_ratio * thermal_derating * inverter_efficiency * soiling_loss
    
    return {
        "Power_Output_kW": max(0.0, round(power_output, 3)),
        "Cell_Temperature": round(cell_temp, 2),
        "Effective_Irradiance": round(effective_irradiance, 2)
    }
  # --- MAIN APPLICATION UI & DATA PIPELINE ---

# Layout Design
st.header("⚡ Industrial Solar Power Yield & Meteorological Integrator")
st.write("Professional simulation software syncing real-time remote sensory API data with engineering calculation arrays.")

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.markdown("### 🛠️ Array Technical Configuration")
panel_watt = st.sidebar.number_input("Nominal Panel Rating (Watts)", min_value=100, max_value=700, value=400, step=5)
panel_count = st.sidebar.number_input("Total Panels in Field", min_value=1, max_value=5000, value=25, step=5)

st.sidebar.markdown("### 📉 System Losses & Coefficients")
temp_coef = st.sidebar.slider("Temperature Coefficient (Pmax / °C)", min_value=-0.006, max_value=-0.002, value=-0.004, step=0.0005, format="%.4f")
inverter_eff = st.sidebar.slider("Inverter Efficiency (%)", min_value=80.0, max_value=100.0, value=96.5, step=0.5)
soiling_loss = st.sidebar.slider("Dust/Soiling Derating Loss (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.5)

# Packing configurations into a safe context dictionary
system_config = {
    "panel_watt": panel_watt,
    "panel_count": panel_count,
    "temp_coef": temp_coef,
    "inverter_eff": inverter_eff,
    "soiling_loss": soiling_loss
}

st.sidebar.markdown("---")
st.sidebar.write("⚙️ *System calculated capacity:*", f"**{(panel_watt * panel_count)/1000:.2f} kWp**")

# --- CORE LOGIC PIPELINE SWITCH ---
st.markdown("### 🌐 Data Ingestion Channel Selector")
live_mode_active = st.toggle("Activate Live Location Telemetry Mode", value=True, 
                             help="Switch between automated live weather coordinates and static environmental input tables.")

if live_mode_active:
    st.subheader("📍 Real-Time Spatial Coordinates")
    geo_col1, geo_col2, geo_col3 = st.columns([2, 2, 1])
    
    with geo_col1:
        lat_input = st.text_input("Target Latitude (decimal degrees)", value="33.6844")
    with geo_col2:
        lon_input = st.text_input("Target Longitude (decimal degrees)", value="73.0479")
    with geo_col3:
        st.write("<br>", unsafe_allow_html=True)
        refresh_data = st.button("Sync API Telemetry", use_container_width=True)

    # Triggering pipeline execution on selection change or manual sync requests
    if st.session_state.live_weather_data is None or refresh_data:
        with st.spinner("Accessing Open-Meteo REST Servers..."):
            st.session_state.live_weather_data = fetch_open_meteo_forecast(lat_input, lon_input)

    working_df = st.session_state.live_weather_data

    if working_df is not None:
        # Map calculation arrays over every row of live meteorological data
        calculated_outputs = []
        for _, row in working_df.iterrows():
            metrics = calculate_advanced_solar_yield(
                temperature=row["Temperature"],
                wind_speed=row["Wind_Speed"],
                cloud_cover=row["Cloud_Cover"],
                hour=row["Hour"],
                config=system_config
            )
            calculated_outputs.append(metrics)
            
        # Unpacking and saving computational outputs back into the master dataframe
        calculated_df = pd.DataFrame(calculated_outputs)
        working_df["Effective_Irradiance (W/m²)"] = calculated_df["Effective_Irradiance"]
        working_df["Cell_Temperature (°C)"] = calculated_df["Cell_Temperature"]
        working_df["Generated_Power (kW)"] = calculated_df["Power_Output_kW"]

        # Presenting High-Level Analytical Dashboard Cards
        st.markdown("#### 📊 Current Hourly Live System Readings")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Ambient Temperature", f"{working_df['Temperature'].iloc[0]} °C")
        m_col2.metric("Cloud Obstruction Index", f"{working_df['Cloud_Cover'].iloc[0]} %")
        m_col3.metric("Calculated PV Cell Temp", f"{working_df['Cell_Temperature (°C)'].iloc[0]} °C")
        m_col4.metric("Live Net Power Output", f"{working_df['Generated_Power (kW)'].iloc[0]} kW")

        # Complex Multiline Time Series Charting
        st.markdown("#### 📈 3-Day Forecast Analysis Visualization")
        chart_view = working_df.set_index("Timestamp")
        st.line_chart(chart_view[["Temperature", "Cloud_Cover", "Generated_Power (kW)"]])

        with st.expander("🔬 View Processed Computational Matrix Data"):
            st.dataframe(working_df, use_container_width=True)
else:
    st.subheader("📝 Manual Static Environmental Input Mode")
    st.info("System isolated from API. Please construct your explicit localized test atmosphere values:")
    
    in_col1, in_col2, in_col3, in_col4 = st.columns(4)
    with in_col1:
        m_temp = st.slider("Test Air Temperature (°C)", -15.0, 55.0, 30.0, 0.5)
    with in_col2:
        m_wind = st.slider("Test Wind Velocity (km/h)", 0.0, 120.0, 12.0, 0.5)
    with in_col3:
        m_cloud = st.slider("Static Cloud Blockage (%)", 0, 100, 40, 5)
    with in_col4:
        m_hour = st.slider("Simulated Hour of Day", 0, 23, 12, 1)

    # Executing the exact same mathematical engine using custom static values
    static_results = calculate_advanced_solar_yield(
        temperature=m_temp,
        wind_speed=m_wind,
        cloud_cover=m_cloud,
        hour=m_hour,
        config=system_config
    )

    st.markdown("---")
    st.subheader("🎯 Controlled Environment Output Performance Summary")
    
    out_col1, out_col2, out_col3 = st.columns(3)
    with out_col1:
        st.metric("Modeled Solar Field Output", f"{static_results['Power_Output_kW']} kW", 
                  delta=f"{round(static_results['Power_Output_kW'] * 1000)} Watts Generation")
    with out_col2:
        st.metric("Internal Cell Thermal State", f"{static_results['Cell_Temperature']} °C")
    with out_col3:
        st.metric("Calculated Incident Radiation", f"{static_results['Effective_Irradiance']} W/m²")

    # Creating full 24-hour simulation sweep profile based on manual settings
    st.markdown("#### 🕒 Full 24-Hour Simulated Yield Under Given Conditions")
    day_hours = list(range(24))
    hourly_sim_power = []
    
    for h in day_hours:
        res = calculate_advanced_solar_yield(m_temp, m_wind, m_cloud, h, system_config)
        hourly_sim_power.append(res["Power_Output_kW"])
        
    simulation_profile_df = pd.DataFrame({
        "Simulated Hour": [f"{h:02d}:00" for h in day_hours],
        "Output Yield Profile (kW)": hourly_sim_power
    }).set_index("Simulated Hour")
    
    st.bar_chart(simulation_profile_df)
