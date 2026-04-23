"""
task_0b_entsoe.py — Task 0B: ENTSO-E Transparency Data (local file mode)
=========================================================================
Reads the ENTSO-E files downloaded manually from the Transparency Portal:
  - Realisierter_Stromverbrauch_*_Stunde.csv  (actual load, hourly)
  - Realisierte_Erzeugung_*_Stunde.csv        (actual generation by carrier)

File format (ENTSO-E DE export):
  Delimiter : ;
  Encoding  : utf-8-sig
  Date cols : 'Datum von' / 'Datum bis'   (DD.MM.YYYY HH:MM, CET/CEST)
  Numbers   : German locale (1.234,56 -> 1234.56)

The pipeline uses 2025 as the analysis year (12 months).
Falls back to 2024 if 2025 data is incomplete.

Outputs:
  data/energy/entsoe_load_DE_2023.csv            (kept at canonical name)
  data/energy/entsoe_generation_DE_2023.csv
"""

import sys
import shutil
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    ENTSOE_LOAD_CSV, ENTSOE_GEN_CSV, ENERGY_DIR,
    PROJECT_ROOT, FALLBACK_SYS_LOAD_MW,
)


LOAD_PATTERN = "Realisierter_Stromverbrauch_*_Stunde.csv"
GEN_PATTERN  = "Realisierte_Erzeugung_*_Stunde.csv"

_SEARCH_DIRS = [
    Path(__file__).parent,       # src/data_pipeline/
    PROJECT_ROOT,                 # project root
    Path("/content"),             # Colab direct upload location
    Path.cwd(),                   # wherever the notebook CWD is
]

# ─── Parsing settings ─────────────────────────────────────────────────────────
SEP          = ";"
ENCODING     = "utf-8-sig"
DATE_COL_FROM = "Datum von"
DATE_COL_TO   = "Datum bis"

# Max consecutive gap (hours) to forward-fill before flagging
MAX_FILL_HOURS = 2

# Preferred analysis year; falls back to next available year
PREFERRED_YEAR = 2025
FALLBACK_YEAR  = 2024


def _find_raw_file(pattern: str) -> Path | None:
    """Locate the raw ENTSO-E CSV across all search directories."""
    for directory in _SEARCH_DIRS:
        if not directory.exists():
            continue
        matches = list(directory.glob(pattern))
        if matches:
            best = sorted(matches, key=lambda p: len(p.name))[-1]
            print(f"[0B]   Found '{pattern}' in {directory}")
            return best
    return None


def _build_synthetic_entsoe(year: int = 2025) -> tuple:
    """
    Generate synthetic hourly ENTSO-E load + generation for Germany.
    Only used when no real files are found.  Clearly labelled in outputs.
    """
    print(f"[0B] Building synthetic ENTSO-E data for {year} ...")
    idx  = pd.date_range(f"{year}-01-01", periods=8760, freq="h", tz="UTC")
    t    = np.arange(8760)
    hour = t % 24
    day  = t / 24.0

    daily    = 0.85 + 0.15 * np.cos(2 * np.pi * (hour - 18) / 24)
    seasonal = 1.10 - 0.20 * np.cos(2 * np.pi * (day - 15) / 365)
    load_mw  = FALLBACK_SYS_LOAD_MW * daily * seasonal

    load_df = pd.DataFrame({"load_MW": load_mw}, index=idx)
    load_df.index.name = "utc_timestamp"

    daytime = np.clip((hour - 6) / 6, 0, 1) * np.clip((20 - hour) / 6, 0, 1)
    seas_pv = 0.5 + 0.5 * np.cos(2 * np.pi * (day - 172) / 365)
    pv_cf   = np.clip(daytime * seas_pv * 0.85, 0, 1)

    rng       = np.random.default_rng(42)
    wind_base = 0.30 + 0.15 * np.cos(2 * np.pi * (day - 30) / 365)
    wind_cf   = np.clip(wind_base + rng.normal(0, 0.10, 8760), 0.02, 1.0)

    residual = np.maximum(0, load_mw - pv_cf * 90_000 - wind_cf * 70_000 - 9_000)
    gen_df = pd.DataFrame({
        "Photovoltaik": pv_cf * 90_000,
        "Wind_Onshore":  wind_cf * 70_000,
        "Kernenergie":   np.full(8760, 3_000.0),
        "Braunkohle":    np.full(8760, 6_000.0),
        "Erdgas":        residual,
    }, index=idx)
    gen_df.index.name = "utc_timestamp"
    return load_df, gen_df



def _parse_german_float(s) -> float:
    """Convert German-locale number string '1.234,56' -> 1234.56."""
    if pd.isna(s):
        return np.nan
    s = str(s).strip()
    if s in ("-", "", "n/e", "N/A"):
        return np.nan
    # Remove thousands separator, swap decimal comma
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def _load_raw_csv(path: Path, label: str) -> pd.DataFrame:
    """Read a raw ENTSO-E portal CSV."""
    print(f"[0B] Loading {label}: {path.name}")
    df = pd.read_csv(path, sep=SEP, encoding=ENCODING, low_memory=False)
    print(f"[0B]   Raw shape: {df.shape[0]} rows × {df.shape[1]} cols")
    print(f"[0B]   Columns  : {list(df.columns[:6])} ...")
    return df


def _parse_datetime_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    """
    Parse the 'Datum von' column into a UTC-aware DatetimeIndex.
    ENTSO-E portal exports use CET/CEST local time (UTC+1 / UTC+2).
    """
    dt_col = DATE_COL_FROM if DATE_COL_FROM in df.columns else df.columns[0]
    # German date format: DD.MM.YYYY HH:MM
    dts = pd.to_datetime(df[dt_col], format="%d.%m.%Y %H:%M", errors="coerce")
    # Localise to CET/CEST then convert to UTC
    try:
        dts = dts.dt.tz_localize("Europe/Berlin", ambiguous="infer",
                                  nonexistent="shift_forward")
        dts = dts.dt.tz_convert("UTC")
    except Exception:
        # If localisation fails (e.g. already tz-aware), just use as-is
        pass
    return dts


def _process_load(path: Path) -> pd.DataFrame:
    """
    Parse the load CSV -> hourly MW time series with UTC index.
    """
    df = _load_raw_csv(path, "ENTSO-E load")

    # Parse datetime
    index = _parse_datetime_index(df)
    df.index = index
    df.index.name = "utc_timestamp"

    # Drop date columns
    drop_cols = [c for c in df.columns if "Datum" in c]
    df = df.drop(columns=drop_cols, errors="ignore")

    # Convert all value columns from German locale floats -> float64
    # Look for the 'Netzlast' (grid load) column
    load_col = next(
        (c for c in df.columns if "Netzlast" in c or "Verbrauch" in c
         or "Last" in c), df.columns[0]
    )
    df[load_col] = df[load_col].apply(_parse_german_float)

    # Keep only the load column, rename to load_MW
    result = df[[load_col]].copy()
    result.columns = ["load_MW"]

    # Resample to exactly hourly
    result = result.resample("h").mean()

    print(f"[0B]   Date range: {result.index[0]} -> {result.index[-1]}")
    return result


def _process_generation(path: Path) -> pd.DataFrame:
    """
    Parse the generation CSV -> hourly MW per carrier with UTC index.
    """
    df = _load_raw_csv(path, "ENTSO-E generation")

    # Parse datetime
    index = _parse_datetime_index(df)
    df.index = index
    df.index.name = "utc_timestamp"

    # Drop date columns
    drop_cols = [c for c in df.columns if "Datum" in c]
    df = df.drop(columns=drop_cols, errors="ignore")

    # Convert all remaining columns using German locale parser
    for col in df.columns:
        df[col] = df[col].apply(_parse_german_float)

    # Resample to hourly
    df = df.resample("h").mean()

    # Clean column names (remove unit suffix like ' [MWh] Berechnete Auflösungen')
    df.columns = [
        c.split("[")[0].strip().replace(" ", "_").replace("/", "_")
        for c in df.columns
    ]

    print(f"[0B]   Date range: {df.index[0]} -> {df.index[-1]}")
    print(f"[0B]   Carriers  : {list(df.columns)}")
    return df


def _select_year(df: pd.DataFrame, preferred: int, fallback: int) -> pd.DataFrame:
    """Filter to preferred year; fall back if fewer than 8000 hours available."""
    for yr in [preferred, fallback]:
        subset = df[df.index.year == yr]
        if len(subset) >= 8000:
            print(f"[0B]   Using year {yr}: {len(subset)} hourly obs")
            return subset
    # If neither has 8000 h, just return all available
    print(f"[0B] WARNING: Neither {preferred} nor {fallback} has ≥8000 h. "
          f"Returning full dataset ({len(df)} obs).")
    return df


def _clean_series(df: pd.DataFrame, label: str,
                  max_fill: int = MAX_FILL_HOURS) -> pd.DataFrame:
    """Forward-fill gaps ≤ max_fill hours; log any longer gaps."""
    n_missing_before = df.isna().sum().sum()
    if n_missing_before == 0:
        print(f"[0B]   {label}: no missing values")
        return df

    df_filled = df.ffill(limit=max_fill)
    n_missing_after = df_filled.isna().sum().sum()
    filled = n_missing_before - n_missing_after

    print(f"[0B]   {label}: {n_missing_before} NaN -> {n_missing_after} NaN "
          f"(filled {filled} via ffill ≤{max_fill}h)")

    # Warn about columns with remaining large gaps
    for col in df_filled.columns:
        n_left = df_filled[col].isna().sum()
        if n_left > max_fill:
            print(f"[0B]   WARNING: '{col}' still has {n_left} missing hours "
                  f"({n_left/len(df_filled)*100:.1f}%)")
    return df_filled


def _copy_to_data_dir(src: Path, label: str) -> None:
    """Copy raw file into data/energy/ for provenance."""
    dest = ENERGY_DIR / src.name
    if not dest.exists():
        shutil.copy2(src, dest)
        print(f"[0B]   Copied raw {label} -> {dest.relative_to(dest.parent.parent.parent)}")


def print_summary(load: pd.DataFrame, gen: pd.DataFrame) -> None:
    print("\n  ENTSO-E Summary")
    print("  ─────────────────────────────────────────────────────")
    yr = int(pd.Series(load.index.year).mode()[0])
    print(f"  Year used         : {yr}")
    print(f"  Load series       : {len(load)} obs | "
          f"mean={load['load_MW'].mean():.0f} MW | "
          f"max={load['load_MW'].max():.0f} MW")
    print(f"  Missing load      : {load['load_MW'].isna().sum()} h")
    total_load_twh = load['load_MW'].sum() / 1e6
    print(f"  Annual load       : {total_load_twh:.1f} TWh")
    print(f"  Generation cols   : {len(gen.columns)} carriers")
    total_gen_twh  = gen.sum().sum() / 1e6
    print(f"  Annual generation : {total_gen_twh:.1f} TWh")
    print("  ─────────────────────────────────────────────────────\n")


def run_task_0b() -> None:
    """Main entry point for Task 0B (local file mode)."""
    print("\n" + "=" * 60)
    print("  TASK 0B — ENTSO-E Data (local files)")
    print("=" * 60)

    # ── Locate raw files ──────────────────────────────────────────────────────
    if ENTSOE_LOAD_CSV.exists() and ENTSOE_GEN_CSV.exists():
        print(f"[0B] Cached outputs found: {ENTSOE_LOAD_CSV.name}, {ENTSOE_GEN_CSV.name}. Skipping download.")
        try:
            load = pd.read_csv(ENTSOE_LOAD_CSV, index_col=0, parse_dates=True)
            gen = pd.read_csv(ENTSOE_GEN_CSV, index_col=0, parse_dates=True)
            print_summary(load, gen)
        except Exception as exc:
            print(f"[0B] WARNING: Could not reload cached outputs: {exc}")
        print("\n[0B] -------- TASK 0B COMPLETE (cached) --------\n")
        return
    load_raw = _find_raw_file(LOAD_PATTERN)
    gen_raw  = _find_raw_file(GEN_PATTERN)

    if load_raw is None or gen_raw is None:
        missing = [p for p, f in ((LOAD_PATTERN, load_raw), (GEN_PATTERN, gen_raw)) if f is None]
        print(f"[0B] WARNING: File(s) not found: {missing}")
        print("[0B] Searched in:")
        for d in _SEARCH_DIRS:
            print(f"[0B]   {d}")
        print("[0B] *** Synthetic fallback activated.  Upload real files to /content/ for research. ***")
        print("[0B] *** Real data: https://transparency.entsoe.eu ***")
        ENERGY_DIR.mkdir(parents=True, exist_ok=True)
        load, gen = _build_synthetic_entsoe(PREFERRED_YEAR)
        load.to_csv(ENTSOE_LOAD_CSV)
        gen.to_csv(ENTSOE_GEN_CSV)
        print(f"[0B] Synthetic load saved       -> {ENTSOE_LOAD_CSV}")
        print(f"[0B] Synthetic generation saved -> {ENTSOE_GEN_CSV}")
        print("\n[0B] ── TASK 0B COMPLETE (synthetic fallback) ──────────────\n")
        return

    # Copy raw files to data/energy/ for provenance
    _copy_to_data_dir(load_raw, "load")
    _copy_to_data_dir(gen_raw,  "generation")

    # ── Parse ─────────────────────────────────────────────────────────────────
    load_all = _process_load(load_raw)
    gen_all  = _process_generation(gen_raw)

    # ── Select best analysis year ─────────────────────────────────────────────
    load = _select_year(load_all, PREFERRED_YEAR, FALLBACK_YEAR)
    gen  = _select_year(gen_all,  PREFERRED_YEAR, FALLBACK_YEAR)

    # ── Clean gaps ────────────────────────────────────────────────────────────
    load = _clean_series(load, "load")
    gen  = _clean_series(gen,  "generation")

    # ── Summary ───────────────────────────────────────────────────────────────
    print_summary(load, gen)

    # ── Save to canonical output paths ────────────────────────────────────────
    load.to_csv(ENTSOE_LOAD_CSV)
    gen.to_csv(ENTSOE_GEN_CSV)

    print(f"[0B] Load saved       -> {ENTSOE_LOAD_CSV}")
    print(f"[0B] Generation saved -> {ENTSOE_GEN_CSV}")

    # ── Final summary ─────────────────────────────────────────────────────────
    print("\n[0B] ── TASK 0B COMPLETE ──────────────────────────────────")
    yr = int(pd.Series(load.index.year).mode()[0])
    print(f"  Year              : {yr}")
    print(f"  {ENTSOE_LOAD_CSV.name}")
    print(f"    Rows   : {len(load)} | Missing: {load['load_MW'].isna().sum()} h")
    print(f"  {ENTSOE_GEN_CSV.name}")
    print(f"    Rows   : {len(gen)} | Carriers: {list(gen.columns)}")
    print("[0B] ─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    run_task_0b()
