import streamlit as st

# Page Configuration
st.set_page_config(page_title="Solar Estimator Pro", layout="centered")

# App Header
st.title("☀️ Solar Energy & Savings Estimator")
st.markdown("Is tool ke zariye aap apne solar setup ki daily generation aur monthly bachat calculate kar sakte hain.")

st.divider()

# Sidebar for Inputs
st.sidebar.header("System Specifications")
num_panels = st.sidebar.number_input("Total Number of Panels", min_value=1, value=10)
panel_wattage = st.sidebar.number_input("Panel Capacity (Watts)", min_value=100, value=545, step=5)
sun_hours = st.sidebar.slider("Daily Sunlight Hours (Average)", 1.0, 12.0, 5.5)
unit_rate = st.sidebar.number_input("Electricity Rate (PKR per Unit)", min_value=1, value=50)

# Efficiency Selection
efficiency = st.sidebar.selectbox("Panel Condition / Efficiency", 
                                 options=[0.85, 0.75, 0.65], 
                                 format_func=lambda x: "High (Clean)" if x==0.85 else ("Medium" if x==0.75 else "Low (Dusty)"))

# Calculations Logic
total_kw = (num_panels * panel_wattage) / 1000  # Converting W to kW
daily_units = total_kw * sun_hours * efficiency
monthly_units = daily_units * 30
monthly_savings = monthly_units * unit_rate

# Displaying Results in Columns
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("System Size", f"{total_kw:.2f} kW")

with col2:
    st.metric("Daily Units", f"{daily_units:.2f} kWh")

with col3:
    st.metric("Monthly Units", f"{monthly_units:.1f} kWh")

st.divider()

# Savings Section
st.subheader("💰 Financial Estimation")
st.info(f"Aapka system mahana takreeban **{monthly_savings:,.0f} PKR** ki bachat kar sakta hai.")

# Simple Bar Chart for Visuals
chart_data = {
    "Estimated Generation": monthly_units,
    "Standard Consumption": 500  # Example baseline
}
st.bar_chart(chart_data)

st.caption("Note: Ye calculations standard losses aur average efficiency par mabni hain.")
