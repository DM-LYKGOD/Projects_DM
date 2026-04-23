"""
task_0h_destatis_genesis.py - Task 0H: Destatis Genesis Table 42131-0004
=========================================================================
Downloads annual cement production data from the Destatis GENESIS API.
"""

import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    DESTATIS_END_YEAR,
    DESTATIS_GENESIS_CSV,
    DESTATIS_START_YEAR,
    GENESIS_PW,
    GENESIS_USER,
)

GENESIS_BASE = "https://www-genesis.destatis.de/genesisWS/rest/2020"
TABLE_ID = "42131-0004"


def _check_credentials() -> bool:
    if GENESIS_USER == "YOUR_GENESIS_USERNAME":
        print(
            "\n[0H] GENESIS credentials not set.\n"
            "  1. Register free at: https://www-genesis.destatis.de\n"
            "  2. Open config.py and set:\n"
            "     GENESIS_USER = 'your_username'\n"
            "     GENESIS_PW   = 'your_password'\n"
            "  Published fallback data has been removed to avoid fabricated results.\n"
        )
        return False
    return True


def _genesis_login() -> str | None:
    """Authenticate with the GENESIS REST API."""
    url = f"{GENESIS_BASE}/helloworld/logincheck"
    params = {"username": GENESIS_USER, "password": GENESIS_PW, "language": "en"}
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("Status", {}).get("Code", "")
        if status in ("0", 0):
            print("[0H] GENESIS login successful")
            return GENESIS_USER
        print(f"[0H] WARNING: GENESIS login returned status {status}")
        return None
    except Exception as exc:
        print(f"[0H] GENESIS login failed: {exc}")
        return None


def _fetch_table(table_id: str) -> dict | None:
    """Fetch a GENESIS table as JSON."""
    url = f"{GENESIS_BASE}/data/table"
    params = {
        "username": GENESIS_USER,
        "password": GENESIS_PW,
        "name": table_id,
        "area": "all",
        "compress": "false",
        "transpose": "false",
        "startyear": str(DESTATIS_START_YEAR),
        "endyear": str(DESTATIS_END_YEAR),
        "language": "en",
        "format": "json",
    }
    try:
        print(f"[0H] Requesting table {table_id} from GENESIS ...")
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"[0H] GENESIS table fetch failed: {exc}")
        return None


def _parse_genesis_table(data: dict) -> pd.DataFrame | None:
    """Parse the GENESIS JSON content payload into a dataframe."""
    try:
        content = data.get("Object", {}).get("Content", "")
        if not content:
            print("[0H] WARNING: Empty content in GENESIS response")
            return None

        from io import StringIO

        df = pd.read_csv(StringIO(content), sep=";", encoding="utf-8", on_bad_lines="skip")
        print(f"[0H] GENESIS table parsed: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[0H] GENESIS parse failed: {exc}")
        return None


def _extract_cement_annual(df: pd.DataFrame) -> pd.DataFrame | None:
    """Extract annual cement production from the parsed table."""
    if df is None:
        return None

    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    year_cols = [c for c in df.columns if "jahr" in c or "year" in c or c == "zeit"]
    val_cols = [c for c in df.columns if "wert" in c or "value" in c or "menge" in c]
    prod_cols = [c for c in df.columns if "23.5" in c or "zement" in c or "cement" in c]

    if not year_cols:
        print("[0H] Could not identify year column in GENESIS table")
        return None

    year_col = year_cols[0]
    val_col = val_cols[0] if val_cols else (prod_cols[0] if prod_cols else df.columns[-1])

    result = df[[year_col, val_col]].copy()
    result.columns = ["year", "production_tonnes"]
    result["year"] = pd.to_numeric(result["year"], errors="coerce")
    result["production_tonnes"] = pd.to_numeric(
        result["production_tonnes"].astype(str).str.replace(",", ""),
        errors="coerce",
    )
    result = result.dropna().astype({"year": int})
    return result.sort_values("year").reset_index(drop=True)


def _add_yoy_growth(df: pd.DataFrame) -> pd.DataFrame:
    """Add year-on-year change columns."""
    df = df.copy().sort_values("year").reset_index(drop=True)
    df["production_Mt"] = df["production_tonnes"] / 1e6
    df["yoy_pct_change"] = df["production_Mt"].pct_change() * 100
    return df


def print_annual_table(df: pd.DataFrame) -> None:
    """Print a compact annual production table."""
    print("\n  Annual Cement Production - Germany")
    print(f"  {'Year':>6}  {'Production (Mt)':>16}  {'YoY Change (%)':>15}")
    print("  " + "-" * 42)
    for _, row in df.iterrows():
        yoy = f"{row['yoy_pct_change']:+.1f}" if pd.notna(row.get("yoy_pct_change")) else "  -"
        print(f"  {int(row['year']):>6}  {row['production_Mt']:>16.2f}  {str(yoy):>15}")


def run_task_0h() -> None:
    """Main entry point for Task 0H."""
    print("\n" + "=" * 60)
    print("  TASK 0H - Destatis Genesis Table 42131-0004")
    print("=" * 60)

    if DESTATIS_GENESIS_CSV.exists():
        print(f"[0H] Cached output found: {DESTATIS_GENESIS_CSV}. Skipping download.")
        print("\n[0H] -------- TASK 0H COMPLETE (cached) --------\n")
        return

    df = None
    if _check_credentials():
        token = _genesis_login()
        if token:
            raw_data = _fetch_table(TABLE_ID)
            if raw_data:
                parsed = _parse_genesis_table(raw_data)
                df = _extract_cement_annual(parsed)

    if df is None or len(df) < 5:
        raise RuntimeError(
            "[0H] GENESIS data could not be retrieved. "
            "Published fallback values have been removed to avoid fabricated results."
        )

    df = _add_yoy_growth(df)
    print_annual_table(df)
    df.to_csv(DESTATIS_GENESIS_CSV, index=False)
    print(f"[0H] Annual production saved -> {DESTATIS_GENESIS_CSV}")


if __name__ == "__main__":
    run_task_0h()
