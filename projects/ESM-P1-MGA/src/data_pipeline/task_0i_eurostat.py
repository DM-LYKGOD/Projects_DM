"""
task_0i_eurostat.py - Task 0I: Eurostat Industrial Electricity Consumption
===========================================================================
Downloads the Eurostat nrg_cb_pem dataset and filters for German industrial
electricity consumption.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    ALPHA_KWH_PER_TONNE,
    DESTATIS_END_YEAR,
    DESTATIS_START_YEAR,
    ENTSOE_LOAD_CSV,
    EUROSTAT_ELEC_CSV,
    TOTAL_DEMAND_TONNES,
)

EUROSTAT_DATASET = "nrg_cb_pem"
EUROSTAT_COUNTRY = "DE"
EUROSTAT_ENERGY_TYPE = "E7000"
EUROSTAT_SECTOR = "B-E"
EUROSTAT_UNIT = "GWh"

CEMENT_EL_TWH = ALPHA_KWH_PER_TONNE * TOTAL_DEMAND_TONNES / 1e9
INDUSTRIAL_SHARE_OF_LOAD = 0.30


def _load_eurostat_client():
    try:
        import eurostat
        return eurostat
    except ImportError as exc:
        raise ImportError("[0I] eurostat not installed. Run: pip install eurostat") from exc


def _download_nrg_cb_pem(eurostat) -> pd.DataFrame | None:
    """Download nrg_cb_pem from Eurostat."""
    print(f"[0I] Downloading Eurostat dataset: {EUROSTAT_DATASET} ...")
    try:
        df = eurostat.get_data_df(EUROSTAT_DATASET)
        print(f"[0I] Raw dataset: {len(df)} rows x {len(df.columns)} cols")
        return df
    except Exception as exc:
        print(f"[0I] Eurostat download failed: {exc}")
        return None


def _filter_de_electricity(df: pd.DataFrame) -> pd.DataFrame:
    """Filter Eurostat data to Germany, electricity, manufacturing, GWh."""
    cols = {c: str(c).strip().lower().replace("\\", "_").replace(" ", "_") for c in df.columns}
    df = df.rename(columns=cols)

    print(f"[0I] Available columns: {list(df.columns)}")

    geo_col = next((c for c in df.columns if "geo" in c or c == "geo_time_period"), None)
    if not geo_col:
        str_cols = [c for c in df.columns if df[c].dtype == object and c not in ("freq",)]
        geo_col = str_cols[-1] if str_cols else None
    print(f"[0I] Geographic column identified: {geo_col}")

    # nrg_bal column may be 'nrg_bal', 'nrg_bal_c', or similar depending on API version
    nrg_bal_col = next(
        (c for c in df.columns if c.startswith("nrg_bal")),
        None
    )
    if nrg_bal_col:
        print(f"[0I] Energy balance column identified: {nrg_bal_col}")
    else:
        print("[0I] WARNING: No nrg_bal* column found — skipping sector filter")

    # siec column (energy product) may be 'siec' or contain 'siec'
    siec_col = next((c for c in df.columns if "siec" in c), None)

    mask = pd.Series(True, index=df.index)
    for col_name, value in [
        (siec_col,    EUROSTAT_ENERGY_TYPE),
        (nrg_bal_col, EUROSTAT_SECTOR),
        ("unit",      EUROSTAT_UNIT),
        (geo_col,     EUROSTAT_COUNTRY),
    ]:
        if col_name and col_name in df.columns:
            mask &= df[col_name].astype(str).str.upper() == value.upper()
        else:
            if col_name:
                print(f"[0I] WARNING: column '{col_name}' not found, skipping filter")

    subset = df[mask].copy()
    print(f"[0I] After filter (DE, {EUROSTAT_ENERGY_TYPE}, {EUROSTAT_SECTOR}, {EUROSTAT_UNIT}): {len(subset)} rows")

    # If strict filter yields nothing, try relaxed: just DE + electricity type
    if len(subset) == 0 and geo_col and siec_col:
        print("[0I] Strict filter returned 0 rows — trying relaxed filter (DE + E7000 only) ...")
        mask2 = (
            df[geo_col].astype(str).str.upper() == EUROSTAT_COUNTRY
        ) & (
            df[siec_col].astype(str).str.upper() == EUROSTAT_ENERGY_TYPE
        )
        subset = df[mask2].copy()
        print(f"[0I] Relaxed filter: {len(subset)} rows")

    return subset


def _pivot_to_annual(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot the filtered dataframe to annual industrial electricity."""
    if df is None or len(df) == 0:
        return pd.DataFrame()

    year_cols = []
    for col in df.columns:
        try:
            year = int(col)
            if DESTATIS_START_YEAR <= year <= DESTATIS_END_YEAR + 1:
                year_cols.append(col)
        except (TypeError, ValueError):
            continue

    if not year_cols:
        print("[0I] WARNING: No year columns found in eurostat output")
        return pd.DataFrame()

    row = df.iloc[0]
    annual_data = {int(col): pd.to_numeric(row[col], errors="coerce") for col in year_cols}
    result = pd.DataFrame.from_dict(annual_data, orient="index", columns=["indust_elec_GWh"])
    result.index.name = "year"
    result["indust_elec_TWh"] = result["indust_elec_GWh"] / 1e3
    return result.dropna().sort_index()


def _cross_validate(result: pd.DataFrame) -> None:
    """Cross-validate industrial electricity consumption against rough checks."""
    print("\n  -- Cross-Validation -----------------------------------")

    if ENTSOE_LOAD_CSV.exists():
        try:
            load_df = pd.read_csv(ENTSOE_LOAD_CSV, index_col=0, parse_dates=True)
            total_twh_2023 = load_df.sum().values[0] / 1e6
            implied_indust_twh = total_twh_2023 * INDUSTRIAL_SHARE_OF_LOAD
            print(f"  ENTSO-E total load 2023  : {total_twh_2023:.1f} TWh")
            print(f"  Implied industrial (30%) : {implied_indust_twh:.1f} TWh")

            if 2023 in result.index:
                eurostat_twh = result.loc[2023, "indust_elec_TWh"]
                delta = abs(implied_indust_twh - eurostat_twh)
                pct = delta / implied_indust_twh * 100 if implied_indust_twh else float("nan")
                print(f"  Eurostat industrial      : {eurostat_twh:.1f} TWh")
                print(f"  Delta                    : {delta:.1f} TWh ({pct:.1f}%)")
        except Exception as exc:
            print(f"  ENTSO-E check skipped: {exc}")
    else:
        print(f"  ENTSO-E check skipped (file not found: {ENTSOE_LOAD_CSV.name})")

    cement_twh = CEMENT_EL_TWH
    print(f"\n  Cement expected electricity : {cement_twh:.2f} TWh/yr")
    print(f"  (alpha={ALPHA_KWH_PER_TONNE} kWh/t x {TOTAL_DEMAND_TONNES / 1e6:.0f} Mt)")

    if 2023 in result.index:
        total_de_twh = result.loc[2023, "indust_elec_TWh"]
        cement_share = cement_twh / total_de_twh * 100 if total_de_twh else float("nan")
        print(f"  Cement share of industrial : {cement_share:.1f}%")

    print("  --------------------------------------------------------\n")


def print_annual_table(result: pd.DataFrame) -> None:
    """Print the annual industrial electricity table."""
    print("\n  Industrial Electricity Consumption - Germany")
    print(f"  {'Year':>6}  {'Industrial (TWh)':>17}  {'Cement share est. (%)':>22}")
    print("  " + "-" * 50)
    for year, row in result.iterrows():
        twh = row["indust_elec_TWh"]
        cement_pct = CEMENT_EL_TWH / twh * 100 if twh > 0 else float("nan")
        print(f"  {int(year):>6}  {twh:>17.1f}  {cement_pct:>22.2f}")


def run_task_0i() -> None:
    """Main entry point for Task 0I."""
    print("\n" + "=" * 60)
    print("  TASK 0I - Eurostat Industrial Electricity Consumption")
    print("=" * 60)

    if EUROSTAT_ELEC_CSV.exists():
        print(f"[0I] Cached output found: {EUROSTAT_ELEC_CSV}. Skipping download.")
        print("\n[0I] -------- TASK 0I COMPLETE (cached) --------\n")
        return

    result = None
    try:
        eurostat = _load_eurostat_client()
        raw_df = _download_nrg_cb_pem(eurostat)
        if raw_df is not None and len(raw_df) > 0:
            filtered = _filter_de_electricity(raw_df)
            result = _pivot_to_annual(filtered)
    except Exception as exc:
        print(f"[0I] Eurostat pipeline error: {exc}")

    if result is None or len(result) == 0:
        raise RuntimeError(
            "[0I] Eurostat data could not be retrieved. "
            "Synthetic fallback has been removed to avoid fabricated results."
        )

    print_annual_table(result)
    _cross_validate(result)
    result.to_csv(EUROSTAT_ELEC_CSV)
    print(f"[0I] Annual industrial electricity saved -> {EUROSTAT_ELEC_CSV}")


if __name__ == "__main__":
    run_task_0i()
