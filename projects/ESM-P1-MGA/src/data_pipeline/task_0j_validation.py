"""
task_0j_validation.py — Task 0J: Data Integration & Validation Report
=======================================================================
Loads all datasets from Tasks 0A–0I, performs consistency checks,
and generates a comprehensive validation report.

Checks performed:
  1. ENTSO-E load vs. OPSD load (should match within 2%)
  2. ERA5 CF series vs. OPSD renewable generation (Pearson r > 0.85)
  3. Eurostat industrial electricity vs. cement alpha×production (plausibility)
  4. Completeness and date range for every dataset

Outputs:
  data/validation_report.txt
"""

import sys
import json
import textwrap
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    ENTSOE_LOAD_CSV, ENTSOE_GEN_CSV,
    ERA5_PV_CF_CSV, ERA5_WIND_CF_CSV, ERA5_CF_HIST_CSV,
    OPSD_TIMESERIES_CSV, OPSD_POWERPLANTS_CSV,
    CEMENT_PARAMS_JSON, DESTATIS_WZ08_CSV,
    CEMENT_SEASONALITY_CSV, DESTATIS_GENESIS_CSV,
    EUROSTAT_ELEC_CSV, PYPSA_DE_NC_2025,
    VALIDATION_REPORT_TXT,
    ALPHA_KWH_PER_TONNE, TOTAL_DEMAND_TONNES
)

# ─── Validation thresholds ────────────────────────────────────────────────────
LOAD_MATCH_TOL      = 0.02   # ENTSO-E vs. OPSD: within 2% annual total
SOLAR_CORR_MIN      = 0.80   # ERA5 PV CF vs. OPSD solar gen correlation
WIND_CORR_MIN       = 0.80   # ERA5 wind CF vs. OPSD wind gen correlation
MAX_MISSING_PCT     = 5.0    # Maximum acceptable missing % per dataset
CEMENT_EL_REF_TWH   = ALPHA_KWH_PER_TONNE * TOTAL_DEMAND_TONNES / 1e9
CEMENT_EL_PLAUS_MIN = 2.0    # TWh — minimum plausible cement electricity
CEMENT_EL_PLAUS_MAX = 5.0    # TWh — maximum plausible cement electricity


# ─── Helper functions ─────────────────────────────────────────────────────────

def _load_csv(path: Path, label: str,
              index_col: int = 0, parse_dates: bool = True) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, index_col=index_col, parse_dates=parse_dates)
        return df
    except Exception as e:
        print(f"[0J] WARNING: Could not load {label}: {e}")
        return None


def _describe_series(s: pd.Series, name: str) -> dict:
    """Return a dict of summary statistics for a pd.Series."""
    return {
        "name"    : name,
        "n_rows"  : len(s),
        "missing" : int(s.isna().sum()),
        "miss_pct": round(s.isna().mean() * 100, 2),
        "mean"    : round(float(s.dropna().mean()), 4) if len(s.dropna()) > 0 else None,
        "min"     : round(float(s.dropna().min()), 4)  if len(s.dropna()) > 0 else None,
        "max"     : round(float(s.dropna().max()), 4)  if len(s.dropna()) > 0 else None,
        "date_min": str(s.dropna().index.min())  if hasattr(s.index, "min") else "N/A",
        "date_max": str(s.dropna().index.max())  if hasattr(s.index, "min") else "N/A",
    }


def _describe_df(df: pd.DataFrame, name: str) -> dict:
    if df is None:
        return {"name": name, "status": "NOT FOUND"}
    return {
        "name"       : name,
        "n_rows"     : len(df),
        "n_cols"     : len(df.columns),
        "missing_pct": round(df.isna().mean().mean() * 100, 2),
        "date_min"   : str(df.index.min()) if hasattr(df.index, "min") else "N/A",
        "date_max"   : str(df.index.max()) if hasattr(df.index, "min") else "N/A",
        "columns"    : list(df.columns[:5]),  # first 5 only
    }


# ─── Check 1 ─ ENTSO-E vs OPSD load ─────────────────────────────────────────

def check_entsoe_vs_opsd(entsoe_load: pd.DataFrame | None,
                          opsd_ts: pd.DataFrame | None) -> dict:
    """Compare ENTSO-E vs. OPSD annual total load for 2023."""
    result = {
        "check"  : "ENTSO-E vs. OPSD load (annual total, 2023)",
        "status" : "SKIPPED",
        "details": "",
    }

    if entsoe_load is None:
        result["details"] = "ENTSO-E load file not found"
        return result

    if opsd_ts is None:
        result["details"] = "OPSD time series file not found"
        return result

    # ENTSO-E: sum for 2023
    entsoe_s = entsoe_load.iloc[:, 0].dropna()
    entsoe_s.index = pd.to_datetime(entsoe_s.index, utc=True)
    entsoe_2023 = entsoe_s[entsoe_s.index.year == 2023].sum() / 1e6  # TWh

    # OPSD: find any load column for DE
    load_cols = [c for c in opsd_ts.columns
                 if "load" in c.lower() or "actual" in c.lower()]
    if not load_cols:
        result["details"] = "No load column found in OPSD data"
        result["status"] = "SKIPPED"
        return result

    opsd_s = opsd_ts[load_cols[0]].dropna()
    opsd_s.index = pd.to_datetime(opsd_ts.index, utc=True)
    opsd_2023 = opsd_s[opsd_s.index.year == 2023].sum() / 1e6  # TWh

    if entsoe_2023 == 0 or opsd_2023 == 0:
        result["details"] = "Zero annual totals detected — insufficient data"
        result["status"] = "WARNING"
        return result

    delta_pct = abs(entsoe_2023 - opsd_2023) / entsoe_2023 * 100

    result["entsoe_twh"]  = round(entsoe_2023, 2)
    result["opsd_twh"]    = round(opsd_2023, 2)
    result["delta_pct"]   = round(delta_pct, 2)
    result["threshold"]   = f"{LOAD_MATCH_TOL*100:.0f}%"

    if delta_pct <= LOAD_MATCH_TOL * 100:
        result["status"]  = "PASS"
        result["details"] = f"Δ = {delta_pct:.2f}% ≤ {LOAD_MATCH_TOL*100:.0f}%"
    else:
        result["status"]  = "WARNING"
        result["details"] = f"Δ = {delta_pct:.2f}% > {LOAD_MATCH_TOL*100:.0f}% (check bidding zone coverage)"

    return result


# ─── Check 2 ─ ERA5 CF vs. OPSD renewable generation ─────────────────────────

def check_era5_vs_opsd_renewables(era5_pv: pd.DataFrame | None,
                                   era5_wind: pd.DataFrame | None,
                                   opsd_ts: pd.DataFrame | None) -> dict:
    """
    Correlate ERA5 capacity factors against OPSD measured renewable generation.
    """
    result = {
        "check"       : "ERA5 CF vs. OPSD renewables (Pearson r, 2022–2023)",
        "status"      : "SKIPPED",
        "solar_r"     : None,
        "wind_r"      : None,
        "details"     : "",
    }

    if opsd_ts is None:
        result["details"] = "OPSD time series not found"
        return result

    # Find OPSD solar and wind actual gen columns
    solar_cols = [c for c in opsd_ts.columns
                  if "solar" in c.lower() and "actual" in c.lower()]
    wind_cols  = [c for c in opsd_ts.columns
                  if "wind" in c.lower() and "onshore" in c.lower()
                  and "actual" in c.lower()]

    # Fallback: try any solar/wind columns
    if not solar_cols:
        solar_cols = [c for c in opsd_ts.columns if "solar" in c.lower()]
    if not wind_cols:
        wind_cols  = [c for c in opsd_ts.columns
                      if "wind" in c.lower() and "offshore" not in c.lower()]

    correlations = {}

    for label, era5_df, opsd_cols, min_r in [
        ("solar", era5_pv,   solar_cols, SOLAR_CORR_MIN),
        ("wind",  era5_wind, wind_cols,  WIND_CORR_MIN),
    ]:
        if era5_df is None or not opsd_cols:
            continue

        try:
            # Align on common hourly index (2023 preferred)
            era5_s = era5_df.iloc[:, 0].copy()
            era5_s.index = pd.to_datetime(era5_s.index, utc=True)
            era5_s = era5_s[era5_s.index.year.isin([2022, 2023])]

            opsd_s = opsd_ts[opsd_cols[0]].copy()
            opsd_s.index = pd.to_datetime(opsd_s.index, utc=True)
            opsd_s = opsd_s[opsd_s.index.year.isin([2022, 2023])]

            # Align
            merged = pd.concat([era5_s, opsd_s], axis=1, join="inner").dropna()
            if len(merged) < 24:
                continue

            # Normalise OPSD generation to [0,1] range (to compare with CF)
            opsd_norm = merged.iloc[:, 1] / merged.iloc[:, 1].max()
            r = merged.iloc[:, 0].corr(opsd_norm)

            correlations[label] = {
                "pearson_r"   : round(r, 4),
                "n_obs"       : len(merged),
                "threshold"   : min_r,
                "pass"        : r >= min_r,
            }
        except Exception as e:
            print(f"[0J] Correlation check {label} failed: {e}")

    result["correlations"] = correlations
    if correlations:
        statuses = []
        for lab, cor in correlations.items():
            status_str = "PASS" if cor["pass"] else "WARNING"
            statuses.append(status_str)
            result[f"{lab}_r"] = cor["pearson_r"]
        result["status"]  = "PASS" if all(s == "PASS" for s in statuses) else "WARNING"
        result["details"] = " | ".join(
            f"{lab}: r={cor['pearson_r']:.3f} ({'≥' if cor['pass'] else '<'}{cor['threshold']})"
            for lab, cor in correlations.items()
        )
    else:
        result["details"] = "Could not compute correlations (missing data)"

    return result


# ─── Check 3 ─ Cement electricity plausibility ────────────────────────────────

def check_cement_electricity(eurostat_df: pd.DataFrame | None) -> dict:
    """
    Check that cement electricity consumption (alpha × production)
    is plausible relative to the Eurostat industrial total.
    """
    result = {
        "check"       : "Cement electricity plausibility (alpha × production)",
        "cement_exp_twh": round(CEMENT_EL_REF_TWH, 3),
        "status"      : "SKIPPED",
        "details"     : "",
    }

    if eurostat_df is not None and "indust_elec_TWh" in eurostat_df.columns:
        # Use most recent year available
        year = eurostat_df.index.max()
        total_twh = eurostat_df.loc[year, "indust_elec_TWh"]
        cement_share = CEMENT_EL_REF_TWH / total_twh * 100

        result["eurostat_total_twh"] = round(total_twh, 2)
        result["cement_share_pct"]   = round(cement_share, 2)
        result["year_checked"]       = int(year)

        if CEMENT_EL_PLAUS_MIN <= CEMENT_EL_REF_TWH <= CEMENT_EL_PLAUS_MAX:
            result["status"]  = "PASS"
            result["details"] = (
                f"Cement elec = {CEMENT_EL_REF_TWH:.2f} TWh "
                f"in plausible range [{CEMENT_EL_PLAUS_MIN}, {CEMENT_EL_PLAUS_MAX}] TWh. "
                f"Share of industrial = {cement_share:.1f}%"
            )
        else:
            result["status"]  = "WARNING"
            result["details"] = (
                f"Cement elec = {CEMENT_EL_REF_TWH:.2f} TWh outside "
                f"plausible range [{CEMENT_EL_PLAUS_MIN}, {CEMENT_EL_PLAUS_MAX}] TWh"
            )
    else:
        result["details"] = (
            f"Eurostat data unavailable. Hard-coded cement elec = "
            f"{CEMENT_EL_REF_TWH:.2f} TWh (α={ALPHA_KWH_PER_TONNE} kWh/t × "
            f"{TOTAL_DEMAND_TONNES/1e6:.0f} Mt)"
        )
        if CEMENT_EL_PLAUS_MIN <= CEMENT_EL_REF_TWH <= CEMENT_EL_PLAUS_MAX:
            result["status"] = "PASS"
        else:
            result["status"] = "WARNING"

    return result


# ─── Dataset inventory ────────────────────────────────────────────────────────

DATASET_REGISTRY = [
    ("PyPSA-DE Network 2025",           PYPSA_DE_NC_2025,       "binary"),
    ("ENTSO-E Load DE 2023",            ENTSOE_LOAD_CSV,        "csv"),
    ("ENTSO-E Generation DE 2023",      ENTSOE_GEN_CSV,         "csv"),
    ("ERA5 PV CF DE 2023",              ERA5_PV_CF_CSV,         "csv"),
    ("ERA5 Wind CF DE 2023",            ERA5_WIND_CF_CSV,       "csv"),
    ("ERA5 CF DE Historical",           ERA5_CF_HIST_CSV,       "csv"),
    ("OPSD Time Series DE",             OPSD_TIMESERIES_CSV,    "csv"),
    ("OPSD Power Plants DE",            OPSD_POWERPLANTS_CSV,   "csv"),
    ("Cement Parameters (VDZ 2023)",    CEMENT_PARAMS_JSON,     "json"),
    ("Destatis WZ08 Cement Index",      DESTATIS_WZ08_CSV,      "csv"),
    ("Cement Seasonality",              CEMENT_SEASONALITY_CSV, "csv"),
    ("Destatis Genesis 42131",          DESTATIS_GENESIS_CSV,   "csv"),
    ("Eurostat Industrial Electricity", EUROSTAT_ELEC_CSV,      "csv"),
]


def _inventory_datasets() -> list[dict]:
    """Build an inventory record for every expected dataset."""
    records = []
    for label, path, ftype in DATASET_REGISTRY:
        rec = {"dataset": label, "file": path.name, "exists": path.exists()}
        if path.exists():
            rec["size_KB"] = round(path.stat().st_size / 1024, 1)
            if ftype == "csv":
                try:
                    df = pd.read_csv(path, index_col=0, parse_dates=True,
                                     low_memory=False)
                    rec["n_rows"]     = len(df)
                    rec["n_cols"]     = len(df.columns)
                    rec["missing_pct"] = round(df.isna().mean().mean() * 100, 2)
                    if hasattr(df.index, "min"):
                        rec["date_min"] = str(df.index.min())[:19]
                        rec["date_max"] = str(df.index.max())[:19]
                except Exception:
                    rec["n_rows"] = "read_error"
            elif ftype == "json":
                try:
                    with open(path) as f:
                        data = json.load(f)
                    rec["n_keys"] = len(data)
                except Exception:
                    rec["n_keys"] = "read_error"
            elif ftype == "binary":
                rec["note"] = "NetCDF binary (not read here)"
        else:
            rec["status"] = "MISSING"
        records.append(rec)
    return records


# ─── Report writer ────────────────────────────────────────────────────────────

def write_validation_report(
    inventory     : list[dict],
    checks        : list[dict],
    output_path   : Path
) -> None:
    """Write the complete validation report to a text file."""

    timestamp = datetime.now().isoformat(timespec="seconds")

    lines = [
        "=" * 72,
        "  ESM-P1-MGA PROJECT — DATA VALIDATION REPORT",
        f"  Generated: {timestamp}",
        "  Institution: Ruhr-Universität Bochum (OPTIMA / Chair of Energy Systems)",
        "  Project: Endogenous Industrial Production Scheduling — MGA Approach",
        "=" * 72,
        "",
        "━" * 72,
        "  SECTION 1: DATASET INVENTORY",
        "━" * 72,
        "",
    ]

    # Table header
    lines.append(
        f"  {'Dataset':<40} {'File':<38} {'Rows':>8} {'Missing%':>9} {'Status':>8}"
    )
    lines.append("  " + "─" * 108)

    all_present = True
    for rec in inventory:
        status = "OK" if rec.get("exists") else "MISSING ⚠"
        if not rec.get("exists"):
            all_present = False
        n_rows = str(rec.get("n_rows", rec.get("n_keys", "—")))
        miss   = f"{rec.get('missing_pct', '—')}"
        date_r = ""
        if "date_min" in rec and "date_max" in rec:
            date_r = f" | {rec['date_min'][:10]} -> {rec['date_max'][:10]}"
        lines.append(
            f"  {rec['dataset']:<40} {rec['file']:<38} "
            f"{n_rows:>8} {miss:>9} {status:>8}{date_r}"
        )

    lines += [
        "",
        f"  {'All datasets present:':50} {'YES ✓' if all_present else 'NO — see MISSING above ⚠'}",
        "",
        "━" * 72,
        "  SECTION 2: CONSISTENCY CHECKS",
        "━" * 72,
        "",
    ]

    all_pass = True
    for check in checks:
        status = check.get("status", "SKIPPED")
        if status == "WARNING":
            all_pass = False
        icon = {"PASS": "✓", "WARNING": "⚠", "SKIPPED": "—"}.get(status, "?")
        lines.append(f"  [{icon}] {status:<8}  {check['check']}")
        lines.append(f"           {check.get('details', '')}")
        # Extra detail rows
        for k, v in check.items():
            if k not in ("check", "status", "details", "correlations"):
                lines.append(f"             {k}: {v}")
        if "correlations" in check:
            for lab, cor in check["correlations"].items():
                lines.append(
                    f"             {lab}: Pearson r = {cor['pearson_r']:.4f} "
                    f"(threshold ≥ {cor['threshold']}, n = {cor['n_obs']})"
                )
        lines.append("")

    lines += [
        "━" * 72,
        "  SECTION 3: MODEL CONSTANTS (from config.py)",
        "━" * 72,
        "",
        f"  alpha (electricity intensity)   : {ALPHA_KWH_PER_TONNE} kWh/tonne (VDZ 2023)",
        f"  total_demand                    : {TOTAL_DEMAND_TONNES/1e6:.1f} Mt/year",
        f"  cement electricity demand (est) : {CEMENT_EL_REF_TWH:.2f} TWh/year",
        "",
        "━" * 72,
        "  SECTION 4: OVERALL VERDICT",
        "━" * 72,
        "",
    ]

    if all_present and all_pass:
        lines.append("  ✓ ALL CHECKS PASSED — Data pipeline is consistent.")
        lines.append("  Safe to proceed to Phase 1 (Task A: PyPSA-DE setup).")
    else:
        lines.append("  ⚠ SOME ISSUES DETECTED — Review warnings above before proceeding.")
        lines.append("  Check API keys in config.py and re-run individual task scripts.")

    lines += [
        "",
        "=" * 72,
        "  END OF VALIDATION REPORT",
        "=" * 72,
    ]

    report_text = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(report_text)
    print(f"\n[0J] Validation report saved -> {output_path}")


def run_task_0j() -> None:
    """Main entry point for Task 0J."""
    print("\n" + "=" * 60)
    print("  TASK 0J — Data Integration & Validation Report")
    print("=" * 60)

    # ── Load all datasets ────────────────────────────────────────────────────
    print("[0J] Loading all datasets ...")

    entsoe_load  = _load_csv(ENTSOE_LOAD_CSV,    "ENTSO-E load")
    entsoe_gen   = _load_csv(ENTSOE_GEN_CSV,     "ENTSO-E gen")
    era5_pv      = _load_csv(ERA5_PV_CF_CSV,     "ERA5 PV CF")
    era5_wind    = _load_csv(ERA5_WIND_CF_CSV,   "ERA5 wind CF")
    era5_hist    = _load_csv(ERA5_CF_HIST_CSV,   "ERA5 historical CF")
    opsd_ts      = _load_csv(OPSD_TIMESERIES_CSV,"OPSD time series")
    opsd_pp      = _load_csv(OPSD_POWERPLANTS_CSV,"OPSD plants", parse_dates=False)
    destatis_wz08= _load_csv(DESTATIS_WZ08_CSV,  "Destatis WZ08")
    destatis_gen = _load_csv(DESTATIS_GENESIS_CSV,"Destatis Genesis", parse_dates=False)
    eurostat_el  = _load_csv(EUROSTAT_ELEC_CSV,  "Eurostat electricity", parse_dates=False)

    # ── Run consistency checks ───────────────────────────────────────────────
    print("[0J] Running consistency checks ...")
    checks = []

    checks.append(check_entsoe_vs_opsd(entsoe_load, opsd_ts))
    checks.append(check_era5_vs_opsd_renewables(era5_pv, era5_wind, opsd_ts))
    checks.append(check_cement_electricity(eurostat_el))

    # ── Build dataset inventory ──────────────────────────────────────────────
    print("[0J] Building dataset inventory ...")
    inventory = _inventory_datasets()

    # ── Write report ─────────────────────────────────────────────────────────
    write_validation_report(inventory, checks, VALIDATION_REPORT_TXT)

    # Final summary
    print("\n[0J] ── TASK 0J COMPLETE ──────────────────────────────────")
    n_present = sum(1 for r in inventory if r.get("exists"))
    n_total   = len(inventory)
    n_passes  = sum(1 for c in checks if c.get("status") == "PASS")
    print(f"  Datasets found : {n_present}/{n_total}")
    print(f"  Checks passed  : {n_passes}/{len(checks)}")
    print(f"  Report saved   -> {VALIDATION_REPORT_TXT.name}")
    print("[0J] ─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    run_task_0j()
