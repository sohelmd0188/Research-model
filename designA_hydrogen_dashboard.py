# H2app.py — Design A Streamlit Dashboard for Solar-Hydrogen System
# This app is the same as the designA_hydrogen_dashboard implementation.
# Run with: streamlit run H2app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Design A — Hydrogen Dashboard (IIUC)")

st.sidebar.title("Model settings & paper defaults")

h2_LHV_kwh_per_kg = st.sidebar.number_input("H₂ LHV (kWh/kg)", value=33.33, format="%.3f")
electrolyzer_eta = st.sidebar.slider("Electrolyzer efficiency (η)", 50, 90, 80) / 100.0
electrolyzer_kwh_per_kg = h2_LHV_kwh_per_kg / electrolyzer_eta
fuelcell_eff = st.sidebar.slider("Fuel cell efficiency (η_fc %)", 30, 70, 50) / 100.0
h2_hot_monthly = st.sidebar.number_input("H₂ (hot season kg/month)", value=18000.0)
h2_cold_monthly = st.sidebar.number_input("H₂ (cold season kg/month)", value=15000.0)
h2_annual_avg_monthly = st.sidebar.number_input("H₂ (annual average kg/month)", value=17400.0)
solar_net_monthly_default = st.sidebar.number_input("Solar (net kWh/month default)", value=750000.0, step=1000.0)
capex_usd = st.sidebar.number_input("CAPEX (USD)", value=16000000.0, step=1000.0)
exchange_rate = st.sidebar.number_input("BDT per USD", value=114.0)
oxygen_price_tk_per_kg = st.sidebar.number_input("O₂ price (Tk/kg)", value=10.0)
grid_emission_kgCO2_per_kwh = st.sidebar.number_input("Grid emission (kgCO₂/kWh)", value=0.71)
diesel_l_per_month = st.sidebar.number_input("Diesel (L/month)", value=42000.0)
diesel_co2_kg_per_l = st.sidebar.number_input("Diesel CO₂ (kg/L)", value=2.68)
grid_price_tk_per_kwh = st.sidebar.number_input("Grid price (Tk/kWh) - for savings calc", value=10.56)
opex_usd_per_month = st.sidebar.number_input("System OPEX (USD/month)", value=598.29)
st.sidebar.markdown('---')
st.sidebar.markdown('Operational sliders')
fraction_h2_to_fuelcell = st.sidebar.slider("Fraction of H₂ for fuel cell (%)", 0, 100, 30) / 100.0
fraction_h2_to_refuel = st.sidebar.slider("Fraction of H₂ to refuelling (%)", 0, 100, 70) / 100.0
initial_h2_storage_kg = st.sidebar.number_input("Initial stored H₂ (kg)", value=700.0)
st.sidebar.markdown('---')
st.sidebar.markdown("Upload monthly CSV (optional): columns 'month','solar_kwh','demand_kwh' (12 rows)")
uploaded = st.sidebar.file_uploader("Monthly profile CSV", type=["csv"])

def demo_monthly_df():
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    demand = np.array([31500,39000,64500,72000,117000,78000,94500,46500,114000,102000,87000,46500])
    solar_monthly = np.full(12, solar_net_monthly_default)
    df = pd.DataFrame({"month": months, "solar_kwh": solar_monthly, "demand_kwh": demand})
    return df

if uploaded:
    df = pd.read_csv(uploaded)
    if not set(["month","solar_kwh","demand_kwh"]).issubset(df.columns):
        st.error("CSV must contain 'month','solar_kwh','demand_kwh' columns.")
        st.stop()
    df = df[["month","solar_kwh","demand_kwh"]].copy()
else:
    df = demo_monthly_df()

df["grid_import_kwh"] = np.maximum(0, df["demand_kwh"] - df["solar_kwh"])
df["grid_export_kwh"] = np.maximum(0, df["solar_kwh"] - df["demand_kwh"])
hot_months = ["Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov"]
df["season"] = df["month"].apply(lambda x: "Hot" if x in hot_months else "Cold")
df["mH2_paper_kg"] = df["season"].apply(lambda s: h2_hot_monthly if s=="Hot" else h2_cold_monthly)
solar_fraction_for_electrolysis = st.sidebar.slider("Fraction of solar used for electrolysis (%)", 0, 100, 80) / 100.0
df["solar_alloc_for_electrolysis_kwh"] = df["solar_kwh"] * solar_fraction_for_electrolysis
df["mH2_from_energy_kg"] = df["solar_alloc_for_electrolysis_kwh"] / electrolyzer_kwh_per_kg
df["mH2_kg"] = df["mH2_paper_kg"]
df["mO2_kg"] = df["mH2_kg"] * 8.0
df["water_kg"] = df["mH2_kg"] * 9.0
df["water_l"] = df["water_kg"]
df["co2_from_grid_import_kg"] = df["grid_import_kwh"] * grid_emission_kgCO2_per_kwh
df["co2_avoided_from_export_kg"] = df["grid_export_kwh"] * grid_emission_kgCO2_per_kwh
df["co2_avoided_from_diesel_kg"] = diesel_l_per_month * diesel_co2_kg_per_l / 12.0
df["h2_for_fuelcell_kg"] = df["mH2_kg"] * fraction_h2_to_fuelcell
df["fuelcell_elec_kwh"] = df["h2_for_fuelcell_kg"] * h2_LHV_kwh_per_kg * fuelcell_eff
df["h2_to_refuel_kg"] = df["mH2_kg"] * fraction_h2_to_refuel
df["monthly_h2_input_kg"] = df["mH2_kg"]
df["monthly_h2_output_kg"] = df["h2_for_fuelcell_kg"] + df["h2_to_refuel_kg"]
storage = []
s = initial_h2_storage_kg
for i, row in df.iterrows():
    s = s + row["monthly_h2_input_kg"] - row["monthly_h2_output_kg"]
    storage.append(max(0.0, s))
df["stored_h2_kg"] = storage
df["o2_revenue_tk"] = df["mO2_kg"] * oxygen_price_tk_per_kg
diesel_price_tk_per_l = st.sidebar.number_input("Diesel price (Tk/L)", value=114.0)
diesel_savings_tk_per_month = diesel_l_per_month * diesel_price_tk_per_l
df["electricity_avoided_tk"] = df["fuelcell_elec_kwh"] * grid_price_tk_per_kwh
h2_sale_price_tk_per_kg = st.sidebar.number_input("Potential H₂ sale price (Tk/kg)", value=0.0)
df["h2_revenue_tk"] = df["h2_to_refuel_kg"] * h2_sale_price_tk_per_kg
df["monthly_revenue_tk"] = df["o2_revenue_tk"] + df["h2_revenue_tk"] + df["electricity_avoided_tk"]
df["monthly_revenue_usd"] = df["monthly_revenue_tk"] / exchange_rate
df["monthly_net_usd"] = df["monthly_revenue_usd"] - opex_usd_per_month
df["cumulative_cashflow_usd"] = df["monthly_net_usd"].cumsum() - capex_usd

st.title("Design A — KPI Grid Dashboard for Solar-Hydrogen System (IIUC)")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Avg H₂ produced (kg/month)", f"{df['mH2_kg'].mean():,.0f}")
    st.caption("Paper seasonal numbers (hot/cold). See sidebar to change.")
with k2:
    st.metric("Avg O₂ produced (kg/month)", f"{df['mO2_kg'].mean():,.0f}", delta=f"{(df['o2_revenue_tk'].sum()/exchange_rate):,.0f} USD/yr revenue")
with k3:
    st.metric("Avg Grid Import (kWh/month)", f"{df['grid_import_kwh'].mean():,.0f}")
    st.caption("Import = demand - solar when positive.")
with k4:
    total_co2_diesel_avoided_kg = diesel_l_per_month * diesel_co2_kg_per_l
    st.metric("Annual CO₂ avoided (diesel) (tonnes/yr)", f"{total_co2_diesel_avoided_kg*12/1000:,.2f}")
    st.caption("Diesel replacement CO₂ avoided. Full monthly diesel replacement assumed by default.")
st.markdown('---')
left_col, right_col = st.columns((3,1))
with left_col:
    st.subheader("Monthly energy balance")
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Solar (kWh)", x=df["month"], y=df["solar_kwh"], marker_color="orange"))
    fig.add_trace(go.Bar(name="Demand (kWh)", x=df["month"], y=df["demand_kwh"], marker_color="grey"))
    fig.add_trace(go.Bar(name="Grid Import (kWh)", x=df["month"], y=df["grid_import_kwh"], marker_color="red"))
    fig.update_layout(barmode='group', height=420, title="Solar vs Demand vs Grid Import (monthly)")
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Hydrogen & Oxygen production (monthly)")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name="H₂ (kg)", x=df["month"], y=df["mH2_kg"], marker_color="green"))
    fig2.add_trace(go.Bar(name="O₂ (kg)", x=df["month"], y=df["mO2_kg"], marker_color="cyan"))
    fig2.update_layout(barmode='group', height=380)
    st.plotly_chart(fig2, use_container_width=True)
    st.subheader("Hydrogen storage & flows")
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name="H₂ input (kg)", x=df["month"], y=df["monthly_h2_input_kg"], marker_color="lightgreen"))
    fig3.add_trace(go.Bar(name="H₂ output (kg)", x=df["month"], y=df["monthly_h2_output_kg"], marker_color="darkgreen"))
    fig3.add_trace(go.Scatter(name="Stored H₂ (kg)", x=df["month"], y=df["stored_h2_kg"], mode="lines+markers", line=dict(color="green")))
    fig3.update_layout(height=380)
    st.plotly_chart(fig3, use_container_width=True)
with right_col:
    st.subheader("Financials & Payback")
    st.metric("CAPEX (USD)", f"{capex_usd:,.0f}")
    st.metric("Avg monthly revenue (USD)", f"{df['monthly_revenue_usd'].mean():,.0f}")
    st.metric("Cumulative cashflow (USD, last month)", f"{df['cumulative_cashflow_usd'].iloc[-1]:,.0f}")
    fig_cf = go.Figure()
    fig_cf.add_trace(go.Scatter(name="Cumulative cashflow (USD)", x=df["month"], y=df["cumulative_cashflow_usd"], mode="lines+markers"))
    fig_cf.add_hline(y=0, line_dash="dash", annotation_text="Break-even", annotation_position="bottom right")
    st.plotly_chart(fig_cf, use_container_width=True, height=300)
    st.subheader("CO₂ breakdown (monthly)")
    fig_co2 = go.Figure()
    fig_co2.add_trace(go.Bar(name="CO₂ from grid import (kg)", x=df["month"], y=df["co2_from_grid_import_kg"], marker_color="red"))
    fig_co2.add_trace(go.Bar(name="CO₂ avoided from export (kg)", x=df["month"], y=df["co2_avoided_from_export_kg"], marker_color="green"))
    fig_co2.update_layout(barmode='group', height=300)
    st.plotly_chart(fig_co2, use_container_width=True)
st.markdown('---')
st.subheader("Detailed monthly table")
st.dataframe(df[["month","season","solar_kwh","demand_kwh","grid_import_kwh","grid_export_kwh",
                 "mH2_kg","mO2_kg","water_l","h2_for_fuelcell_kg","fuelcell_elec_kwh",
                 "h2_to_refuel_kg","stored_h2_kg","o2_revenue_tk","monthly_revenue_tk","monthly_net_usd","cumulative_cashflow_usd"]]
            .style.format({
                "solar_kwh":"{:.0f}","demand_kwh":"{:.0f}","grid_import_kwh":"{:.0f}",
                "mH2_kg":"{:.0f}","mO2_kg":"{:.0f}","water_l":"{:.0f}",
                "fuelcell_elec_kwh":"{:.0f}","stored_h2_kg":"{:.0f}",
                "o2_revenue_tk":"{:.0f}","monthly_revenue_tk":"{:.0f}","monthly_net_usd":"{:.0f}","cumulative_cashflow_usd":"{:.0f}"
            }))
st.markdown('---')
st.caption("Notes: default values and formulas are taken from the uploaded paper. Change sidebar inputs to match alternative scenarios or paste your exact equations in the code where indicated.")