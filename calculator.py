# calculator.py
from constants import *

def fetch_market_data():
    import requests
    try:
        btc = requests.get(COINGECKO_URL, timeout=COINGECKO_TIMEOUT).json()["bitcoin"]["gbp"]
        hr_res = requests.get(BLOCKCHAIN_URL, timeout=BLOCKCHAIN_TIMEOUT).json()
        values = [p["y"] for p in hr_res["values"] if p["y"] is not None]
        if not values:
            raise ValueError("No hashrate data")
        hashrate_eh = round(sum(values) / len(values) / 1e18, 0)
        return int(btc), int(hashrate_eh)
    except Exception:
        return 80000, 1111  # Nov 2025 fallback

def calculate(
    chp_mw, load_factor, roc_rtfo, eii,
    miner_model, mining_mw
):
    # === Market Data ===
    btc_price, hashrate = fetch_market_data()
    if hashrate == 0:
        hashrate = 1111

    # === BTC Yield ===
    total_btc_per_year = BLOCKS_PER_DAY * DAYS_PER_YEAR * BLOCK_REWARD
    network_th = hashrate * 1_000_000
    btc_per_th_year = total_btc_per_year / network_th

    # === Miner Specs ===
    j_th = MINER_SPECS[miner_model]["j_th"]
    cost_per_mw = MINER_SPECS[miner_model]["cost_per_mw_gbp"]

    # === Energy ===
    annual_mwh = chp_mw * HOURS_PER_YEAR * load_factor
    min_export_pct = 0.05 if "ROC + RTFO" in roc_rtfo else 0.10 if "ROC only" in roc_rtfo else 0.0
    max_mining_mwh = annual_mwh * (1 - min_export_pct)
    actual_mining_mwh = min(mining_mw * HOURS_PER_YEAR * 0.98, max_mining_mwh)

    # === Mining Output ===
    th_per_mwh = 1_000_000 / j_th
    btc_per_mwh = btc_per_th_year * th_per_mwh * (1 - POOL_FEE_PCT)
    total_btc = btc_per_mwh * actual_mining_mwh
    revenue_btc = total_btc * btc_price

    # === Costs ===
    capex = mining_mw * cost_per_mw
    capex_annuity = capex * 0.20
    opex_annual = mining_mw * 12 * 6

    grid_save_mwh = 72 if "Yes" in eii else 45
    grid_savings = grid_save_mwh * actual_mining_mwh

    # === Net ===
    net_revenue = revenue_btc + grid_savings - capex_annuity - opex_annual
    net_per_mwh = net_revenue / actual_mining_mwh if actual_mining_mwh > 0 else 0
    payback = (capex_annuity + opex_annual) / (revenue_btc + grid_savings) if (revenue_btc + grid_savings) > 0 else float('inf')

    return {
        "btc_price": btc_price,
        "hashrate": hashrate,
        "total_btc": total_btc,
        "revenue_btc": revenue_btc,
        "grid_savings": grid_savings,
        "capex_annuity": capex_annuity,
        "opex_annual": opex_annual,
        "net_revenue": net_revenue,
        "net_per_mwh": net_per_mwh,
        "payback": payback,
        "annual_mwh": annual_mwh,
        "max_mining_mwh": max_mining_mwh,
        "actual_mining_mwh": actual_mining_mwh,
        "th_per_mwh": th_per_mwh,
        "j_th": j_th,
    }