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


def calculate(chp_mw, load_factor, roc_rtfo, eii, miner_model, mining_mw):
    # === Market Data ===
    btc_price, hashrate = fetch_market_data()
    if hashrate == 0:
        hashrate = 1111

    # === BTC YIELD (CORRECTED) ===
    total_btc_per_year = BLOCKS_PER_DAY * DAYS_PER_YEAR * BLOCK_REWARD
    network_th_s = hashrate * 1_000_000  # EH/s → TH/s

    # === Miner Specs ===
    j_th = MINER_SPECS[miner_model]["j_th"]
    cost_per_mw = MINER_SPECS[miner_model]["cost_per_mw_gbp"]

    # === Energy ===
    annual_mwh = chp_mw * HOURS_PER_YEAR * load_factor
    min_export_pct = 0.05 if "ROC + RTFO" in roc_rtfo else 0.10 if "ROC only" in roc_rtfo else 0.0
    max_mining_mwh = annual_mwh * (1 - min_export_pct)
    actual_mining_mwh = min(mining_mw * HOURS_PER_YEAR * 0.98, max_mining_mwh)

    # === Mining Output (FIXED) ===
    th_per_mw = 1_000_000 / j_th  # TH/s per MW
    effective_mw = actual_mining_mwh / HOURS_PER_YEAR
    miner_th_s = effective_mw * th_per_mw

    total_btc = (miner_th_s / network_th_s) * total_btc_per_year * (1 - POOL_FEE_PCT)
    revenue_btc = total_btc * btc_price

    # === Costs ===
    capex = mining_mw * cost_per_mw
    capex_annuity = capex * 0.20
#    opex_annual = mining_mw * 12 * 6  # £6k/MW/month × 12
    opex_annual = mining_mw * 12 * 6000  # £6,000/MW/year

    grid_save_mwh = 72 if "Yes" in eii else 45
    grid_savings = grid_save_mwh * actual_mining_mwh

    # === Net ===
    net_revenue = revenue_btc + grid_savings - capex_annuity - opex_annual
    net_per_mwh = net_revenue / actual_mining_mwh if actual_mining_mwh > 0 else 0
    payback = (capex_annuity + opex_annual) / (revenue_btc + grid_savings) if (revenue_btc + grid_savings) > 0 else float('inf')
    # After calculating payback in years
    payback_months = payback * 12 if payback != float('inf') else float('inf')

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
        "payback_months": payback_months,
        "annual_mwh": annual_mwh,
        "max_mining_mwh": max_mining_mwh,
        "actual_mining_mwh": actual_mining_mwh,
        "effective_mw": effective_mw,
        "miner_th_s": miner_th_s,
        "th_per_mw": th_per_mw,
        "j_th": j_th,
    }