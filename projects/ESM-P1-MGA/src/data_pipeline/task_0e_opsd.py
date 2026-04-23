"""
task_0e_opsd.py — Task 0E: Open Power System Data (OPSD)
=========================================================
Downloads the OPSD hourly time series and conventional power plants
dataset for Germany. Filters to DE columns (2018–2023), cleans gaps.

PREREQUISITES:
  pip install requests pandas

Outputs:
  data/energy/opsd_timeseries_DE.csv
  data/energy/opsd_powerplants_DE.csv
"""

import sys
import io
from pathlib import Path
import pandas as pd
import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    OPSD_TIMESERIES_CSV, OPSD_POWERPLANTS_CSV,
    OPSD_START_YEAR, OPSD_END_YEAR
)

# ─── OPSD download URLs ────────────────────────────────────────────────────────
OPSD_TS_URL = (
    "https://data.open-power-system-data.org/time_series/"
    "latest/time_series_60min_singleindex.csv"
)
OPSD_PP_URL = (
    "https://data.open-power-system-data.org/conventional_power_plants/"
    "latest/conventional_power_plants_DE.csv"
)

# Max gap (hours) to interpolate
MAX_INTERP_HOURS = 3

# Germany column prefixes in the OPSD time series file
DE_PREFIX = "DE_"


def _download_csv(url: str, label: str,
                  chunk_mb: int = 10) -> pd.DataFrame:
    """
    Stream-download a CSV from OPSD and return as DataFrame.
    Uses chunked download to handle large files (~400 MB for time series).
    """
    print(f"[0E] Downloading {label} ...")
    print(f"[0E]   URL: {url}")

    with requests.get(url, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        chunks = []
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=chunk_mb * 1024 * 1024):
            if chunk:
                chunks.append(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total * 100
                    print(f"\r[0E]   Progress: {pct:.1f}%", end="")
        print()  # new line after progress
        raw = b"".join(chunks)

    df = pd.read_csv(io.BytesIO(raw), low_memory=False)
    print(f"[0E] {label}: {len(df)} rows × {len(df.columns)} cols loaded")
    return df


def filter_de_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to Germany-relevant columns only and restrict to 2018–2023.

    OPSD time series columns use prefix DE_ for Germany.
    UTC timestamp column: 'utc_timestamp' or 'cet_cest_timestamp'.
    """
    # Identify timestamp column
    ts_cols = [c for c in df.columns if "utc_timestamp" in c.lower() or
               c.lower() in ("utc_timestamp", "timestamp")]
    if not ts_cols:
        ts_cols = [df.columns[0]]  # fallback: first column
    ts_col = ts_cols[0]

    df[ts_col] = pd.to_datetime(df[ts_col], utc=True)
    df = df.set_index(ts_col)
    df.index.name = "utc_timestamp"

    # Filter columns: keep DE_ prefix + any generic columns
    de_cols = [c for c in df.columns if c.startswith(DE_PREFIX)]
    if not de_cols:
        print("[0E] WARNING: No 'DE_' columns found. Check OPSD column naming.")
        de_cols = [c for c in df.columns if "DE" in c.upper()]

    df = df[de_cols]

    # Filter to date range
    start = pd.Timestamp(f"{OPSD_START_YEAR}-01-01", tz="UTC")
    end   = pd.Timestamp(f"{OPSD_END_YEAR}-12-31 23:00", tz="UTC")
    df    = df.loc[start:end]

    print(f"[0E] After filter: {len(df)} rows × {len(df.columns)} DE columns, "
          f"{df.index[0]} -> {df.index[-1]}")
    return df


def clean_timeseries(df: pd.DataFrame,
                     max_interp: int = MAX_INTERP_HOURS) -> pd.DataFrame:
    """
    Remove duplicate index entries, then interpolate short gaps.
    Logs number of duplicates and gaps per column.
    """
    # Remove duplicates
    n_dup = df.index.duplicated().sum()
    if n_dup > 0:
        print(f"[0E] WARNING: {n_dup} duplicate timestamps removed")
        df = df[~df.index.duplicated(keep="first")]

    # Interpolate short gaps
    total_missing_before = df.isna().sum().sum()
    df = df.interpolate(method="linear", limit=max_interp)
    total_missing_after  = df.isna().sum().sum()
    filled = total_missing_before - total_missing_after

    print(f"[0E] Gap fill: {total_missing_before} NaN -> {total_missing_after} NaN "
          f"(interpolated {filled} values, limit={max_interp}h)")

    # Log any remaining large gaps per column
    for col in df.columns:
        n_left = df[col].isna().sum()
        if n_left > 0:
            pct = n_left / len(df) * 100
            if pct > 1.0:
                print(f"[0E] WARNING: {col} still has {n_left} NaN ({pct:.1f}%)")

    return df


def process_power_plants(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise the conventional power plants DataFrame:
    - Ensure capacity_net_bnetza column
    - Convert MW to numeric
    - Keep only active/planned units
    """
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Try to find capacity column
    cap_cols = [c for c in df.columns if "capacity" in c or "mw" in c]
    if cap_cols:
        for cc in cap_cols:
            df[cc] = pd.to_numeric(df[cc], errors="coerce")

    # Keep only DE country (should already be filtered by URL, but double-check)
    if "country" in df.columns:
        df = df[df["country"].str.upper() == "DE"]

    print(f"[0E] Power plants: {len(df)} units")
    if cap_cols:
        total_gw = df[cap_cols[0]].sum() / 1e3
        print(f"[0E] Total capacity ({cap_cols[0]}): {total_gw:.1f} GW")

    # Summary by fuel type
    fuel_col = next((c for c in ["fuel", "energy_source_level_2",
                                  "energy_source"] if c in df.columns), None)
    if fuel_col:
        summary = df.groupby(fuel_col)[cap_cols[0]].sum().sort_values(ascending=False)
        print("[0E] Capacity by fuel (GW):")
        for fuel, cap in summary.items():
            print(f"    {fuel:<20} {cap/1e3:>6.1f} GW")

    return df


def run_task_0e() -> None:
    """Main entry point for Task 0E."""
    print("\n" + "=" * 60)
    print("  TASK 0E — Open Power System Data (OPSD)")
    print("=" * 60)

    # ── Time series ──────────────────────────────────────────────────────────
    if OPSD_TIMESERIES_CSV.exists() and OPSD_POWERPLANTS_CSV.exists():
        print(f"[0E] Cached outputs found: {OPSD_TIMESERIES_CSV.name}, {OPSD_POWERPLANTS_CSV.name}. Skipping download.")
        print("\n[0E] -------- TASK 0E COMPLETE (cached) --------\n")
        return

    ts_raw = _download_csv(OPSD_TS_URL, "OPSD time series")
    ts_de  = filter_de_timeseries(ts_raw)
    ts_de  = clean_timeseries(ts_de)

    ts_de.to_csv(OPSD_TIMESERIES_CSV)
    print(f"[0E] Time series saved -> {OPSD_TIMESERIES_CSV}")

    # ── Power plants ─────────────────────────────────────────────────────────
    pp_raw = _download_csv(OPSD_PP_URL, "OPSD power plants")
    pp_de  = process_power_plants(pp_raw)

    pp_de.to_csv(OPSD_POWERPLANTS_CSV, index=False)
    print(f"[0E] Power plants saved -> {OPSD_POWERPLANTS_CSV}")

    # Final summary
    print("\n[0E] ── TASK 0E COMPLETE ──────────────────────────────────")
    print(f"  {OPSD_TIMESERIES_CSV.name}")
    print(f"    Rows    : {len(ts_de)}")
    print(f"    Cols    : {len(ts_de.columns)} DE columns")
    print(f"    Range   : {ts_de.index[0]} -> {ts_de.index[-1]}")
    print(f"    Missing : {ts_de.isna().sum().sum()} cells remaining")
    print(f"  {OPSD_POWERPLANTS_CSV.name}")
    print(f"    Units   : {len(pp_de)}")
    print("[0E] ─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    run_task_0e()
