from __future__ import annotations
import glob, math, datetime as dt
from pathlib import Path
from typing import List, Optional, Tuple
import requests
import pandas as pd
import traceback

from constants import PREFERRED_BRAND_ASICS, MUST_INCLUDE_ASICS

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def _strip_brand(name: str, brand: str) -> str:
    if not isinstance(name, str) or not brand:
        return name
    n, b = name.strip(), str(brand).strip()
    if n.lower().startswith(b.lower() + " "):
        return n[len(b) + 1 :].strip()
    return n

def _fmt(x, nd=2):
    try:
        return f"{float(x):,.{nd}f}"
    except Exception:
        return "n/a"

def _today_prefix() -> str:
    return dt.datetime.now().strftime("%y%m%d_")

def _make_filename(ext="csv") -> Path:
    return DATA_DIR / f"minerstat_asic_sha256_{dt.datetime.now().strftime('%y%m%d_%H%M%S')}.{ext}"

def _find_todays_file(ext="csv") -> Optional[Path]:
    pattern = str(DATA_DIR / f"minerstat_asic_sha256_{_today_prefix()}*.{ext}")
    matches = sorted(glob.glob(pattern))
    return Path(matches[-1]) if matches else None

def _fetch_minerstat_sha256() -> pd.DataFrame:
    j = requests.get("https://api.minerstat.com/v2/hardware", timeout=60).json()
    rows, fetched_at = [], dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    for item in j:
        if str(item.get("type", "")).lower() != "asic":
            continue
        sha = (item.get("algorithms") or {}).get("SHA-256") or {}
        if not isinstance(sha, dict):
            continue
        speed = sha.get("speed")   # H/s
        power = sha.get("power")   # W
        if not isinstance(speed, (int, float)) or speed <= 0:
            continue
        ths = speed / 1e12
        eff = (power / ths) if power else math.nan
        rows.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "brand": item.get("brand"),
            "url": item.get("url"),
            "hashrate_THs": round(ths, 2),
            "power_W": power,
            "efficiency_J_per_TH": round(eff, 2) if eff == eff else None,
            "retrieved_at": fetched_at,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["efficiency_J_per_TH", "hashrate_THs"], ascending=[True, False], na_position="last")
        df["brand"] = df["brand"].fillna("Unknown")
    return df

def ensure_today_csv() -> Path:
    existing = _find_todays_file("csv")
    if existing and existing.exists():
        return existing
    try:
        df = _fetch_minerstat_sha256()
        out = _make_filename("csv")
        df.to_csv(out, index=False)
        return out
    except Exception:
        # If fetch fails, but we have any CSV today, use it.
        if existing and existing.exists():
            return existing
        # Otherwise rethrow with context
        traceback.print_exc()
        raise

def load_today_df() -> pd.DataFrame:
    return pd.read_csv(ensure_today_csv())

def _pick_diverse_top_six(df: pd.DataFrame, must_include: list[str]) -> pd.DataFrame:
    base = df.copy()
    base = base.sort_values(["efficiency_J_per_TH", "hashrate_THs"], ascending=[True, False], na_position="last")

    chosen = []
    seen = set()

    # 1) Guarantee brands in MUST_INCLUDE_ASICS (best model per brand, if present)
    want = [b.lower() for b in must_include]
    for b in want:
        match = base[base["brand"].str.lower() == b]
        if not match.empty:
            row = match.iloc[0]
            chosen.append(row)
            seen.add(row["brand"])

    # 2) Fill remaining with next-best while keeping brand diversity
    for _, row in base.iterrows():
        if len(chosen) == 6:
            break
        if row["brand"] in seen:
            continue
        chosen.append(row)
        seen.add(row["brand"])

    # 3) If still < 6, top-up ignoring diversity
    if len(chosen) < 6:
        for _, row in base.iterrows():
            if len(chosen) == 6:
                break
            if any(row["id"] == r["id"] for r in chosen):
                continue
            chosen.append(row)

    return pd.DataFrame(chosen[:6])

def _pick_top_six_single_brand(df: pd.DataFrame, brand: str) -> pd.DataFrame:
    base = df[df["brand"].str.lower() == brand.lower()].copy()
    base = base.sort_values(["efficiency_J_per_TH", "hashrate_THs"], ascending=[True, False], na_position="last")
    return base.head(6)

def pick_top_six(df: pd.DataFrame, preferred_brand: Optional[str] = None, must_include: Optional[list[str]] = None) -> pd.DataFrame:
    """
    Selection logic:
    - If preferred_brand provided (or constant set), return top 6 from that brand.
    - Else, use must_include list to guarantee brand presence, then fill best remaining.
    """
    brand = (preferred_brand if preferred_brand is not None else PREFERRED_BRAND_ASICS).strip()
    if brand:
        return _pick_top_six_single_brand(df, brand)

    must = must_include if must_include is not None else MUST_INCLUDE_ASICS
    return _pick_diverse_top_six(df, must)

def get_dropdown_options(preferred_brand: Optional[str] = None) -> List[Tuple[str, str]]:
    df = load_today_df()
    reduced = pick_top_six(df, preferred_brand=preferred_brand)
    options: List[Tuple[str, str]] = []
    for _, r in reduced.iterrows():
        brand = (r.get("brand") or "").strip()
        display_name = _strip_brand(str(r.get("name", "")), brand)
        eff = f"{_fmt(r.get('efficiency_J_per_TH'))} J/TH"
        ths = f"{_fmt(r.get('hashrate_THs'))} TH/s"
        label = f"{brand} {display_name} ({eff}, {ths})".strip()
        value = str(r["id"]) if pd.notna(r["id"]) else str(r["name"])
        options.append((label, value))
    return options

# at bottom of asics_data.py
def get_dropdown_options_from_constants():
    """Uses PREFERRED_BRAND_ASICS (if set) else MUST_INCLUDE_ASICS (inside pick_top_six)."""
    pref = PREFERRED_BRAND_ASICS.strip()
    return get_dropdown_options(preferred_brand=pref or None)

# --- add to end of asics_data.py ---

def get_specs_by_id(miner_id: str):
    """
    Return a dict of specs for a given miner id from today's CSV.
    Keys: id, name, brand, hashrate_ths, power_w, efficiency_j_th
    """
    if not miner_id:
        return None

    df = load_today_df()
    row = df[df["id"] == miner_id]
    if row.empty:
        # fallback: sometimes UI may pass name as value; try name match
        row = df[df["name"] == miner_id]
        if row.empty:
            return None

    r = row.iloc[0]
    def _as_float(val):
        try:
            return float(val)
        except Exception:
            return None

    return {
        "id": r.get("id"),
        "name": r.get("name"),
        "brand": r.get("brand"),
        "hashrate_ths": _as_float(r.get("hashrate_THs")),
        "power_w": _as_float(r.get("power_W")),
        "efficiency_j_th": _as_float(r.get("efficiency_J_per_TH")),
    }

