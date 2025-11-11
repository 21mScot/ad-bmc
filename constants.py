# constants.py
# === BTC NETWORK CONSTANTS (Update at halving) ===
BLOCKS_PER_DAY   = 144
BLOCK_REWARD     = 3.125        # Post-2024 halving
POOL_FEE_PCT     = 0.01         # 1%
DAYS_PER_YEAR    = 365.25
HOURS_PER_YEAR   = 8760

# === API CONFIG ===
COINGECKO_URL    = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=gbp"
COINGECKO_TIMEOUT = 5
BLOCKCHAIN_URL   = "https://api.blockchain.info/charts/hash-rate?format=json&timespan=30days"
BLOCKCHAIN_TIMEOUT = 10

# === MINER SPECS ===
MINER_SPECS = {
    "Whatsminer M53S++ Hydro (22 J/TH)": {"j_th": 22, "cost_per_mw_gbp": 1_800_000},
    "Whatsminer M50S++ (24 J/TH)": {"j_th": 24, "cost_per_mw_gbp": 1_600_000},
    "Antminer S21 XP Hydro (11 J/TH)": {"j_th": 11, "cost_per_mw_gbp": 2_800_000},
}