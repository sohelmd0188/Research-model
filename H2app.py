# H2app.py — Updated Design A (MWh units, default Solar=80 MWh)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="H2 Dashboard (MWh)")

# Sidebar settings
st.sidebar.title("Model settings (units: MWh, Tk -> USD conversion)")
# Energy unit note: all energy inputs/outputs use MWh in UI; internal conversions if needed use MWh.
default_solar_mwh = st.sidebar.number_input("Default Solar (MWh/month)", value=80.0, step=1.0)
exchange_rate = st.sidebar.number_input("BDT per USD (exchange rate)", value=114.0)
oxygen_price_tk_per_kg = st.sidebar.number_input("O₂ price (Tk/kg)", value=10.0)
h2_sale_price_tk_per_kg = st.sidebar.number_input("H₂ sale price (Tk/kg)", value=0.0)
grid_price_tk_per_mwh = st.sidebar.number_input("Grid price (Tk/MWh)", value=10560.0)  # default 10.56 Tk/kWh -> 10560 Tk/MWh
grid_emission_kgCO2_per_mwh = st.sidebar.number_input("Grid emission (kgCO₂/MWh)", value=710.0)  # 0.71 kg/kWh -> 710 kg/MWh
diesel_l_per_month = st.sidebar.number_input("Diesel (L/month)", value=42000.0)
diesel_co2_kg_per_l = st.sidebar.number_input("Diesel CO₂ (kg/L)", value=2.68)
diesel_price_tk_per_l = st.sidebar.number_input("Diesel price (Tk/L)", value=114.0)

st.sidebar.markdown("---")
st.sidebar.markdown("Operational sliders")
electrolyzer_eff = st.sidebar.slider("Electrolyzer efficiency (%)", 50, 90, 80) / 100.0
h2_lhv_kwh_per_kg = st.sidebar.number_input("H₂ LHV (kWh/kg)", value=33.33)
h2_lhv_mwh_per_kg = h2_lhv_kwh_per_kg / 1000.0  # convert to MWh/kg
fuelcell_eff = st.sidebar.slider("Fuel cell efficiency (%)", 30, 70, 50) / 100.0
fraction_h2_to_fuelcell = st.sidebar.slider("Fraction H₂ -> Fuel cell (%)", 0, 100, 30) / 100.0
fraction_h2_to_refuel = st.sidebar.slider("Fraction H₂ -> Refuel (%)", 0, 100, 70) / 100.0
initial_h2_storage_kg = st.sidebar.number_input("Initial H₂ stored (kg)", value=700.0)

st.sidebar.markdown("---")
st.sidebar.markdown("Upload CSV (optional): columns 'month','solar_mwh','demand_mwh' (12 rows)")
uploaded = st.sidebar.file_uploader("Monthly profile CSV", type=["csv"])

# Load data (demo if not uploaded)
def demo_df():
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    # Example demand in MWh (demo values)
    demand_mwh = np.array([31.5,39.0,64.5,72.0,117.0,78.0,94.5,46.5,114.0,102.0,87.0,46.5])  # was kWh/1000 -> MWh
    solar_mwh = np.full(12, default_solar_mwh)
    return pd.DataFrame({"month": months, "solar_mwh": solar_mwh, "demand_mwh": demand_mwh})

if uploaded:
    df = pd.read_csv(uploaded)
    if not set(["month","solar_mwh","demand_mwh"]).issubset(df.columns):
        st.error("CSV must contain 'month','solar_mwh','demand_mwh'")
        st.stop()
    df = df[["month","solar_mwh","demand_mwh"]].copy()
else:
    df = demo_df()

# Calculations (MWh units)
df["grid_import_mwh"] = np.maximum(0, df["demand_mwh"] - df["solar_mwh"])
df["grid_export_mwh"] = np.maximum(0, df["solar_mwh"] - df["demand_mwh"])

# Electrolyzer energy allocated: assume fraction of solar used for electrolysis, and grid can supplement
solar_frac_for_electrolysis = st.sidebar.slider("Solar fraction for electrolysis (%)", 0, 100, 80) / 100.0
df["solar_alloc_electrolysis_mwh"] = df["solar_mwh"] * solar_frac_for_electrolysis
# If solar insufficient, grid supplement for electrolysis (operator decision) - simple model: electrolyzer uses solar_alloc + grid_import up to demand
df["electrolyzer_energy_mwh"] = df["solar_alloc_electrolysis_mwh"].copy()
# Optionally allow extra from grid (user can toggle)
use_grid_for_electrolysis = st.sidebar.checkbox("Allow grid supplement for electrolysis when solar insufficient", value=True)
if use_grid_for_electrolysis:
    need_mwh = (df["demand_mwh"] - df["solar_alloc_electrolysis_mwh"]).clip(lower=0)
    # use grid import to cover need (not exceeding actual grid_import)
    df["electrolyzer_energy_mwh"] = df["solar_alloc_electrolysis_mwh"] + np.minimum(need_mwh, df["grid_import_mwh"])

# Hydrogen production (kg) from electrolyzer energy:
# mH2 (kg) = Energy (MWh) / (LHV (MWh/kg) / electrolyzer_eff) = Energy / (LHV_mwh_per_kg / eta)
df["h2_kg"] = df["electrolyzer_energy_mwh"] / (h2_lhv_mwh_per_kg / electrolyzer_eff)

# Oxygen production (kg)
df["o2_kg"] = df["h2_kg"] * 8.0

# Water required (L) (approx kg to L)
df["water_l"] = df["h2_kg"] * 9.0

# Fuel cell electricity generation (MWh)
df["h2_for_fuelcell_kg"] = df["h2_kg"] * fraction_h2_to_fuelcell
df["fuelcell_elec_mwh"] = df["h2_for_fuelcell_kg"] * h2_lhv_mwh_per_kg * fuelcell_eff

# H2 to refuelling station
df["h2_to_refuel_kg"] = df["h2_kg"] * fraction_h2_to_refuel

# Storage tracking (monthly)
df["monthly_h2_input_kg"] = df["h2_kg"]
df["monthly_h2_output_kg"] = df["h2_for_fuelcell_kg"] + df["h2_to_refuel_kg"]
storage = []
s = initial_h2_storage_kg
for i,row in df.iterrows():
    s = s + row["monthly_h2_input_kg"] - row["monthly_h2_output_kg"]
    storage.append(max(0.0,s))
df["stored_h2_kg"] = storage

# CO2 calculations (kg)
df["co2_from_grid_import_kg"] = df["grid_import_mwh"] * grid_emission_kgCO2_per_mwh
df["co2_avoided_from_export_kg"] = df["grid_export_mwh"] * grid_emission_kgCO2_per_mwh
df["co2_avoided_from_diesel_kg"] = diesel_l_per_month * diesel_co2_kg_per_l / 12.0

# Financials: Tk to USD
df["o2_revenue_tk"] = df["o2_kg"] * oxygen_price_tk_per_kg
df["h2_revenue_tk"] = df["h2_to_refuel_kg"] * h2_sale_price_tk_per_kg
df["electricity_avoided_tk"] = df["fuelcell_elec_mwh"] * grid_price_tk_per_mwh
df["monthly_revenue_tk"] = df["o2_revenue_tk"] + df["h2_revenue_tk"] + df["electricity_avoided_tk"]
df["monthly_revenue_usd"] = df["monthly_revenue_tk"] / exchange_rate

# UI layout
st.title("H₂ System Live Model — Design A (MWh units)")
# Top KPIs
c1,c2,c3,c4 = st.columns(4)
with c1:
    st.metric("Solar (MWh/month)", f"{df['solar_mwh'].mean():,.1f}")
with c2:
    st.metric("Electrolyzer energy (MWh/month)", f"{df['electrolyzer_energy_mwh'].sum():,.1f}")
with c3:
    st.metric("H₂ produced (kg/month avg)", f"{df['h2_kg'].mean():,.0f}")
with c4:
    st.metric("O₂ produced (kg/month avg)", f"{df['o2_kg'].mean():,.0f}")

st.markdown("---")

# Month selector block
selected_month = st.selectbox("Select month to view details", options=df['month'].tolist())
df_month = df[df['month']==selected_month].iloc[0]

st.subheader(f"Details — {selected_month}")
colA, colB, colC = st.columns(3)
with colA:
    st.markdown("**Energy (MWh)**")
    st.write(f"Solar: {df_month['solar_mwh']:.2f} MWh")
    st.write(f"Demand: {df_month['demand_mwh']:.2f} MWh")
    st.write(f"Grid Import: {df_month['grid_import_mwh']:.2f} MWh")
    st.write(f"Grid Export: {df_month['grid_export_mwh']:.2f} MWh")
with colB:
    st.markdown("**Production & Storage**")
    st.write(f"H₂ produced: {df_month['h2_kg']:.0f} kg")
    st.write(f"O₂ produced: {df_month['o2_kg']:.0f} kg")
    st.write(f"Water required: {df_month['water_l']:.0f} L")
    st.write(f"Stored H₂ (end month): {df_month['stored_h2_kg']:.0f} kg")
with colC:
    st.markdown("**CO₂ & Financials**")
    st.write(f"CO₂ from grid import: {df_month['co2_from_grid_import_kg']:.0f} kg")
    st.write(f"CO₂ avoided from export: {df_month['co2_avoided_from_export_kg']:.0f} kg")
    st.write(f"O₂ revenue: {df_month['o2_revenue_tk']:.0f} Tk ({df_month['o2_revenue_tk']/exchange_rate:.2f} USD)")
    st.write(f"H₂ sale revenue: {df_month['h2_revenue_tk']:.0f} Tk ({df_month['h2_revenue_tk']/exchange_rate:.2f} USD)")
    st.write(f"Electricity avoided revenue: {df_month['electricity_avoided_tk']:.0f} Tk ({df_month['electricity_avoided_tk']/exchange_rate:.2f} USD)")

st.markdown("---")

left, right = st.columns((2,1))
with left:
    st.subheader("Monthly overview charts")
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Solar (MWh)", x=df["month"], y=df["solar_mwh"], marker_color="orange"))
    fig.add_trace(go.Bar(name="Demand (MWh)", x=df["month"], y=df["demand_mwh"], marker_color="grey"))
    fig.add_trace(go.Bar(name="Grid Import (MWh)", x=df["month"], y=df["grid_import_mwh"], marker_color="red"))
    fig.update_layout(barmode='group', height=420, title="Solar vs Demand vs Grid Import (MWh)")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("H₂ & O₂ production (monthly)")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name="H₂ (kg)", x=df["month"], y=df["h2_kg"], marker_color="green"))
    fig2.add_trace(go.Bar(name="O₂ (kg)", x=df["month"], y=df["o2_kg"], marker_color="cyan"))
    fig2.update_layout(barmode='group', height=380)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Hydrogen storage tracking")
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name="H₂ input (kg)", x=df["month"], y=df["monthly_h2_input_kg"], marker_color="lightgreen"))
    fig3.add_trace(go.Bar(name="H₂ output (kg)", x=df["month"], y=df["monthly_h2_output_kg"], marker_color="darkgreen"))
    fig3.add_trace(go.Scatter(name="Stored H₂ (kg)", x=df["month"], y=df["stored_h2_kg"], mode="lines+markers", line=dict(color="green")))
    fig3.update_layout(height=380)
    st.plotly_chart(fig3, use_container_width=True)

with right:
    st.subheader("Financial summary (annual projections)")
    total_o2_rev_usd = df["o2_revenue_tk"].sum() / exchange_rate
    total_h2_rev_usd = df["h2_revenue_tk"].sum() / exchange_rate
    total_elec_avoided_usd = df["electricity_avoided_tk"].sum() / exchange_rate
    st.write(f"Total O₂ revenue (USD/yr): {total_o2_rev_usd:,.2f}")
    st.write(f"Total H₂ sale revenue (USD/yr): {total_h2_rev_usd:,.2f}")
    st.write(f"Total electricity avoided (USD/yr): {total_elec_avoided_usd:,.2f}")
    st.markdown("---")
    st.subheader("CO₂ (annual)")
    st.write(f"Total CO₂ from grid imports (tonnes/yr): {df['co2_from_grid_import_kg'].sum()/1000:,.2f}")
    st.write(f"Total CO₂ avoided from exports (tonnes/yr): {df['co2_avoided_from_export_kg'].sum()/1000:,.2f}")

st.markdown("---")
st.subheader("Monthly data table (MWh / kg / Tk)")
st.dataframe(df.style.format({
    "solar_mwh":"{:.1f}","demand_mwh":"{:.1f}","grid_import_mwh":"{:.1f}","grid_export_mwh":"{:.1f}",
    "electrolyzer_energy_mwh":"{:.1f}","h2_kg":"{:.0f}","o2_kg":"{:.0f}","water_l":"{:.0f}",
    "fuelcell_elec_mwh":"{:.2f}","stored_h2_kg":"{:.0f}","o2_revenue_tk":"{:.0f}","monthly_revenue_tk":"{:.0f}"
}))
