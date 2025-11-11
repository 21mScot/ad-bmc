# app.py
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# === BTC NETWORK CONSTANTS (Update at halving) ===
BLOCKS_PER_DAY   = 144          # ~10-min blocks
BLOCK_REWARD     = 3.125        # Current subsidy (post-2024)
POOL_FEE_PCT     = 0.01         # 1% pool fee
DAYS_PER_YEAR    = 365.25
COINGECKO_TIMEOUT = 5           # seconds
COINGEKO_URL     = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=gbp"
BLOCKCHAIN_TIMEOUT = 10        # seconds
BLOCKCHAIN_URL   = "https://api.blockchain.info/charts/hash-rate?format=json&timespan=30days"

st.set_page_config(page_title="AD → BTC Mining Calculator", layout="centered")

# === CONFIG ===
MINER_SPECS = {
    "Whatsminer M53S++ Hydro (22 J/TH)": {"j_th": 22, "cost_per_mw_gbp": 1_800_000},
    "Whatsminer M50S++ (24 J/TH)": {"j_th": 24, "cost_per_mw_gbp": 1_600_000},
    "Antminer S21 XP Hydro (11 J/TH)": {"j_th": 11, "cost_per_mw_gbp": 2_800_000},
}

# === LIVE DATA ===
@st.cache_data(ttl=60)
def fetch_market_data():
    try:
        btc = requests.get(COINGEKO_URL,
            timeout=COINGECKO_TIMEOUT
        ).json()["bitcoin"]["gbp"]
        hr_res = requests.get(BLOCKCHAIN_URL,
            timeout=BLOCKCHAIN_TIMEOUT
        ).json()
        values = [p["y"] for p in hr_res["values"] if p["y"] is not None]
        if not values:
            raise ValueError("No hashrate data")
        hashrate_eh = round(sum(values) / len(values) / 1e18, 0)
        return int(btc), int(hashrate_eh)
    except Exception as e:
        st.warning(f"Live data failed: {e}. Using Nov 2025 defaults.")
        return 80000, 1111

BTC_PRICE, HASHRATE = fetch_market_data()

# === Safety guard ===
if HASHRATE == 0:
    st.warning("Hashrate is zero. Forcing fallback to 1,111 EH/s.")
    HASHRATE = 1111

# === BTC YIELD (CORRECT) ===
total_btc_per_year = BLOCKS_PER_DAY * DAYS_PER_YEAR * BLOCK_REWARD
network_eh = HASHRATE
network_th = network_eh * 1_000_000  # 1 EH/s = 1e6 TH/s


# === INPUTS ===
with st.sidebar:
    st.header("AD Plant")
    chp_mw = st.slider("CHP Size (MW)", 0.1, 5.0, 1.0, 0.1)
    load_factor = st.slider("Load Factor (%)", 80, 98, 95, 1) / 100
    roc_rtfo = st.selectbox(
        "ROC/RTFO Status",
        ["ROC + RTFO (5% min export)", "ROC only (10% min export)", "None (0% min export)"]
    )
    eii = st.selectbox("EII Exempt?", ["Yes (0 CCL)", "No"])

    st.header("Mining Setup")
    miner_model = st.selectbox("Miner Model", list(MINER_SPECS.keys()))
    max_mining = min(chp_mw * 0.95, 5.0)
    mining_mw = st.slider("Mining Power (MW)", 0.05, chp_mw * 1.1, min(1.0, max_mining), 0.05)

    st.caption("Cooling: Immersion using digestate heat → **£0 cost**")

# === CALCULATIONS ===
j_th = MINER_SPECS[miner_model]["j_th"]
cost_per_mw = MINER_SPECS[miner_model]["cost_per_mw_gbp"]

annual_mwh = chp_mw * 8760 * load_factor
min_export_pct = 0.05 if "ROC + RTFO" in roc_rtfo else 0.10 if "ROC only" in roc_rtfo else 0.0
max_mining_mwh = annual_mwh * (1 - min_export_pct)
actual_mining_mwh = min(mining_mw * 8760 * 0.98, max_mining_mwh)

btc_per_th_year = total_btc_per_year / network_th

th_per_mwh = 1_000_000 / j_th
btc_per_mwh = btc_per_th_year * th_per_mwh * (1 - POOL_FEE_PCT)
total_btc = btc_per_mwh * actual_mining_mwh
revenue_btc = total_btc * BTC_PRICE

capex = mining_mw * cost_per_mw
capex_annuity = capex * 0.20
opex_annual = mining_mw * 12 * 6

grid_save_mwh = 72 if "Yes" in eii else 45
grid_savings = grid_save_mwh * actual_mining_mwh

net_revenue = revenue_btc + grid_savings - capex_annuity - opex_annual
net_per_mwh = net_revenue / actual_mining_mwh if actual_mining_mwh > 0 else 0
payback = (capex_annuity + opex_annual) / (revenue_btc + grid_savings) if (revenue_btc + grid_savings) > 0 else float('inf')

# === UI ===
st.title("AD Plant → Bitcoin Mining Calculator")
st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')} • BTC £{BTC_PRICE:,} • {HASHRATE} EH/s")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("BTC / year", f"{total_btc:.3f}", f"£{revenue_btc:,.0f}")
with col2:
    st.metric("£ / MWh net", f"£{net_per_mwh:,.1f}")
with col3:
    st.metric("Payback", f"{payback:.1f} yr")

df_chart = pd.DataFrame({
    "Category": ["BTC Revenue", "Grid Savings", "Capex + Opex (Yr1)"],
    "GBP": [revenue_btc, grid_savings, capex_annuity + opex_annual]
})
fig = px.pie(df_chart, values="GBP", names="Category", hole=0.4,
             color_discrete_sequence=["#f4a261", "#2a9d8f", "#e76f51"],
             title="Year 1 Revenue Breakdown")
fig.update_layout(height=400, legend=dict(orientation="h", yanchor="bottom", y=-0.1))
st.plotly_chart(fig, use_container_width=True)

with st.expander("Detailed Breakdown"):
    st.write(f"**Annual MWh**: {annual_mwh:,.0f} | **Max Mining MWh**: {max_mining_mwh:,.0f}")
    st.write(f"**Grid savings**: £{grid_savings:,.0f} (@ £{grid_save_mwh}/MWh)")
    st.write(f"**Capex annuity**: £{capex_annuity:,.0f} | **Opex**: £{opex_annual:,.0f}")
    
    st.caption("All values update every 60s or use Nov 2025 defaults on failure")


with st.expander("Bitcoin mining - fixed inputs"):
    col_a, col_b = st.columns(2)
    with col_a:
         st.write(f"**1. Blocks per day**", f"{BLOCKS_PER_DAY}")
    with col_b:
        st.write(f"**2. Target time per block**", f"10 minutes")
    st.caption("However, these can vary slightly due to network conditions.")


with st.expander("Bitcoin mining - external variables, uncontrollable"):
    st.markdown("""
    <small>These drive 98% of BTC revenue uncertainty. We pull live data where possible.</small>
    """, unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.write(f"**1. BTC Price**", f"£{BTC_PRICE:,}")
        st.write(f"**2. Network Hashrate**", f"{HASHRATE:,} EH/s")
        st.write(f"**3. Network difficulty**", f"??? BTC")
    with col_b:
        st.write(f"**3. Block Subsidy**", f"{BLOCK_REWARD} BTC")
        st.write(f"**Pool hard coded, Block Reward not subsidy & fees**", f"{j_th}")
    st.caption("All values update every 60s or use Nov 2025 defaults on failure")

with st.expander("Bitcoin mining - variables we can control"):
    col1, col2 = st.columns(2)
    with col1:
        st.metric("first", f"£{BTC_PRICE:,}", help="Live from CoinGecko")
        st.metric("Pool Fee", f"{POOL_FEE_PCT:.0%}")
    with col2:
        st.metric("second", f"{BLOCKS_PER_DAY}", help="~144 (10-min target)")

st.caption("Built for AD operators • Share: ad-bmc.streamlit.app")