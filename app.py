import streamlit as st
 
st.set_page_config(page_title="Solar Power Estimator Pro", layout="wide", page_icon="⚡")
 
# --- TERMS & AGREEMENT POPUP ---
def show_terms():
    @st.dialog("📄 Terms & Privacy Agreement")
    def terms_dialog():
        st.markdown("""
        ### ⚠️ IMPORTANT DISCLAIMER
        
        By using this Solar Power Estimator Pro app, you agree that:
        
        1. **No Liability**: The calculations and estimates provided are for educational and planning purposes only. We are NOT responsible for any financial loss, installation errors, or damage caused by using this data.
        
        2. **Data Usage**: Your location/country selection may be used for weather API calls. We do NOT store or share your personal data.
        
        3. **Accuracy**: Solar generation depends on real weather, panel quality, installation. Results may vary ±20%.
        
        4. **Third Party APIs**: Open-Meteo and Nominatim services are used. If they are offline, app will use database values.
        
        5. **Professional Advice**: Always consult a certified solar engineer before actual installation.
        
        By clicking "I Agree", you accept all terms above.
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ I Disagree", use_container_width=True, type="secondary"):
                st.stop()
        with col2:
            if st.button("✅ I Agree", use_container_width=True, type="primary"):
                st.session_state['agreed'] = True
                st.rerun()
 
    if 'agreed' not in st.session_state:
        terms_dialog()
        st.stop()
 
show_terms()
 
# --- IMPORTS ---
import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go
from datetime import datetime
import datetime as dt
import requests
from io import BytesIO
 
# Safe optional imports
GEO_ENABLED = False
try:
    from geopy.geocoders import Nominatim
    GEO_ENABLED = True
except Exception:
    pass
 
PDF_ENABLED = False
FPDF = None
try:
    from fpdf import FPDF
    PDF_ENABLED = True
except Exception:
    pass
 
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_ENABLED = True
except Exception:
    FOLIUM_ENABLED = False
 
# --- THEME ---
st.markdown("""
    <style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
.stApp {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 75%, #f5576c 100%);
    background-attachment: fixed;
    color: #1a1a2e;
}
.main-header {
    color: white; font-size: 42px; font-weight: 900;
    text-shadow: 0 8px 32px rgba(0,0,0,0.3); margin-bottom: 30px; text-align: center;
    background: rgba(255,255,255,0.15); backdrop-filter: blur(20px);
    padding: 24px; border-radius: 24px; border: 1px solid rgba(255,255,255,0.3);
}
[data-testid="stMetricValue"] { color: #667eea!important; font-size: 28px; font-weight: 900; }
.stMetric {
    background: rgba(255,255,255,0.85); backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.5); border-radius: 20px; padding: 20px;
    box-shadow: 0 8px 32px rgba(31,38,135,0.15); transition: transform 0.3s;
}
.stMetric:hover { transform: translateY(-5px); }
.feature-box {
    background: rgba(255,255,255,0.9); backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.6); padding: 24px; border-radius: 20px;
    margin-bottom: 16px; box-shadow: 0 8px 32px rgba(31,38,135,0.12);
}
.info-label {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 8px 18px; border-radius: 12px; font-size: 1rem;
    font-weight: 700; box-shadow: 0 4px 15px rgba(102,126,234,0.4);
}
.wind-alert {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    padding: 1rem; border-radius: 12px; color: white; font-weight: 600; margin: 1rem 0;
}
.safe-alert {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    padding: 1rem; border-radius: 12px; color: white; font-weight: 600; margin: 1rem 0;
}
div[data-testid="stTabs"] button {
    background: rgba(255,255,255,0.7); color: #667eea; border-radius: 12px; font-weight: 600; margin: 4px;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;
}
@media (max-width: 768px) {
   .main-header { padding: 1rem; font-size: 0.9rem; }
   .stMetric { padding: 1rem; }
}
    </style>
""", unsafe_allow_html=True)
 
# ============================================================
# DATABASE SECTION
# ============================================================
 
# --- 120+ COUNTRIES DATABASE [Lat, Currency, Export, Import, ESG, Labor, Sourcing, GHI, Elec%, Voltage, Frequency, Wind_kmh, Wind_Zone] ---
db = {
    "Afghanistan": [33.9, "AFN", 5, 12, "B", "High", "Import", 5.2, 98, 220, 50, 45, "High"],
    "Albania": [41.1, "ALL", 10, 18, "B+", "Medium", "EU Import", 4.1, 100, 230, 50, 25, "Low"],
    "Algeria": [28.0, "DZD", 4, 12, "B", "Medium", "Local", 6.0, 99, 230, 50, 55, "Extreme"],
    "Andorra": [42.5, "EUR", 0.12, 0.28, "A+", "Very Low", "EU Certified", 4.3, 100, 230, 50, 30, "Moderate"],
    "Angola": [-11.2, "AOA", 15, 30, "C", "High", "Import", 5.5, 42, 220, 50, 35, "Moderate"],
    "Argentina": [-38.4, "ARS", 25, 65, "B+", "Medium", "Local", 5.1, 100, 220, 50, 70, "Extreme"],
    "Armenia": [40.2, "AMD", 12, 25, "B+", "Medium", "Import", 4.2, 100, 230, 50, 40, "High"],
    "Australia": [-25.2, "AUD", 0.10, 0.35, "A+", "Very Low", "AU Certified", 5.8, 100, 230, 50, 85, "Extreme"],
    "Austria": [47.5, "EUR", 0.15, 0.45, "A+", "Very Low", "EU Certified", 3.4, 100, 230, 50, 35, "Moderate"],
    "Azerbaijan": [40.1, "AZN", 0.05, 0.12, "B", "Medium", "Import", 4.8, 100, 220, 50, 50, "High"],
    "Bahrain": [26.0, "BHD", 0.02, 0.06, "A", "Low", "GCC", 5.9, 100, 230, 50, 60, "Extreme"],
    "Bangladesh": [23.6, "BDT", 7.5, 14.0, "B", "Medium", "Local Assembly", 4.6, 99, 220, 50, 90, "Extreme"],
    "Belgium": [50.5, "EUR", 0.12, 0.52, "A+", "Very Low", "EU Certified", 2.9, 100, 230, 50, 40, "High"],
    "Bhutan": [27.5, "BTN", 3, 8, "A", "Low", "Hydro+Solar", 4.5, 99, 230, 50, 30, "Moderate"],
    "Bolivia": [-16.2, "BOB", 0.4, 0.9, "B", "Medium", "Import", 5.8, 94, 220, 50, 25, "Low"],
    "Bosnia": [44.2, "BAM", 0.08, 0.16, "B+", "Medium", "EU Import", 3.6, 100, 230, 50, 45, "High"],
    "Botswana": [-22.3, "BWP", 1.2, 2.4, "B+", "Medium", "Local", 6.1, 72, 230, 50, 50, "High"],
    "Brazil": [-14.2, "BRL", 0.55, 1.15, "A-", "Low", "Local Mfg", 5.5, 99, 220, 60, 60, "Extreme"],
    "Bulgaria": [42.7, "BGN", 0.09, 0.18, "A-", "Low", "EU Certified", 3.8, 100, 230, 50, 40, "High"],
    "Burkina Faso": [12.4, "XOF", 85, 170, "C", "High", "Import", 5.8, 19, 220, 50, 55, "Extreme"],
    "Burundi": [-3.4, "BIF", 180, 350, "C", "High", "Import", 5.2, 11, 220, 50, 20, "Low"],
    "Cambodia": [12.6, "KHR", 600, 1200, "B", "Medium", "Import", 5.0, 89, 230, 50, 70, "Extreme"],
    "Cameroon": [6.3, "XAF", 75, 150, "C", "High", "Import", 5.0, 64, 220, 50, 35, "Moderate"],
    "Canada": [56.1, "CAD", 0.08, 0.24, "A+", "Very Low", "US/CA Certified", 3.7, 100, 120, 60, 80, "Extreme"],
    "Chile": [-35.6, "CLP", 65, 155, "A", "Low", "Local", 6.2, 100, 220, 50, 75, "Extreme"],
    "China": [35.8, "CNY", 0.42, 0.72, "C+", "High", "Global Supply", 4.3, 100, 220, 50, 50, "High"],
    "Colombia": [4.5, "COP", 380, 750, "B+", "Medium", "Import", 4.5, 99, 110, 60, 30, "Moderate"],
    "Croatia": [45.1, "EUR", 0.10, 0.20, "A", "Low", "EU Certified", 3.7, 100, 230, 50, 50, "High"],
    "Cuba": [21.5, "CUP", 2.5, 5.0, "B", "Medium", "Import", 5.4, 100, 120, 60, 100, "Extreme"],
    "Cyprus": [35.1, "EUR", 0.15, 0.30, "A", "Low", "EU Certified", 5.6, 100, 230, 50, 55, "Extreme"],
    "Czech": [49.8, "CZK", 2.2, 4.8, "A", "Low", "EU Certified", 3.1, 100, 230, 50, 35, "Moderate"],
    "Denmark": [56.2, "DKK", 0.65, 2.80, "A+", "Very Low", "EU Certified", 2.7, 100, 230, 50, 90, "Extreme"],
    "Djibouti": [11.6, "DJF", 30, 60, "C", "High", "Import", 6.2, 61, 220, 50, 65, "Extreme"],
    "Dominican": [18.7, "DOP", 8.5, 17, "B", "Medium", "Import", 5.5, 99, 120, 60, 85, "Extreme"],
    "Ecuador": [-1.8, "USD", 0.10, 0.20, "B+", "Medium", "Import", 4.8, 97, 120, 60, 25, "Low"],
    "Egypt": [26.8, "EGP", 1.2, 2.6, "B", "Medium", "Local Assembly", 6.1, 100, 220, 50, 50, "High"],
    "El Salvador": [13.8, "USD", 0.14, 0.28, "B+", "Medium", "Import", 5.4, 99, 120, 60, 45, "High"],
    "Estonia": [58.6, "EUR", 0.12, 0.28, "A+", "Very Low", "EU Certified", 2.8, 100, 230, 50, 70, "Extreme"],
    "Ethiopia": [9.1, "ETB", 0.5, 1.2, "B", "Medium", "China Import", 5.9, 51, 220, 50, 40, "High"],
    "Fiji": [-18.1, "FJD", 0.25, 0.50, "A-", "Low", "Import", 5.3, 99, 240, 50, 95, "Extreme"],
    "Finland": [61.9, "EUR", 0.08, 0.38, "A+", "Very Low", "EU Certified", 2.5, 100, 230, 50, 60, "Extreme"],
    "France": [46.2, "EUR", 0.15, 0.34, "A+", "Very Low", "EU Certified", 3.5, 100, 230, 50, 45, "High"],
    "Gabon": [-0.8, "XAF", 95, 190, "B", "Medium", "Import", 4.9, 87, 220, 50, 30, "Moderate"],
    "Georgia": [42.3, "GEL", 0.15, 0.30, "B+", "Medium", "Import", 4.2, 100, 220, 50, 50, "High"],
    "Germany": [51.1, "EUR", 0.12, 0.48, "A+", "Very Low", "EU Certified", 3.0, 100, 230, 50, 55, "Extreme"],
    "Ghana": [7.9, "GHS", 0.50, 1.0, "B", "Medium", "Import", 5.4, 86, 230, 50, 40, "High"],
    "Greece": [39.0, "EUR", 0.18, 0.38, "A", "Low", "EU Import", 4.5, 100, 230, 50, 65, "Extreme"],
    "Guatemala": [15.8, "GTQ", 1.2, 2.4, "B", "Medium", "Import", 5.5, 93, 120, 60, 35, "Moderate"],
    "Honduras": [14.1, "HNL", 4.5, 9.0, "B", "Medium", "Import", 5.6, 88, 120, 60, 70, "Extreme"],
    "Hungary": [47.2, "HUF", 35, 75, "A-", "Low", "EU Certified", 3.4, 100, 230, 50, 40, "High"],
    "Iceland": [64.9, "ISK", 8, 18, "A+", "Very Low", "Geothermal", 2.2, 100, 230, 50, 120, "Extreme"],
    "India": [20.5, "INR", 6.2, 12.5, "A-", "Low", "Local Mfg", 5.4, 99, 230, 50, 60, "Extreme"],
    "Indonesia": [-0.7, "IDR", 1500, 3400, "B", "Medium", "Local", 4.8, 99, 220, 50, 50, "High"],
    "Iran": [32.4, "IRR", 800, 2000, "B", "Medium", "Local", 5.6, 100, 220, 50, 70, "Extreme"],
    "Iraq": [33.2, "IQD", 70, 160, "C", "High", "Import", 5.8, 99, 220, 50, 55, "Extreme"],
    "Ireland": [53.1, "EUR", 0.22, 0.55, "A+", "Very Low", "EU Certified", 2.7, 100, 230, 50, 95, "Extreme"],
    "Israel": [31.0, "ILS", 0.40, 0.60, "A", "Low", "Local", 5.7, 100, 230, 50, 50, "High"],
    "Italy": [41.8, "EUR", 0.20, 0.50, "A", "Low", "EU Certified", 4.2, 100, 230, 50, 50, "High"],
    "Jamaica": [18.1, "JMD", 25, 50, "B+", "Medium", "Import", 5.6, 99, 110, 50, 100, "Extreme"],
    "Japan": [36.2, "JPY", 21, 42, "A+", "Very Low", "JP Certified", 3.8, 100, 100, 50, 110, "Extreme"],
    "Jordan": [30.5, "JOD", 0.08, 0.18, "B+", "Medium", "Local", 5.8, 100, 230, 50, 60, "Extreme"],
    "Kazakhstan": [48.0, "KZT", 8, 18, "B", "Medium", "Local", 4.6, 100, 220, 50, 65, "Extreme"],
    "Kenya": [-1.2, "KES", 12, 28, "B", "Medium", "Import", 5.7, 76, 240, 50, 35, "Moderate"],
    "Kuwait": [29.3, "KWD", 0.02, 0.08, "A", "Low", "GCC", 5.9, 100, 240, 50, 70, "Extreme"],
    "Kyrgyzstan": [41.2, "KGS", 2.5, 5.0, "B", "Medium", "Import", 4.5, 100, 220, 50, 45, "High"],
    "Latvia": [56.9, "EUR", 0.11, 0.24, "A", "Low", "EU Certified", 2.8, 100, 230, 50, 60, "Extreme"],
    "Lebanon": [33.9, "LBP", 120, 250, "C", "High", "Import", 5.5, 98, 220, 50, 55, "Extreme"],
    "Libya": [26.3, "LYD", 0.15, 0.30, "C", "High", "Import", 6.0, 99, 230, 50, 65, "Extreme"],
    "Lithuania": [55.2, "EUR", 0.10, 0.22, "A", "Low", "EU Certified", 2.9, 100, 230, 50, 60, "Extreme"],
    "Luxembourg": [49.8, "EUR", 0.18, 0.36, "A+", "Very Low", "EU Certified", 3.0, 100, 230, 50, 40, "High"],
    "Madagascar": [-18.8, "MGA", 450, 900, "C", "High", "Import", 5.6, 36, 220, 50, 75, "Extreme"],
    "Malawi": [-13.9, "MWK", 85, 170, "C", "High", "Import", 5.7, 12, 230, 50, 30, "Moderate"],
    "Malaysia": [4.2, "MYR", 0.38, 0.68, "A-", "Low", "Local Mfg", 4.7, 100, 240, 50, 45, "High"],
    "Mali": [17.6, "XOF", 90, 180, "C", "High", "Import", 5.9, 38, 220, 50, 50, "High"],
    "Malta": [35.9, "EUR", 0.16, 0.32, "A", "Low", "EU Certified", 5.4, 100, 230, 50, 70, "Extreme"],
    "Mexico": [23.6, "MXN", 2.2, 4.8, "B+", "Medium", "US Import", 5.6, 99, 127, 60, 80, "Extreme"],
    "Mongolia": [46.9, "MNT", 180, 360, "B", "Medium", "Import", 4.3, 89, 230, 50, 80, "Extreme"],
    "Morocco": [31.7, "MAD", 1.1, 2.2, "B+", "Medium", "Local", 5.9, 99, 220, 50, 55, "Extreme"],
    "Mozambique": [-18.7, "MZN", 4.5, 9.0, "C", "High", "Import", 5.8, 34, 220, 50, 85, "Extreme"],
    "Myanmar": [19.7, "MMK", 80, 160, "C", "High", "Import", 5.0, 50, 230, 50, 75, "Extreme"],
    "Namibia": [-22.6, "NAD", 1.8, 3.6, "B+", "Medium", "Import", 6.2, 56, 220, 50, 70, "Extreme"],
    "Nepal": [28.3, "NPR", 8.2, 18.5, "B", "Medium", "India Import", 4.7, 95, 230, 50, 40, "High"],
    "Netherlands": [52.1, "EUR", 0.16, 0.55, "A+", "Very Low", "EU Certified", 2.8, 100, 230, 50, 85, "Extreme"],
    "New Zealand": [-40.9, "NZD", 0.11, 0.40, "A+", "Very Low", "AU/NZ", 4.4, 100, 230, 50, 90, "Extreme"],
    "Nicaragua": [12.9, "NIO", 4.2, 8.4, "B", "Medium", "Import", 5.5, 97, 120, 60, 80, "Extreme"],
    "Niger": [17.6, "XOF", 95, 190, "C", "High", "Import", 6.0, 19, 220, 50, 55, "Extreme"],
    "Nigeria": [9.0, "NGN", 70, 160, "C", "High", "Import", 5.5, 62, 230, 50, 45, "High"],
    "North Korea": [40.3, "KPW", 5, 10, "C", "High", "Import", 4.2, 26, 220, 60, 60, "Extreme"],
    "Norway": [60.4, "NOK", 0.9, 2.8, "A+", "Very Low", "EU Certified", 2.3, 100, 230, 50, 80, "Extreme"],
    "Oman": [21.5, "OMR", 0.03, 0.12, "A", "Low", "GCC", 6.0, 100, 240, 50, 65, "Extreme"],
    "Pakistan": [30.3, "PKR", 42.0, 82.0, "B+", "Medium", "China Import", 5.3, 97, 220, 50, 55, "Extreme"],
    "Palestine": [31.9, "ILS", 0.45, 0.90, "C", "High", "Import", 5.7, 100, 230, 50, 50, "High"],
    "Panama": [8.4, "USD", 0.15, 0.30, "A-", "Low", "Import", 4.9, 94, 120, 60, 45, "High"],
    "Paraguay": [-23.4, "PYG", 350, 700, "B+", "Medium", "Import", 5.1, 99, 220, 50, 40, "High"],
    "Peru": [-9.1, "PEN", 0.32, 0.68, "B+", "Medium", "Import", 5.4, 99, 220, 60, 35, "Moderate"],
    "Philippines": [12.8, "PHP", 6.2, 14.0, "B", "Medium", "China Import", 5.1, 94, 220, 60, 95, "Extreme"],
    "Poland": [51.9, "PLN", 0.45, 0.95, "A", "Low", "EU Certified", 3.1, 100, 230, 50, 50, "High"],
    "Portugal": [39.3, "EUR", 0.14, 0.32, "A", "Low", "EU Certified", 4.3, 100, 230, 50, 55, "Extreme"],
    "Qatar": [25.3, "QAR", 0.15, 0.38, "A", "Low", "GCC", 5.9, 100, 240, 50, 60, "Extreme"],
    "Romania": [45.9, "RON", 0.45, 0.95, "A-", "Low", "EU Certified", 3.6, 100, 230, 50, 45, "High"],
    "Russia": [61.5, "RUB", 3.5, 6.2, "B", "Medium", "Local", 3.2, 100, 220, 50, 70, "Extreme"],
    "Rwanda": [-1.9, "RWF", 150, 300, "B+", "Medium", "Import", 5.3, 35, 230, 50, 25, "Low"],
    "Saudi Arabia": [23.8, "SAR", 0.15, 0.32, "A", "Low", "GCC Local", 6.1, 100, 220, 60, 65, "Extreme"],
    "Senegal": [14.7, "XOF", 85, 170, "B", "Medium", "Import", 5.8, 70, 230, 50, 50, "High"],
    "Serbia": [44.0, "RSD", 6, 12, "B+", "Medium", "Import", 3.7, 100, 230, 50, 45, "High"],
    "Singapore": [1.3, "SGD", 0.28, 0.45, "A+", "Very Low", "Import", 4.6, 100, 230, 50, 40, "High"],
    "Slovakia": [48.7, "EUR", 0.12, 0.26, "A", "Low", "EU Certified", 3.2, 100, 230, 50, 45, "High"],
    "Slovenia": [46.1, "EUR", 0.13, 0.27, "A+", "Very Low", "EU Certified", 3.5, 100, 230, 50, 50, "High"],
    "Somalia": [5.1, "SOS", 200, 400, "C", "High", "Import", 6.0, 35, 220, 50, 70, "Extreme"],
    "South Africa": [-30.5, "ZAR", 1.9, 3.8, "B+", "Medium", "Local", 5.7, 85, 230, 50, 60, "Extreme"],
    "South Korea": [37.5, "KRW", 95, 180, "A+", "Very Low", "KR Certified", 3.8, 100, 220, 60, 75, "Extreme"],
    "South Sudan": [6.5, "SSP", 25, 50, "C", "High", "Import", 5.9, 7, 230, 50, 40, "High"],
    "Spain": [40.4, "EUR", 0.22, 0.45, "A", "Low", "EU Certified", 4.6, 100, 230, 50, 60, "Extreme"],
    "Sri Lanka": [7.8, "LKR", 25, 58, "B", "Medium", "India Import", 5.2, 99, 230, 50, 80, "Extreme"],
    "Sudan": [15.5, "SDG", 2.5, 5.0, "C", "High", "Import", 6.1, 52, 230, 50, 60, "Extreme"],
    "Sweden": [60.1, "SEK", 0.85, 2.40, "A+", "Very Low", "EU Certified", 2.6, 100, 230, 50, 75, "Extreme"],
    "Switzerland": [46.8, "CHF", 0.20, 0.45, "A+", "Very Low", "EU Certified", 3.4, 100, 230, 50, 40, "High"],
    "Syria": [34.8, "SYP", 35, 70, "C", "High", "Import", 5.8, 89, 220, 50, 55, "Extreme"],
    "Tajikistan": [38.5, "TJS", 0.25, 0.50, "B", "Medium", "Import", 4.6, 100, 220, 50, 50, "High"],
    "Tanzania": [-6.1, "TZS", 180, 420, "B", "Medium", "Import", 5.6, 38, 230, 50, 40, "High"],
    "Thailand": [15.8, "THB", 2.8, 6.0, "A-", "Low", "Local Mfg", 5.0, 100, 220, 50, 60, "Extreme"],
    "Tunisia": [34.0, "TND", 0.18, 0.38, "B+", "Medium", "Local", 5.8, 100, 230, 50, 55, "Extreme"],
    "Turkey": [38.9, "TRY", 3.5, 6.5, "B+", "Medium", "Local", 4.9, 100, 230, 50, 50, "High"],
    "UAE": [23.4, "AED", 0.22, 0.48, "A", "Low", "GCC Local", 5.9, 100, 220, 50, 65, "Extreme"],
    "Uganda": [1.4, "UGX", 580, 1160, "B", "Medium", "Import", 5.5, 42, 240, 50, 30, "Moderate"],
    "Ukraine": [48.3, "UAH", 1.8, 4.2, "B", "Medium", "EU Import", 3.4, 100, 220, 50, 50, "High"],
    "UK": [55.3, "GBP", 0.22, 0.58, "A+", "Very Low", "UK/EU Certified", 2.8, 100, 230, 50, 80, "Extreme"],
    "Uruguay": [-32.5, "UYU", 3.8, 7.6, "A", "Low", "Import", 4.8, 100, 230, 50, 70, "Extreme"],
    "USA": [37.0, "USD", 0.14, 0.30, "A+", "Very Low", "US Certified", 4.8, 100, 120, 60, 90, "Extreme"],
    "Uzbekistan": [41.3, "UZS", 250, 500, "B", "Medium", "Local", 5.2, 100, 220, 50, 50, "High"],
    "Venezuela": [6.4, "VES", 0.02, 0.04, "C", "High", "Import", 5.2, 99, 120, 60, 35, "Moderate"],
    "Vietnam": [14.0, "VND", 2200, 3800, "B+", "Medium", "Local Mfg", 4.8, 100, 220, 50, 85, "Extreme"],
    "Yemen": [15.4, "YER", 40, 80, "C", "High", "Import", 5.9, 47, 220, 50, 60, "Extreme"],
    "Zambia": [-13.1, "ZMW", 1.2, 2.4, "B", "Medium", "Import", 5.7, 45, 230, 50, 35, "Moderate"],
    "Zimbabwe": [-19.0, "USD", 0.10, 0.25, "C", "High", "Import", 5.8, 47, 230, 50, 40, "High"],
}
 
panel_db = {
    "Jinko 545W Mono PERC": [21.5, 0.55, 0.28, -0.35, 49.8, 13.8, "Tier-1 Standard"],
    "Trina 550W Mono PERC": [21.8, 0.58, 0.29, -0.36, 50.1, 13.9, "Tier-1 Standard"],
    "LONGi 540W Hi-MO4": [21.2, 0.52, 0.27, -0.35, 49.5, 13.7, "Tier-1 Standard"],
    "Canadian 545W CS3W": [21.6, 0.56, 0.28, -0.35, 49.9, 13.8, "Tier-1 Standard"],
    "Jinko 580W TOPCon N-Type": [23.5, 0.65, 0.32, -0.30, 50.8, 14.5, "Tier-1 High Eff"],
    "Trina 575W TOPCon": [23.8, 0.68, 0.33, -0.29, 51.0, 14.6, "Tier-1 High Eff"],
    "LONGi 570W Hi-MO5": [23.2, 0.62, 0.31, -0.31, 50.5, 14.3, "Tier-1 High Eff"],
    "JA Solar 575W DeepBlue 3.0": [23.6, 0.66, 0.32, -0.30, 50.9, 14.5, "Tier-1 High Eff"],
    "Risen 590W Hyper-ion": [24.0, 0.70, 0.34, -0.29, 51.2, 14.7, "Tier-1 Premium"],
    "Huansheng 610W HJT": [24.5, 0.75, 0.38, -0.25, 51.5, 15.0, "HJT Premium"],
    "REC Alpha Pure 410W HJT": [24.2, 0.72, 0.37, -0.24, 51.3, 14.9, "HJT Premium"],
    "Tongwei 600W TNC HJT": [24.8, 0.78, 0.39, -0.24, 51.8, 15.2, "HJT Premium"],
    "Jinko 605W Bifacial TOPCon": [24.2, 0.68, 0.35, -0.29, 51.0, 14.6, "Bifacial Dual Glass"],
    "Trina 600W Vertex Bifacial": [24.0, 0.65, 0.34, -0.29, 50.8, 14.5, "Bifacial Dual Glass"],
    "Canadian 590W Bifacial": [23.6, 0.62, 0.33, -0.30, 50.5, 14.3, "Bifacial Dual Glass"],
    "SunPower 415W Maxeon 6 IBC": [25.2, 0.85, 0.42, -0.22, 52.5, 12.8, "IBC Premium"],
    "Maxeon 3 400W IBC": [24.8, 0.80, 0.40, -0.23, 52.0, 12.6, "IBC Premium"],
    "Aiko 625W ABC IBC": [25.5, 0.88, 0.43, -0.21, 52.8, 13.0, "IBC Ultra Premium"],
    "Oxford PV 550W Perovskite": [29.5, 1.20, 0.55, -0.20, 53.5, 12.5, "Future Tech"],
    "LONGi 530W Silicon-Perovskite": [28.8, 1.15, 0.52, -0.21, 53.0, 12.4, "Future Tech"],
    "First Solar 460W CdTe Thin Film": [18.5, 0.35, 0.22, -0.25, 48.5, 14.5, "Thin Film Low Cost"],
    "Solar Frontier 170W CIGS": [17.8, 0.30, 0.20, -0.28, 47.5, 13.8, "CIGS Thin Film"],
    "QCells 415W Q.PEAK DUO": [21.0, 0.50, 0.26, -0.35, 49.2, 13.5, "QCells Standard"],
    "QCells 480W Q.TRON": [22.8, 0.60, 0.30, -0.32, 50.3, 14.2, "QCells Premium"],
    "JA 545W DeepBlue 3.0 Mono": [21.4, 0.54, 0.28, -0.35, 49.7, 13.7, "JA Standard"],
    "Risen 550W RSM144": [21.7, 0.57, 0.28, -0.35, 49.9, 13.8, "Risen Standard"],
}
 
battery_db = {
    "LiFePO4 LFP": [94, 6000, 180, 2.0, 48, "Cobalt Free"],
    "NMC Lithium": [92, 4000, 220, 2.5, 48, "High Energy"],
    "Lead Acid AGM": [85, 1200, 120, 5.0, 24, "Cheap"],
    "Sodium Ion": [90, 3000, 150, 3.0, 48, "Emerging"],
    "Solid State": [96, 8000, 350, 1.5, 48, "Future"],
    "No Battery": [0, 0, 0, 0, 0, "Grid Only"],
}
 
inverter_db = {
    "String Inverter": [97.5, 1.0, 800, "Central MPPT"],
    "Micro Inverter": [96.8, 1.05, 1200, "Panel Level MPPT"],
    "Hybrid Inverter": [97.0, 1.02, 1500, "Battery + Grid"],
    "Power Optimizer": [98.0, 1.03, 1400, "DC Optimizer"],
    "Central Inverter": [98.5, 0.98, 600, "Large Scale"],
}
 
structure_db = {
    "Low": {"type": "Aluminum Fixed Tilt", "tilt_max": 30, "material": "Anodized AL-6005-T5", "foundation": "Ground Screw", "clamp": "Standard Mid/End"},
    "Moderate": {"type": "Galvanized Steel", "tilt_max": 25, "material": "Hot Dip Galvanized Steel Q235", "foundation": "Concrete Ballast", "clamp": "Reinforced Clamp"},
    "High": {"type": "Galvanized Steel + Bracing", "tilt_max": 20, "material": "Galvanized Steel + Cross Bracing", "foundation": "Concrete Footing", "clamp": "Heavy Duty Clamp"},
    "Extreme": {"type": "Steel Structure + Wind Deflector", "tilt_max": 15, "material": "S355 Steel + Wind Deflector", "foundation": "Deep Concrete Pile", "clamp": "Hurricane Rated Clamp"},
}
 
BATTERY_TYPES = {
    "Lithium-Ion": {"default_dod": 90, "efficiency": 95, "life_years": 10},
    "Lead-Acid": {"default_dod": 50, "efficiency": 80, "life_years": 3},
    "Gel Battery": {"default_dod": 70, "efficiency": 85, "life_years": 5},
}
 
# ============================================================
# UTILITY & PHYSICS FUNCTIONS
# ============================================================
 
@st.cache_data(ttl=86400)
def safe_geocode(country_name, c_lat_fallback):
    if not GEO_ENABLED:
        return c_lat_fallback, 70.0, country_name
    try:
        geolocator = Nominatim(user_agent="solarx_app_final_v3", timeout=3)
        location = geolocator.geocode(country_name)
        if location:
            return location.latitude, location.longitude, location.address.split(',')[0]
        return c_lat_fallback, 70.0, country_name
    except Exception:
        return c_lat_fallback, 70.0, country_name
 
@st.cache_data(ttl=1800)
def fetch_meteorological_data(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,wind_speed_10m,cloud_cover",
        "timezone": "auto", "forecast_days": 3,
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            h_data = res.json().get("hourly", {})
            df = pd.DataFrame({
                "Timestamp": pd.to_datetime(h_data.get("time")),
                "Temperature": h_data.get("temperature_2m"),
                "Wind_Speed": h_data.get("wind_speed_10m"),
                "Cloud_Cover": h_data.get("cloud_cover"),
            })
            df["Hour"] = df["Timestamp"].dt.hour
            return df
    except Exception:
        pass
    return None
 
@st.cache_data(ttl=1800)
def get_7day_weather(lat, lon):
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&daily=temperature_2m_max,temperature_2m_min,wind_speed_10m_max,cloud_cover_mean"
               f"&hourly=temperature_2m,wind_speed_10m,cloud_cover&timezone=auto")
        r = requests.get(url, timeout=7)
        data = r.json()
        daily = data['daily']
        hourly = data['hourly']
        week_data = []
        for i in range(7):
            week_data.append({
                'date': daily['time'][i],
                'temp_max': daily['temperature_2m_max'][i],
                'temp_min': daily['temperature_2m_min'][i],
                'wind_max': daily['wind_speed_10m_max'][i] * 3.6,
                'cloud': daily['cloud_cover_mean'][i],
            })
        return week_data, hourly
    except Exception:
        return None, None
 
def calc_wind_load(wind_speed_kmh, tilt_angle, panel_qty):
    wind_ms = wind_speed_kmh / 3.6
    q = 0.613 * wind_ms ** 2
    cp = 1.2 if tilt_angle > 30 else 0.8
    force_per_panel = q * cp * 2.6 / 1000
    return force_per_panel * panel_qty
 
def calc_lightning_protection(building_height):
    if building_height > 20:
        return building_height + 2, 20
    return building_height + 1.5, 30
 
def model_solar_physics(temp, wind, cloud, hour, cfg, scenario_mode="live"):
    """Physics engine combining irradiance, tilt, NOCT, degradation, soiling."""
    if 6 <= hour <= 18:
        amplitude = 1050.0 if scenario_mode == "live" else 950.0
        base_ghi = amplitude * np.sin(np.pi * (hour - 6) / 12)
        tilt_factor = np.cos(np.radians(cfg["tilt"] - 25))
        azimuth_factor = np.cos(np.radians(cfg["azimuth"] - 180))
        effective_ghi = base_ghi * max(0.4, tilt_factor * azimuth_factor)
    else:
        return {"Power_kW": 0.0, "Cell_Temp": temp, "Irradiance": 0.0}
 
    attenuation = (cloud / 100.0) * 0.82
    incident_irradiance = effective_ghi * (1.0 - attenuation)
 
    noct_constant = 45.0 if cfg["panel_type"] == "Monocrystalline" else 48.0
    cooling_index = 1.0 + (wind * 0.035)
    cell_temp = temp + ((noct_constant - 20.0) * (incident_irradiance / 800.0) / cooling_index)
 
    thermal_loss = 1.0
    if cell_temp > 25.0:
        thermal_loss = 1.0 - ((cell_temp - 25.0) * abs(cfg["temp_coef"]))
 
    total_age_loss = cfg["system_age"] * (cfg["annual_degrad"] / 100.0)
    retained_efficiency = max(0.5, 1.0 - total_age_loss)
 
    field_peak_kw = (cfg["panel_w"] * cfg["panel_count"]) / 1000.0
    net_output_kw = (field_peak_kw * (incident_irradiance / 1000.0) * thermal_loss
                     * (cfg["inverter_eff"] / 100.0) * (1.0 - cfg["soiling"] / 100.0) * retained_efficiency)
    return {
        "Power_kW": max(0.0, round(net_output_kw, 3)),
        "Cell_Temp": round(cell_temp, 2),
        "Irradiance": round(incident_irradiance, 2),
    }
 
def compute_financial_net_metering(daily_gen_kwh, daily_load_kwh, cfg):
    import_tariff = cfg["tariff_import"]
    export_tariff = cfg["tariff_export"]
    if daily_gen_kwh >= daily_load_kwh:
        surplus_kwh = daily_gen_kwh - daily_load_kwh
        daily_credit = surplus_kwh * export_tariff
        net_financial_benefit = (daily_load_kwh * import_tariff) + daily_credit
        daily_bill = 0.0
    else:
        deficit_kwh = daily_load_kwh - daily_gen_kwh
        daily_bill = deficit_kwh * import_tariff
        daily_credit = 0.0
        net_financial_benefit = daily_gen_kwh * import_tariff
    system_capital_cost = cfg["panel_count"] * cfg["cost_per_panel"]
    annual_savings = net_financial_benefit * 365.25
    payback_years = system_capital_cost / annual_savings if annual_savings > 0 else 99.0
    return {
        "Daily_Savings_Currency": round(net_financial_benefit, 2),
        "Daily_Bill_Due": round(daily_bill, 2),
        "Export_Credit": round(daily_credit, 2),
        "Estimated_Payback_Years": round(payback_years, 2),
        "Total_CapEx": system_capital_cost,
    }
 
def generate_pdf_report(data_dict):
    if not PDF_ENABLED:
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 18)
    def safe_text(txt):
        return str(txt).encode('ascii', 'ignore').decode('ascii')
    pdf.cell(0, 12, safe_text('SolarX Pro - Solar Analysis Report'), 0, 1, 'C')
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, safe_text(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}'), 0, 1, 'C')
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, safe_text('SYSTEM CONFIGURATION'), 0, 1)
    pdf.set_font('Arial', '', 11)
    for key, val in data_dict.items():
        pdf.cell(0, 7, safe_text(f'{key}: {val}'), 0, 1)
    pdf_bytes = pdf.output(dest='S')
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin-1', 'replace')
    return pdf_bytes
 
# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("⚡ Solar Power Estimator Pro")
 
    country = st.selectbox("🌍 Country - 120+ Options", sorted(db.keys()), key="country_select_main")
    country_data = list(db[country]) + [None] * 15
    c_lat, c_curr, c_sale, c_buy = country_data[0], country_data[1], country_data[2], country_data[3]
    esg_rating, labor_risk, sourcing = country_data[4], country_data[5], country_data[6]
    avg_ghi, elec_access, grid_v, grid_f = country_data[7], country_data[8], country_data[9], country_data[10]
    wind_kmh_db, wind_zone = country_data[11], country_data[12]
 
    st.divider()
    st.markdown("### 🔌 Telemetry Mode")
    live_weather_toggle = st.toggle("Activate Live Satellite Telemetry", value=False,
                                    help="ON = Live GPS coords | OFF = Country DB profiles")
 
# ============================================================
# MAIN INPUTS
# ============================================================
col1, col2, col3 = st.columns(3)
with col1:
    panel_type = st.selectbox("Solar Panel Type", list(panel_db.keys()), key="panel_sel")
    p_eff, p_cost, voc, p_temp, voc_std, isc, p_note = panel_db[panel_type]
    p_qty = st.number_input("Number of Panels", min_value=1, max_value=50000, value=22, key="p_qty")
 
with col2:
    inverter_type = st.selectbox("Inverter Type", list(inverter_db.keys()), key="inv_sel")
    inv_eff, inv_bonus, inv_cost, inv_note = inverter_db[inverter_type]
    tilt = st.slider("Tilt Angle °", 0, 60, 25, key="tilt")
    azimuth = st.slider("Azimuth °", -180, 180, 180, key="azimuth")
 
with col3:
    building_height = st.number_input("Building Height m", 3.0, 50.0, 6.0, key="b_height")
    wire_length = st.number_input("DC Cable Length m", 10, 200, 50, key="wire_len")
    cable_size = st.selectbox("DC Cable mm²", [4, 6, 10, 16, 25], key="cable")
 
st.divider()
 
with st.expander("🔋 Battery & Load"):
    battery_type = st.selectbox("Battery Type", list(battery_db.keys()), key="bat_sel")
    b_eff, b_cycles, b_cost, b_degrade, b_voltage, b_note = battery_db[battery_type]
    has_batt = battery_type != "No Battery"
    b_cap = st.number_input("Battery kWh", value=20.0) if has_batt else 0
    dod = st.slider("DoD %", 50, 95, 85) if has_batt else 0
    h_load = st.number_input("Daily Load kWh", value=55.0, key="h_load")
    net_metering = st.checkbox("Net Metering", value=True)
 
with st.expander("⚙️ Advanced Physics Config"):
    panel_w_adv = st.number_input("Unit Panel Power (W) [Advanced]", 200, 700, int(p_eff * 25), 5)
    system_age = st.slider("System Age (Years)", 0, 25, 1)
    annual_degrad = st.number_input("Annual Degradation %", 0.1, 2.0, 0.5, 0.1)
    soiling_adv = st.slider("Soiling % [Advanced]", 0.0, 20.0, 3.5, 0.5)
 
with st.expander("🌤️ Environment"):
    sun_h = st.slider("Peak Sun Hours", 3.0, 8.5, float(avg_ghi), key="sun_h")
    sys_loss = st.slider("System Losses %", 8, 30, 14, key="sys_loss")
    soiling = st.slider("Soiling %", 0, 20, 5, key="soiling")
    temp_ambient = st.slider("Temp °C", 15, 50, 28, key="temp_amb")
 
with st.expander("💹 Financial"):
    buy_rate = st.number_input(f"Buy Rate {c_curr}", value=float(c_buy), key="buy_rate")
    sell_rate = st.number_input(f"Sell Rate {c_curr}", value=float(c_sale), key="sell_rate")
    tax_val = st.slider("Tax %", 0, 30, 17, key="tax")
    install_cost = st.number_input(f"Install/kWp {c_curr}", value=42000.0 if country == "Pakistan" else 750.0, key="install")
    discount_rate = st.slider("Discount %", 3, 15, 8, key="discount")
    cost_per_panel_adv = st.number_input("Cost per Panel installed", 10.0, 10000.0, 250.0, 10.0)
 
# ============================================================
# CALCULATIONS
# ============================================================
 
# Basic array sizing
sys_size = (p_eff * p_qty * 100) / 1000
panels_per_string = int(1000 / voc_std)
strings = math.ceil(p_qty / panels_per_string)
voc_string = voc_std * panels_per_string
isc_string = isc * strings
mppt_voltage = voc_string * 0.8
 
# Location
lat, lon, location_name = safe_geocode(country, c_lat)
wind = wind_kmh_db
cloud_pct = 20
 
# Wind & structure
wind_force = calc_wind_load(wind, tilt, p_qty)
struct = structure_db[wind_zone]
wind_safe = wind_force < (sys_size * 50)
rod_height, protection_radius = calc_lightning_protection(building_height)
 
# Electrical
current_dc = (sys_size * 1000) / 400
voltage_drop = (current_dc * wire_length * 0.0175) / cable_size
vd_percent = (voltage_drop / mppt_voltage) * 100 if mppt_voltage > 0 else 0
 
# Generation profile (24h)
hours = np.arange(24)
angle_eff = np.cos(np.radians(tilt - abs(c_lat))) * np.cos(np.radians(azimuth))
temp_loss = 1 + (p_temp / 100) * (temp_ambient + 25 - 25)
soiling_loss = 1 - soiling / 100
weather_factor = 1 - cloud_pct * 0.008 + wind * 0.0003
 
daily_yield = (sys_size * sun_h * ((100 - sys_loss) / 100) * max(0.3, angle_eff)
               * (p_eff / 21.5) * temp_loss * soiling_loss * (inv_eff / 100) * inv_bonus * weather_factor)
 
gen_24 = [max(0, daily_yield / 12 * np.sin(np.pi * (h - 6) / 12)) if 6 <= h <= 18 else 0 for h in hours]
load_24 = [(h_load / 24) * (2.8 if (h > 18 or h < 7) else 0.7) for h in hours]
 
# Battery SOC simulation
soc = []
c_soc = b_cap * (dod / 100) if has_batt else 0
for g, l in zip(gen_24, load_24):
    if has_batt:
        diff = g - l
        c_soc = max(0, min(b_cap, c_soc + diff * (b_eff / 100)))
    soc.append(c_soc)
 
export_24 = [max(0, g - l - (soc[i] - soc[i - 1] if i > 0 else 0)) for i, (g, l) in enumerate(zip(gen_24, load_24))]
import_24 = [max(0, l - g - (soc[i - 1] - soc[i] if i > 0 else 0)) for i, (g, l) in enumerate(zip(gen_24, load_24))]
 
# Financials
battery_cost = b_cap * b_cost if has_batt else 0
panel_cost = sys_size * 1000 * p_cost
inverter_cost = sys_size * inv_cost
structure_cost = sys_size * 150
cable_cost = wire_length * cable_size * 2.5
lightning_cost = rod_height * 80
gross_cost = (panel_cost + battery_cost + inverter_cost + structure_cost
              + cable_cost + lightning_cost + sys_size * install_cost)
net_cost = gross_cost * (0.70 if country == "Pakistan" else 1.0)
 
years = np.arange(25)
yearly_gen = [sum(gen_24) * 365 * (1 - b_degrade / 100) ** y for y in years]
gen_ratio = sum(export_24) / sum(gen_24) if sum(gen_24) > 0 else 0
yearly_profit = [y * ((1 - gen_ratio) * buy_rate + gen_ratio * sell_rate) * (1 - tax_val / 100) for y in yearly_gen]
payback = net_cost / yearly_profit[0] if yearly_profit[0] > 0 else 99
npv = sum([p / ((1 + discount_rate / 100) ** i) for i, p in enumerate(yearly_profit)]) - net_cost
 
# Advanced physics engine config
adv_cfg = {
    "panel_type": "Monocrystalline",
    "panel_w": panel_w_adv, "panel_count": p_qty, "cost_per_panel": cost_per_panel_adv,
    "temp_coef": p_temp / 100,
    "tilt": tilt, "azimuth": azimuth, "system_age": system_age,
    "annual_degrad": annual_degrad, "inverter_eff": inv_eff,
    "soiling": soiling_adv, "tariff_import": buy_rate, "tariff_export": sell_rate,
}
 
# Advanced financials
total_daily_load_kwh = h_load
fin_report = compute_financial_net_metering(daily_yield, total_daily_load_kwh, adv_cfg)
total_battery_storage_kwh = (adv_cfg["battery_ah"] * adv_cfg["battery_v"] / 1000.0) if "battery_ah" in adv_cfg else b_cap
usable_battery_storage_kwh = b_cap * (dod / 100) if has_batt else 0
hours_of_autonomy = usable_battery_storage_kwh / (h_load / 24) if h_load > 0 else 0
 
# Add missing keys to adv_cfg
adv_cfg["battery_ah"] = int(b_cap * 1000 / max(b_voltage, 1)) if has_batt else 200
adv_cfg["battery_v"] = b_voltage if has_batt else 48
 
# ============================================================
# HEADER
# ============================================================
st.markdown(f"<div class='main-header'>⚡ Solar Power Estimator Pro: {country} | 📍 {location_name}</div>",
            unsafe_allow_html=True)
 
# ============================================================
# KPI METRICS
# ============================================================
k1, k2, k3, k4, k5, k6, k7, k8, k9, k10 = st.columns(10)
k1.metric("System kWp", f"{sys_size:.2f}")
k2.metric("Panel", panel_type.split()[0])
k3.metric("Inverter", inverter_type.split()[0])
k4.metric("Daily Gen", f"{sum(gen_24):.1f} kWh")
k5.metric("Battery", battery_type.split()[0] if has_batt else "None")
k6.metric("VOC String", f"{voc_string:.0f} V")
k7.metric("VD Loss", f"{vd_percent:.2f}%")
k8.metric("Self Use", f"{(1 - sum(import_24) / h_load) * 100:.1f}%")
k9.metric("ESG", esg_rating)
if wind_zone == "Extreme":
    k10.metric("Wind Risk", "EXTREME", f"{wind:.0f} km/h", delta_color="inverse")
elif wind_zone == "High":
    k10.metric("Wind Risk", "HIGH", f"{wind:.0f} km/h", delta_color="inverse")
elif wind_zone == "Moderate":
    k10.metric("Wind Risk", "MODERATE", f"{wind:.0f} km/h")
else:
    k10.metric("Wind Risk", "LOW", f"{wind:.0f} km/h", delta_color="normal")
 
st.divider()
 
# ============================================================
# TABS (16 TABS - MERGED)
# ============================================================
tabs = st.tabs([
    "📊 Energy", "🔧 Technical", "🔌 Inverter", "🔋 Battery", "⚡ Electrical",
    "💰 Financial", "🌿 Eco", "🛡️ Ethics", "📈 Net Metering", "🤖 AI Diagnosis",
    "🌤️ Weather", "🏗️ Structure", "⚙️ Protection", "📡 Physics Engine",
    "📊 Storage Matrix", "📄 Export",
])
 
# Tab 0: Energy
with tabs[0]:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(hours), y=gen_24, name="Solar Gen", fill='tozeroy', line=dict(color='#667eea', width=4)))
    fig.add_trace(go.Scatter(x=list(hours), y=load_24, name="Load", line=dict(color='#f5576c', width=3)))
    if has_batt:
        fig.add_trace(go.Scatter(x=list(hours), y=soc, name="Battery SOC", line=dict(color='#4ade80', width=3)))
    fig.update_layout(height=500, plot_bgcolor='rgba(255,255,255,0.8)', paper_bgcolor='rgba(255,255,255,0)',
                      title="24-Hour Generation vs Load Profile")
    st.plotly_chart(fig, use_container_width=True)
 
# Tab 1: Technical
with tabs[1]:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='feature-box'><b>Panel:</b><br>{panel_type}<br>Eff: {p_eff}%<br>VOC: {voc}V<br>ISC: {isc}A<br>Note: {p_note}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='feature-box'><b>Array:</b><br>Panels: {p_qty}<br>Strings: {strings}<br>Per String: {panels_per_string}<br>Area: {p_qty * 2.2:.1f} m²</div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='feature-box'><b>Conditions:</b><br>Tilt: {tilt}°<br>Azimuth: {azimuth}°<br>Temp: {temp_ambient}°C<br>GHI: {avg_ghi} kWh/m²</div>", unsafe_allow_html=True)
 
# Tab 2: Inverter
with tabs[2]:
    st.markdown("<span class='info-label'>INVERTER DESIGN</span>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Inverter Type", inverter_type)
        st.metric("Efficiency", f"{inv_eff}%")
    with c2:
        st.metric("Grid Voltage", f"{grid_v}V {grid_f}Hz")
        st.metric("Inverter Bonus", f"+{(inv_bonus - 1) * 100:.1f}%")
    with c3:
        st.markdown(f"<div class='feature-box'><b>Notes:</b><br>{inv_note}<br><br>DC Input: {voc_string:.0f}V</div>", unsafe_allow_html=True)
 
# Tab 3: Battery
with tabs[3]:
    if has_batt:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Battery Type", battery_type)
            st.metric("Capacity", f"{b_cap} kWh")
        with c2:
            st.metric("Efficiency", f"{b_eff}%")
            st.metric("DoD", f"{dod}%")
        with c3:
            st.markdown(f"<div class='feature-box'><b>Backup:</b><br>{b_cap / h_load * 24:.1f} hours<br><br>Cycles: {b_cycles}<br>Notes: {b_note}</div>", unsafe_allow_html=True)
    else:
        st.info("Grid-Tied System - No Battery")
 
# Tab 4: Electrical
with tabs[4]:
    st.markdown("<span class='info-label'>⚡ ELECTRICAL DESIGN</span>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("DC Voltage VOC", f"{voc_string:.0f} V")
        st.metric("DC Current ISC", f"{isc_string:.1f} A")
        st.metric("MPPT Voltage", f"{mppt_voltage:.0f} V")
    with c2:
        st.metric("Cable Size", f"{cable_size} mm²")
        st.metric("Cable Length", f"{wire_length} m")
        st.metric("Voltage Drop", f"{voltage_drop:.2f} V")
    with c3:
        st.metric("VD % Loss", f"{vd_percent:.2f}%")
        st.metric("Grid Voltage", f"{grid_v}V {grid_f}Hz")
        st.metric("Building Height", f"{building_height} m")
    st.divider()
    st.markdown("<span class='info-label'>⚡ LIGHTNING PROTECTION - IEC 62305</span>", unsafe_allow_html=True)
    c4, c5 = st.columns(2)
    with c4:
        st.metric("Lightning Rod Height", f"{rod_height:.1f} m")
        st.metric("Protection Radius", f"{protection_radius} m")
    with c5:
        st.markdown(f"<div class='feature-box'><b>Notes:</b><br>• Rod height = Building + 1.5m<br>• Radius = 30m for <20m building<br>• Cost: {lightning_cost:,.0f} {c_curr}</div>", unsafe_allow_html=True)
    if vd_percent > 3:
        st.warning(f"⚠️ Voltage Drop {vd_percent:.2f}% > 3%! Increase cable from {cable_size}mm² to {cable_size + 6}mm²")
    else:
        st.success(f"✅ Voltage Drop {vd_percent:.2f}% - Design OK")
 
# Tab 5: Financial
with tabs[5]:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gross Cost", f"{gross_cost:,.0f} {c_curr}")
    col2.metric("After Subsidy", f"{net_cost:,.0f} {c_curr}")
    col3.metric("Payback", f"{payback:.1f} Years")
    col4.metric("25Yr NPV", f"{npv:,.0f} {c_curr}")
    st.progress(min(1.0, payback / 12))
 
    # 25-year cash flow chart
    fig_fin = go.Figure()
    cumulative = np.cumsum(yearly_profit) - net_cost
    fig_fin.add_trace(go.Bar(x=list(range(25)), y=list(yearly_profit), name="Annual Profit", marker_color='#667eea'))
    fig_fin.add_trace(go.Scatter(x=list(range(25)), y=list(cumulative), name="Cumulative NPV", line=dict(color='#f5576c', width=3)))
    fig_fin.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_fin.update_layout(height=400, title="25-Year Financial Projection", plot_bgcolor='rgba(255,255,255,0.8)')
    st.plotly_chart(fig_fin, use_container_width=True)
 
    st.divider()
    st.markdown("**Advanced Payback Analysis**")
    fa1, fa2, fa3 = st.columns(3)
    fa1.metric("Project CapEx", f"{fin_report['Total_CapEx']:,.0f}")
    fa2.metric("Daily Fiscal Return", f"{fin_report['Daily_Savings_Currency']}")
    fa3.metric("Break-Even Time", f"{fin_report['Estimated_Payback_Years']} Years")
 
# Tab 6: Eco
with tabs[6]:
    co2_annual = sum(gen_24) * 365 * 0.82 / 1000
    st.success(f"CO2 Avoided: **{co2_annual:.2f} Tons/Year** | Trees Equivalent: {int(co2_annual * 18)}")
    coal_saved = co2_annual / 2.2
    st.metric("Coal Saved (tons/yr)", f"{coal_saved:.1f}")
    st.metric("Lifetime CO2 Avoided", f"{co2_annual * 25:.1f} tons")
 
# Tab 7: Ethics
with tabs[7]:
    st.markdown("<div class='feature-box'><b>🛡️ ESG Compliance</b></div>", unsafe_allow_html=True)
    st.metric("ESG Rating", esg_rating)
    st.write(f"Sourcing: {sourcing} | Labor Risk: {labor_risk}")
    st.write(f"Electricity Access: {elec_access}%")
 
# Tab 8: Net Metering
with tabs[8]:
    st.markdown("<span class='info-label'>NET METERING</span>", unsafe_allow_html=True)
    if net_metering:
        st.success("✅ Net Metering Active")
        st.metric("Export to Grid", f"{sum(export_24):.1f} kWh/day")
        st.metric("Credit Value", f"{sum(export_24) * sell_rate:,.0f} {c_curr}/day")
        st.metric("Export Credit (Adv)", f"{fin_report['Export_Credit']}")
    else:
        st.warning("⚠️ Net Metering Off")
 
# Tab 9: AI Diagnosis
with tabs[9]:
    st.markdown("<div class='feature-box'><b>🤖 AI Diagnosis</b></div>", unsafe_allow_html=True)
    pr = (sum(gen_24) / (sys_size * sun_h)) * 100 if sys_size * sun_h > 0 else 0
    st.metric("Performance Ratio", f"{pr:.1f}%")
    if vd_percent > 3:
        st.warning("⚠️ Increase cable size to reduce voltage drop losses")
    if tilt > struct["tilt_max"]:
        st.warning(f"⚠️ Tilt {tilt}° exceeds max {struct['tilt_max']}° for {wind_zone} wind zone")
    if not wind_safe:
        st.error(f"⚠️ HIGH WIND LOAD: {wind_force:.1f} kN detected!")
    if pr > 80:
        st.success("✅ Excellent design - PR > 80%")
    elif pr > 70:
        st.info("ℹ️ Good design - some optimization possible")
    else:
        st.warning("⚠️ Low PR - review losses and orientation")
    st.text_area("System Report", value=f"""
========================================================================
SOLAR SYSTEMS ENGINEERING AUDIT REPORT
Time: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================================================
- Peak PV Capacity: {sys_size:.2f} kWp
- Panel Count: {p_qty} x {panel_type}
- Performance Ratio: {pr:.1f}%
- Average Irradiance: ~{avg_ghi * 1000 / 12:.0f} W/m² (peak hours)
- Financial Export: {fin_report['Export_Credit']} credits/day
========================================================================
""", height=200)
 
# Tab 10: Weather
with tabs[10]:
    st.markdown("<span class='info-label'>WEATHER & WIND ANALYSIS</span>", unsafe_allow_html=True)
 
    if use_live_weather and password == LIVE_PASSWORD:
        week_weather, _ = get_7day_weather(lat, lon)
        if week_weather:
            st.success(f"✅ LIVE CONNECTED: {location_name}")
            col_map, col_data = st.columns([1, 1])
            with col_map:
                if FOLIUM_ENABLED:
                    import folium
                    from streamlit_folium import st_folium
                    m = folium.Map(location=[lat, lon], zoom_start=10)
                    folium.Marker([lat, lon], popup=location_name,
                                  icon=folium.Icon(color='red', icon='bolt')).add_to(m)
                    st_folium(m, height=350, width=400, key=f"map_{lat}_{lon}")
                else:
                    st.info(f"📍 {location_name} | Lat: {lat:.4f}, Lon: {lon:.4f}")
            with col_data:
                st.metric("Today Wind", f"{week_weather[0]['wind_max']:.1f} km/h")
                st.metric("Today Temp Max", f"{week_weather[0]['temp_max']:.1f}°C")
                st.metric("Today Temp Min", f"{week_weather[0]['temp_min']:.1f}°C")
 
            dates = [w['date'][5:] for w in week_weather]
            fig_w = go.Figure()
            fig_w.add_trace(go.Bar(x=dates, y=[w['temp_max'] for w in week_weather], name="Max °C", marker_color='#ef4444'))
            fig_w.add_trace(go.Bar(x=dates, y=[w['temp_min'] for w in week_weather], name="Min °C", marker_color='#3b82f6'))
            fig_w.add_trace(go.Scatter(x=dates, y=[w['wind_max'] for w in week_weather], name="Wind km/h",
                                       yaxis='y2', line=dict(color='#f59e0b', width=3)))
            fig_w.update_layout(title="7-Day Weather Forecast", yaxis=dict(title="Temperature °C"),
                                 yaxis2=dict(title="Wind km/h", overlaying='y', side='right'),
                                 height=400, barmode='group', plot_bgcolor='rgba(255,255,255,0.8)')
            st.plotly_chart(fig_w, use_container_width=True)
        else:
            st.error("⚠️ Weather API offline. Refresh in 2 minutes.")
    elif use_live_weather and password != LIVE_PASSWORD:
        st.error("❌ Incorrect password.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Location", location_name)
            st.metric("Cloud Cover", f"{cloud_pct}%")
            st.metric("Wind Speed", f"{wind:.1f} km/h")
            st.metric("Daily Yield (DB)", f"{daily_yield:.1f} kWh")
        with col2:
            if wind > 80:
                st.markdown(f"<div class='wind-alert'>🔴 EXTREME: >80 km/h - Structure damage risk!</div>", unsafe_allow_html=True)
                st.write("• Use hurricane-rated mounting")
                st.write("• Reduce tilt to <15°")
            elif wind > 50:
                st.warning(f"🟠 HIGH: {wind:.0f} km/h - Cross bracing required")
            else:
                st.markdown(f"<div class='safe-alert'>🟢 SAFE: {wind:.1f} km/h - Wind OK</div>", unsafe_allow_html=True)
        st.info("💡 Enable Live Weather in sidebar for 7-day forecast & map.")
 
# Tab 11: Structure
with tabs[11]:
    st.markdown("<span class='info-label'>STRUCTURE & MATERIAL SPEC</span>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='feature-box'><b>Type:</b><br>{struct['type']}<br><b>Max Tilt:</b> {struct['tilt_max']}°<br><b>Wind Zone:</b> {wind_zone}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='feature-box'><b>Material:</b><br>{struct['material']}<br><b>Clamp:</b><br>{struct['clamp']}</div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='feature-box'><b>Foundation:</b><br>{struct['foundation']}<br><b>Wind Load:</b> {wind_force:.1f} kN</div>", unsafe_allow_html=True)
    if tilt > struct['tilt_max']:
        st.error(f"⚠️ WARNING: Tilt {tilt}° exceeds max {struct['tilt_max']}° for {wind_zone} zone!")
 
# Tab 12: Protection
with tabs[12]:
    st.markdown("<span class='info-label'>⚙️ PROTECTION SYSTEMS</span>", unsafe_allow_html=True)
    st.metric("Lightning Rod Height", f"{rod_height:.1f} m")
    st.metric("Protection Radius", f"{protection_radius} m")
    st.metric("Structure Cost Est.", f"{structure_cost + lightning_cost:,.0f} {c_curr}")
    if wind_safe:
        st.success("✅ Structure wind load within safe limits")
    else:
        st.error(f"⚠️ Wind load {wind_force:.1f} kN exceeds safe limit! Upgrade structure.")
 
# Tab 13: Physics Engine (App 2 Advanced)
with tabs[13]:
    st.markdown("<span class='info-label'>📡 ADVANCED PHYSICS ENGINE</span>", unsafe_allow_html=True)
 
    if live_weather_toggle:
        st.subheader("🌐 Live Telemetry Mode")
        col_la, col_lo = st.columns(2)
        with col_la:
            lat_in = st.text_input("GPS Latitude", str(round(lat, 4)))
        with col_lo:
            lon_in = st.text_input("GPS Longitude", str(round(lon, 4)))
        sim_data_df = fetch_meteorological_data(float(lat_in), float(lon_in))
        mode_tag = "live"
        if sim_data_df is None:
            st.warning("API unavailable. Using fallback data.")
            sim_data_df = pd.DataFrame({
                "Hour": list(range(24)) * 3,
                "Temperature": [temp_ambient] * 72,
                "Wind_Speed": [wind / 3.6] * 72,
                "Cloud_Cover": [cloud_pct] * 72,
            })
    else:
        st.subheader("🗺️ Country Database Mode")
        sim_hours = list(range(24))
        mock_temps = [temp_ambient - 4 + 8 * np.sin(np.pi * (h - 6) / 12) if 6 <= h <= 18 else temp_ambient - 4 for h in sim_hours]
        sim_data_df = pd.DataFrame({
            "Hour": sim_hours,
            "Temperature": mock_temps,
            "Wind_Speed": [wind / 3.6] * 24,
            "Cloud_Cover": [cloud_pct] * 24,
        })
        mode_tag = "country"
 
    output_metrics = []
    for _, row in sim_data_df.iterrows():
        calc = model_solar_physics(row["Temperature"], row["Wind_Speed"], row["Cloud_Cover"],
                                   int(row["Hour"]), adv_cfg, scenario_mode=mode_tag)
        output_metrics.append(calc)
 
    calc_res_df = pd.DataFrame(output_metrics)
    sim_data_df = sim_data_df.copy()
    sim_data_df["Incident_Irradiance"] = calc_res_df["Irradiance"].values
    sim_data_df["Cell_Temperature"] = calc_res_df["Cell_Temp"].values
    sim_data_df["Hourly_Yield_kW"] = calc_res_df["Power_kW"].values
 
    total_adv_gen = sim_data_df["Hourly_Yield_kW"].sum() if mode_tag == "country" else (sim_data_df["Hourly_Yield_kW"].sum() / 3.0)
 
    m1, m2, m3 = st.columns(3)
    m1.metric("Physics Engine Daily Yield", f"{total_adv_gen:.2f} kWh")
    m2.metric("Peak Cell Temp", f"{sim_data_df['Cell_Temperature'].max():.1f} °C")
    m3.metric("Avg Irradiance", f"{sim_data_df['Incident_Irradiance'].mean():.1f} W/m²")
 
    st.line_chart(sim_data_df.set_index("Hour")[["Hourly_Yield_kW", "Incident_Irradiance"]].rename(
        columns={"Hourly_Yield_kW": "Power kW", "Incident_Irradiance": "Irradiance W/m²"}))
    st.dataframe(sim_data_df, use_container_width=True)
 
# Tab 14: Storage Matrix
with tabs[14]:
    st.markdown("<span class='info-label'>🔋 BATTERY STORAGE MATRIX</span>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    b1.metric("Total Storage", f"{b_cap:.2f} kWh")
    b2.metric("Usable Capacity", f"{usable_battery_storage_kwh:.2f} kWh", f"DoD: {dod}%")
    b3.metric("Autonomy Backup", f"{hours_of_autonomy:.1f} Hours")
 
    st.divider()
    st.markdown("**Battery Chemistry Comparison**")
    bat_compare_df = pd.DataFrame([
        {"Type": k, "DoD %": v["default_dod"], "Efficiency %": v["efficiency"], "Life Years": v["life_years"]}
        for k, v in BATTERY_TYPES.items()
    ])
    st.dataframe(bat_compare_df, use_container_width=True)
 
# Tab 15: Export
with tabs[15]:
    st.markdown("<span class='info-label'>📤 EXPORT REPORT - CSV + PDF</span>", unsafe_allow_html=True)
    enable_export = st.checkbox("📄 Enable PDF Export", value=False)
 
    df_export = pd.DataFrame({
        "Hour": list(hours),
        "Generation_kW": [round(x, 3) for x in gen_24],
        "Load_kW": [round(x, 3) for x in load_24],
        "Export_kW": [round(x, 3) for x in export_24],
        "Import_kW": [round(x, 3) for x in import_24],
        "Battery_SOC_kWh": [round(x, 3) for x in soc],
        "Battery_%": [round((x / b_cap) * 100, 1) if has_batt and b_cap > 0 else 0 for x in soc],
    })
    csv = df_export.to_csv(index=False).encode('utf-8')
 
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 Download CSV", csv,
                           file_name=f"SolarX_{country}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                           mime="text/csv")
    with col2:
        if enable_export:
            report_data = {
                "Country": country, "Location": location_name,
                "System Size": f"{sys_size:.2f} kWp",
                "Daily Gen": f"{sum(gen_24):.2f} kWh",
                "Wind Speed": f"{wind:.1f} km/h",
                "Wind Force": f"{wind_force:.1f} kN",
                "Cable Size": f"{cable_size} mm²",
                "VD Loss": f"{vd_percent:.2f}%",
                "Total Cost": f"{net_cost:,.0f} {c_curr}",
                "Payback": f"{payback:.1f} Years",
                "25yr NPV": f"{npv:,.0f} {c_curr}",
                "ESG Rating": esg_rating,
            }
            pdf_data = generate_pdf_report(report_data)
            if pdf_data is not None and len(pdf_data) > 0:
                st.download_button("📄 Download PDF", pdf_data,
                                   file_name=f"SolarX_Report_{country}.pdf",
                                   mime="application/pdf")
            else:
                st.info("💡 For PDF: pip install fpdf2")
 
    st.dataframe(df_export, height=350, use_container_width=True)
