# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from calculator import calculate
from constants import *  # uses MINER_SPECS, BLOCKS_PER_DAY, BLOCK_REWARD, POOL_FEE_PCT, etc.
from asics_data import (
    get_dropdown_options_from_constants,
    ensure_today_csv,
    get_specs_by_id,   # make sure this exists in asics_data.py
)

st.set_page_config(page_title="AD → BTC Mining Calculator", layout="centered")

st.subheader("ASIC picker")

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Refresh list"):
        st.cache_data.clear()
        ensure_today_csv()   # will fetch if today's CSV is missing
        st.success("Refreshed")

@st.cache_data(ttl=3600)
def _opts():
    return get_dropdown_options_from_constants()

opts = _opts()
labels = [l for (l, _) in opts]
values = {l: v for (l, v) in opts}

choice = st.selectbox("Choose a miner", labels or ["No options"], index=0)
selected_id = values.get(choice)
st.caption(f"Selected id: `{selected_id}`")

# === Use dropdown miner to drive the calculator ===
dynamic_key = "DYNAMIC"
selected_specs = get_specs_by_id(selected_id) if selected_id else None

def _baseline_spec():
    """Pick the first spec in MINER_SPECS as a baseline for any required keys."""
    try:
        first_key = next(iter(MINER_SPECS.keys()))
        return dict(MINER_SPECS[first_key])
    except Exception:
        return {}

def _put_dynamic_spec():
    """Inject a DYNAMIC miner that matches calculator's expected keys, merged with a baseline."""
    if not selected_specs:
        return False
    ths = selected_specs.get("hashrate_ths")
    watts = selected_specs.get("power_w")
    j_th = selected_specs.get("efficiency_j_th")
    if not (ths and watts):
        return False

    base = _baseline_spec()

    # Start from baseline so all cost/finance fields exist, then override core hardware fields
    dynamic = dict(base)
    dynamic.update({
        "name": f"{selected_specs.get('brand','')} {selected_specs.get('name','')}".strip(),
        # Calculator-expected keys:
        "j_th": j_th,          # efficiency (J/TH)
        "th_s": ths,           # hashrate TH/s
        "watts": watts,        # power W
        # Friendly duplicate keys for UI/use elsewhere:
        "efficiency_j_th": j_th,
        "hashrate_ths": ths,
        "power_w": watts,
    })

    # Ensure any absolutely required finance fields exist (fallbacks if baseline lacked them)
    dynamic.setdefault("cost_per_mw_gbp", base.get("cost_per_mw_gbp", 0))
    dynamic.setdefault("capex_per_mw_gbp", base.get("capex_per_mw_gbp", 0))
    dynamic.setdefault("opex_per_mw_gbp", base.get("opex_per_mw_gbp", 0))

    MINER_SPECS[dynamic_key] = dynamic
    return True

if not _put_dynamic_spec():
    # If dropdown lookup failed, fall back to the first static spec
    dynamic_key = next(iter(MINER_SPECS.keys()))

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

    # Toggle: use dropdown-selected miner or legacy list
    use_dropdown = st.toggle("Use dropdown miner", value=True)
    if use_dropdown and dynamic_key in MINER_SPECS:
        miner_model = dynamic_key
        st.caption(f"Using dropdown miner: {MINER_SPECS[dynamic_key].get('name','(unknown)')}")
    else:
        miner_model = st.selectbox("Miner Model (legacy list)", list(MINER_SPECS.keys()), index=0)

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
fig = px.pie(
    df_chart, values="GBP", names="Category", hole=0.4,
    color_discrete_sequence=["#2a9d8f", "#e76f51", "#f4a261"],
    title="Year 1 Revenue Breakdown"
)
fig.update_traces(textinfo="percent", textposition="inside")
fig.update_layout(height=400, legend=dict(orientation="h", yanchor="bottom", y=-0.2))
st.plotly_chart(fig, use_container_width=True)

# === Transparency ===
with st.expander("Detailed Breakdown"):
    st.write(f"**Annual MWh**: {results['annual_mwh']:,.0f} | **Max Mining MWh**: {results['max_mining_mwh']:,.0f}")
    st.write(f"**BTC Revenue**: £{results['revenue_btc']:,.0f} ({results['total_btc']:.6f} BTC @ £{results['btc_price']:,.0f})")
    st.write(f"**Grid savings**: £{results['grid_savings']:,.0f} (@ £72/MWh if EII)")
    st.write(f"**Capex annuity**: £{results['capex_annuity']:,.0f} | **Opex**: £{results['opex_annual']:,.0f}")

with st.expander("Bitcoin mining: full transparency"):
    st.markdown("<small>These drive 98% of BTC revenue uncertainty.</small>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    # 1. Network data
    with col1:
        st.write("**<u>1. Network data</u>**", unsafe_allow_html=True)
        st.write("External variables")
        st.write("**a) Network Hashrate (Hn)**")
        st.write(f"{results['hashrate']:,} EH/s live")
        st.write("**b) Blocks / day**")
        st.write(f"{BLOCKS_PER_DAY}")
        st.write("**c) Block Subsidy**")
        st.write(f"{BLOCK_REWARD} BTC est.")
        st.write("**d) Pool fee (assumed)**")
        st.write(f"{POOL_FEE_PCT:.0%}")
        st.write("**e) BTC price**")
        st.write(f"£{results['btc_price']:,}")

    # 2. Hardware data
    with col2:
        st.write("**<u>2. Hardware data</u>**", unsafe_allow_html=True)
        st.write("Miner specific")
        hw = MINER_SPECS.get(miner_model, {})
        ths = hw.get("th_s", hw.get("hashrate_ths", "n/a"))
        watts = hw.get("watts", hw.get("power_w", "n/a"))
        jth = hw.get("j_th", hw.get("efficiency_j_th", "n/a"))
        st.write("**a) Miner hashrate (Hm)**")
        st.write(f"{ths} TH/s")
        st.write("**b) Miner power**")
        st.write(f"{watts} W")
        st.write("**c) Miner efficiency**")
        st.write(f"{jth} J/TH")

    # 3. Site specific inputs
    with col3:
        st.write("**<u>3. Site specific inputs</u>**", unsafe_allow_html=True)
        st.write("Electricity & overheads")
        st.write("**a) Power capacity**")
        st.write(f"{mining_mw} MW")
        st.write("**b) Electricity cost (Ce)**")
        st.write("Model input (site-specific)")
        st.write("**c) Cooling (Cc)**")
        st.write("£0 using digestate heat")
        st.write("**d) Maintenance (Cm)**")
        st.write("Hydro, typically <1% failure")
        st.write("**e) Number of miners**")
        st.write("Derived: site MW / miner power")

    st.caption("**<u>4. Economics</u>**", unsafe_allow_html=True)
    st.markdown("<small>These drive 98% of BTC revenue uncertainty.</small>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.write("1. BTC Price", f"£{results['btc_price']:,}")
        st.write("2. Network Hashrate", f"{results['hashrate']:,} EH/s")
        st.write("3. Block Reward", f"{BLOCK_REWARD} BTC")
    st.caption("Next halving: ~April 2028 → reward → 1.5625 BTC")

    st.caption("Calculations")
    st.caption("Notes:")
    st.caption("Block reward = BLOCK_SUBSIDY + TX_FEE; TX_FEE not included in this model yet.")
    st.write("1. Miner specific calculations")
    st.write("daily_revenue_btc = Hm/Hn * blocks_per_day * block_reward")
    st.write("daily_revenue = daily_revenue_btc * btc_price")
    st.write("daily_opex = ((W * 24)/1000) * Ce + Cc + Cm")
    st.write("Daily profit = daily_revenue - daily_opex")

st.caption("Built for AD operators • Share: ad-bmc.streamlit.app")
