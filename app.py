# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from calculator import calculate
from constants import *

st.set_page_config(page_title="AD → BTC Mining Calculator", layout="centered")

# === INPUTS ===
with st.sidebar:
    st.header("AD Plant")
    chp_mw = st.slider("CHP Size (MW)", 0.1, 5.0, 1.0, 0.1)
    load_factor = st.slider("Load Factor (%)", 80, 98, 95, 1) / 100
    roc_rtfo = st.selectbox("ROC/RTFO Status", [
        "ROC + RTFO (5% min export)", "ROC only (10% min export)", "None (0% min export)"
    ])
    eii = st.selectbox("EII Exempt?", ["Yes (0 CCL)", "No"])

    st.header("Mining Setup")
    max_mining = min(chp_mw * 0.95, 5.0)
    mining_mw = st.slider("Mining Power (MW)", 0.05, chp_mw * 1.1, min(1.0, max_mining), 0.05)
    miner_model = st.selectbox("Miner Model", list(MINER_SPECS.keys()))

    st.caption("Cooling: Immersion using digestate heat → **£0 cost**")

# === CALCULATE ===
results = calculate(chp_mw, load_factor, roc_rtfo, eii, miner_model, mining_mw)

# === UI ===
st.title("AD Plant → Bitcoin Mining Calculator")
st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')} • BTC £{results['btc_price']:,} • {results['hashrate']} EH/s")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("BTC / year", f"{results['total_btc']:.4f}", f"£{results['revenue_btc']:,.0f}")
with col2:
    st.metric("£ / MWh net", f"£{results['net_per_mwh']:.1f}")
with col3:
    st.metric("Payback", f"{results['payback_months']:.0f} months")

# === Chart ===
df_chart = pd.DataFrame({
    "Category": [
        f"Grid Savings (£{results['grid_savings']:,.0f})",
        f"Capex + Opex (£{results['capex_annuity'] + results['opex_annual']:,.0f})",
        f"BTC Revenue (£{results['revenue_btc']:,.0f})"
    ],
    "GBP": [
        results['grid_savings'],
        results['capex_annuity'] + results['opex_annual'],
        results['revenue_btc']
    ]
})
fig = px.pie(df_chart, values="GBP", names="Category", hole=0.4,
             color_discrete_sequence=["#2a9d8f", "#e76f51", "#f4a261"],
             title="Year 1 Revenue Breakdown")
fig.update_traces(textinfo="percent", textposition="inside")
fig.update_layout(height=400, legend=dict(orientation="h", yanchor="bottom", y=-0.2))
st.plotly_chart(fig, use_container_width=True)

# === Transparency ===
with st.expander("Debugger: temporary"):
    st.write(f"**total_btc**: {results['total_btc']:,.6f} | **revenue_btc**: £{results['revenue_btc']:,.0f}")
    st.write(f"**grid_savings**: £{results['grid_savings']:,.0f} | **capex_annuityc**: £{results['capex_annuity']:,.0f}")    
    st.write(f"**opex_annual**: £{results['opex_annual']:,.0f}")
    st.write(f"**£ / MWh net**", f"£{results['net_per_mwh']:.1f} | **Payback**: {results['payback_months']:.0f} months")

# In Metrics
with st.expander("Detailed Breakdown"):
    st.write(f"**Annual MWh**: {results['annual_mwh']:,.0f} | **Max Mining MWh**: {results['max_mining_mwh']:,.0f}")
    st.write(f"**BTC Revenue**: £{results['revenue_btc']:,.0f} ({results['total_btc']:.6f} BTC @ £{results['btc_price']:,.0f})")    
    st.write(f"**Grid savings**: £{results['grid_savings']:,.0f} (@ £72/MWh if EII)")
    st.write(f"**Capex annuity**: £{results['capex_annuity']:,.0f} | **Opex**: £{results['opex_annual']:,.0f}")

with st.expander("5 Uncontrollable External Variables"):
    st.markdown("<small>These drive 98% of BTC revenue uncertainty.</small>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("1. BTC Price", f"£{results['btc_price']:,}")
        st.metric("2. Network Hashrate", f"{results['hashrate']:,} EH/s")
        st.metric("3. Block Reward", f"{BLOCK_REWARD} BTC")
    with col2:
        st.metric("4. Blocks per Day", f"{BLOCKS_PER_DAY}")
        st.metric("5. Pool Fee", f"{POOL_FEE_PCT:.0%}")
    st.caption("Next halving: ~April 2028 → reward → 1.5625 BTC")

st.caption("Built for AD operators • Share: ad-bmc.streamlit.app")