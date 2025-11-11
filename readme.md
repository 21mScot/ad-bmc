# AD → BTC Mining Calculator

A live web tool for Anaerobic Digestion (AD) plant operators to calculate **Bitcoin yield** from behind-the-meter power.  
**Key Value:** Divert excess CHP electricity to mining → **£95+/MWh net uplift** + **1–3 BTC/year** (at current prices) without losing ROCs/RTFO.

## 🎯 Quick Start
1. Open: [https://ad-bmc.streamlit.app](https://ad-bmc.streamlit.app) (no install).
2. Input your **CHP size (MW)** and **load factor** in the sidebar.
3. Toggle **ROC/RTFO** and **EII** for compliance/savings.
4. Select miner → See **instant BTC/year**, **£/MWh**, and **payback** (often <1.5 years).

## 📊 Sample Output (1 MW CHP, 92% Load, EII Exempt, M53S++ Miner – Nov 2025)
| Metric | Value |
|--------|-------|
| **Mining MWh/year** | 7,562 |
| **BTC/year** | 2.91 BTC (£232,800 @ £80,000/BTC) |
| **Grid Savings** | £544,464 (@ £72/MWh) |
| **Net £/MWh** | £102.4 (after costs) |
| **Payback** | 0.9 years |

## 🔧 Variables Explained
- **CHP Size/Load Factor:** Your plant's output (e.g., 90–95% for AD reliability).
- **ROC/RTFO:** Min 5–10% export to keep subsidies (Ofgem rules).
- **EII Exempt:** Saves £27/MWh on CCL/DUoS for energy-intensive industries.
- **Miner Model:** Hydro/immersion optimized for Scotland (uses digestate heat – £0 cooling).
- **Live Data:** BTC price & hashrate auto-refresh every 60s.

## 🚀 Economics Nuances
- **Uptime:** 98% (AD = predictable vs. wind).
- **Costs:** 20% capex annuity (5-yr life), £6/kW/month opex.
- **Upside:** Add gate fees/digestate revenue as fixed baseline – mining is **pure add-on**.

## 📞 Contact
Built by [Your Name/21mScot] for quick PoC. Questions? Email: [your-email@domain.com] | Let's deploy on your plant.

*Powered by Streamlit • Open source: Fork this repo.*