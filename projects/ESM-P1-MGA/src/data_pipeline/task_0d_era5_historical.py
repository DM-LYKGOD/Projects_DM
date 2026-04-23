"""
task_0d_era5_historical.py - Task 0D: Pre-Processed ERA5 Historical CF
========================================================================
Downloads pre-processed hourly wind and solar capacity factor time series
for Germany from the University of Reading research data repository.

Outputs:
  data/climate/era5_cf_DE_historical.csv
"""

import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import CLIMATE_DIR, ERA5_CF_HIST_CSV

READING_BASE = "https://researchdata.reading.ac.uk/321"
READING_FILES = {
    "solar_pv": f"{READING_BASE}/1/NUTS0_pv_capacity_factors.csv",
    "wind_onshore": f"{READING_BASE}/1/NUTS0_wind_capacity_factors.csv",
}


def _download_with_retry(url: str, timeout: int = 120, retries: int = 3) -> bytes | None:
    """Attempt to download a URL, retrying on transient failures."""
    for attempt in range(1, retries + 1):
        try:
            print(f"[0D]   Attempt {attempt}/{retries}: GET {url}")
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.exceptions.RequestException as exc:
            print(f"[0D]   WARNING: {exc}")
            if attempt < retries:
                time.sleep(5 * attempt)
    return None


def _parse_reading_csv(raw_bytes: bytes, country_col: str = "DE") -> pd.Series:
    """Parse a Reading University NUTS0 capacity factor CSV for Germany."""
    df = pd.read_csv(io.BytesIO(raw_bytes), index_col=0, parse_dates=True)
    df.columns = [str(c).strip().upper() for c in df.columns]

    if country_col not in df.columns:
        candidates = [c for c in df.columns if "DE" in c or "GERM" in c]
        if not candidates:
            raise KeyError(
                f"[0D] Country column '{country_col}' not found. "
                f"Available: {list(df.columns)}"
            )
        country_col = candidates[0]
        print(f"[0D]   Using column '{country_col}' for Germany")

    series = df[country_col].dropna()
    series.index = pd.to_datetime(series.index, utc=True)
    return series


def run_task_0d() -> None:
    """Main entry point for Task 0D."""
    print("\n" + "=" * 60)
    print("  TASK 0D - ERA5-Derived Historical Capacity Factors")
    print("=" * 60)
    print(f"  Source: {READING_BASE}")

    if ERA5_CF_HIST_CSV.exists():
        print(f"[0D] Cached output found: {ERA5_CF_HIST_CSV}. Skipping download.")
        df = pd.read_csv(ERA5_CF_HIST_CSV, index_col=0, parse_dates=True)
        print("\n  ERA5 Historical CF - Coverage Summary")
        print(f"  Rows        : {len(df):,}")
        print(f"  Start       : {df.index.min()}")
        print(f"  End         : {df.index.max()}")
        print(f"  Solar mean  : {df['solar_pv_cf'].mean():.4f}")
        print(f"  Wind mean   : {df['wind_onshore_cf'].mean():.4f}")
        print(f"[0D] Historical CF already available -> {ERA5_CF_HIST_CSV}")
        print("\n[0D] -------- TASK 0D COMPLETE (cached) --------\n")
        return

    solar_series = None
    wind_series = None

    print("\n[0D] Downloading solar PV CF ...")
    raw_solar = _download_with_retry(READING_FILES["solar_pv"])
    if raw_solar:
        try:
            solar_series = _parse_reading_csv(raw_solar, country_col="DE")
            print(
                f"[0D] Solar CF loaded: {len(solar_series)} hourly obs | "
                f"mean={solar_series.mean():.4f}"
            )
        except Exception as exc:
            print(f"[0D] WARNING: Could not parse solar CSV: {exc}")

    print("\n[0D] Downloading wind CF ...")
    raw_wind = _download_with_retry(READING_FILES["wind_onshore"])
    if raw_wind:
        try:
            wind_series = _parse_reading_csv(raw_wind, country_col="DE")
            print(
                f"[0D] Wind CF loaded: {len(wind_series)} hourly obs | "
                f"mean={wind_series.mean():.4f}"
            )
        except Exception as exc:
            print(f"[0D] WARNING: Could not parse wind CSV: {exc}")

    if solar_series is None or wind_series is None:
        raise RuntimeError(
            "[0D] Real historical CF download was not fully successful. "
            "Synthetic fallback has been removed to avoid fabricated results."
        )

    df = pd.DataFrame(
        {
            "solar_pv_cf": solar_series,
            "wind_onshore_cf": wind_series,
            "source": "reading_university_Bloomfield2020",
        }
    )
    df.index.name = "utc_timestamp"

    print("\n  ERA5 Historical CF - Coverage Summary")
    print(f"  Rows        : {len(df):,}")
    print(f"  Start       : {df.index.min()}")
    print(f"  End         : {df.index.max()}")
    print(f"  Solar mean  : {df['solar_pv_cf'].mean():.4f}")
    print(f"  Wind mean   : {df['wind_onshore_cf'].mean():.4f}")

    CLIMATE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(ERA5_CF_HIST_CSV)
    print(f"[0D] Historical CF saved -> {ERA5_CF_HIST_CSV}")


if __name__ == "__main__":
    run_task_0d()
