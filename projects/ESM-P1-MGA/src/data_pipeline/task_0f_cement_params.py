"""
task_0f_cement_params.py - Task 0F: VDZ Cement Industry Parameters
===================================================================
Builds and persists cement industry techno-economic parameters, with
traceability to the VDZ Environmental Data 2023 source document.

Manual download required:
  1. Go to the VDZ publication page
  2. Download the PDF
  3. Save it to data/industrial/vdz_environmental_data_2023.pdf
  4. Re-run this script

Outputs:
  data/industrial/cement_parameters.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    ALPHA_KWH_PER_TONNE,
    CEMENT_PARAMS_JSON,
    INDUSTRIAL_DIR,
    MIN_LOAD_FRAC,
    RAMP_LIMIT_FRAC,
    RATED_CAPACITY_T_H,
    S_MAX_DAYS,
    S_MAX_TONNES,
    TOTAL_DEMAND_TONNES,
)


# Try several common save-as names for the VDZ report
_VDZ_PDF_CANDIDATES = [
    "vdz_environmental_data_2023.pdf",
    "VDZ_Umweltdaten_Environmental_Data_2023.pdf",
    "VDZ_Environmental_Data_2023.pdf",
    "vdz_umweltdaten_2023.pdf",
]

VDZ_PDF_PATH = next(
    (INDUSTRIAL_DIR / name for name in _VDZ_PDF_CANDIDATES
     if (INDUSTRIAL_DIR / name).exists()),
    INDUSTRIAL_DIR / _VDZ_PDF_CANDIDATES[0],   # default (used in error messages)
)

VDZ_REFERENCE_URL = (
    "https://www.vdz-online.de/en/knowledge-base/"
    "publications/environmental-data-of-the-german-cement-industry-2023"
)



def _ensure_pdf_available(pdf_path: Path) -> None:
    """Fail closed unless the VDZ source PDF is present."""
    if not pdf_path.exists():
        raise RuntimeError(
            f"[0F] Required source PDF not found at {pdf_path}. "
            "Download the VDZ report first to avoid unverified parameter outputs."
        )


def _try_extract_from_pdf(pdf_path: Path) -> dict:
    """
    Attempt to extract key parameters from the VDZ PDF.
    Returns extracted values for traceability checks.
    """
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "[0F] pdfplumber is required to inspect the VDZ source PDF. "
            "Install it with: pip install pdfplumber"
        ) from exc

    _ensure_pdf_available(pdf_path)
    print(f"[0F] Attempting PDF extraction from {pdf_path.name} ...")
    extracted = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages[:30]:
                text = page.extract_text() or ""
                full_text += text + "\n"

        import re

        matches_kwh = re.findall(r"(\d+[\.,]?\d*)\s*kWh[\/\s]*t", full_text)
        if matches_kwh:
            vals = [float(m.replace(",", ".")) for m in matches_kwh]
            elec_vals = [v for v in vals if 80 <= v <= 150]
            if elec_vals:
                extracted["alpha_kwh_per_tonne"] = elec_vals[0]
                print(f"[0F]   Found alpha = {elec_vals[0]} kWh/t from PDF")

        matches_mt = re.findall(
            r"(\d+[\.,]?\d*)\s*(?:million tonnes?|Mt|Mio\.?\s*t)",
            full_text,
            re.IGNORECASE,
        )
        if matches_mt:
            vals = [float(m.replace(",", ".")) for m in matches_mt]
            prod_vals = [v for v in vals if 20 <= v <= 40]
            if prod_vals:
                extracted["total_demand_tonnes"] = prod_vals[0] * 1e6
                print(f"[0F]   Found total_demand = {prod_vals[0]} Mt from PDF")

    except Exception as exc:
        raise RuntimeError(
            f"[0F] PDF extraction failed: {exc}. "
            "Parameter export is blocked to avoid unverified results."
        ) from exc

    if "alpha_kwh_per_tonne" not in extracted or "total_demand_tonnes" not in extracted:
        raise RuntimeError(
            "[0F] Could not confirm key parameters from the VDZ PDF. "
            "Parameter export is blocked to avoid unverified results."
        )

    return extracted


def build_parameters(pdf_values: dict) -> dict:
    """Construct the full cement parameter dictionary with source metadata."""
    params = {
        "alpha_kwh_per_tonne": pdf_values["alpha_kwh_per_tonne"],
        "total_demand_tonnes": pdf_values["total_demand_tonnes"],
        "total_demand_Mt": pdf_values["total_demand_tonnes"] / 1e6,
        "rated_capacity_t_h": RATED_CAPACITY_T_H,
        "rated_capacity_Mt_yr": RATED_CAPACITY_T_H * 8760 / 1e6,
        "ramp_limit_frac": RAMP_LIMIT_FRAC,
        "ramp_limit_t_h": RATED_CAPACITY_T_H * RAMP_LIMIT_FRAC,
        "s_max_days": S_MAX_DAYS,
        "s_max_tonnes": S_MAX_TONNES,
        "min_load_frac": MIN_LOAD_FRAC,
        "min_load_t_h": RATED_CAPACITY_T_H * MIN_LOAD_FRAC,
        "thermal_kwh_per_tonne": 780,
        "avg_heat_value_gj_t": 2.81,
        "process_co2_kg_t": 520,
        "energy_co2_kg_t": 160,
        "source": "VDZ Environmental Data 2023",
        "reference": VDZ_REFERENCE_URL,
        "extraction_method": "pdf_verified_core_values",
        "baseline_defaults": {
            "alpha_kwh_per_tonne_config": ALPHA_KWH_PER_TONNE,
            "total_demand_tonnes_config": TOTAL_DEMAND_TONNES,
        },
        "units": {
            "alpha_kwh_per_tonne": "kWh_el/tonne cement",
            "total_demand_tonnes": "tonnes/year",
            "rated_capacity_t_h": "tonnes/hour",
            "ramp_limit_frac": "fraction of rated capacity per hour",
            "ramp_limit_t_h": "tonnes/hour/hour",
            "s_max_days": "days",
            "s_max_tonnes": "tonnes",
            "min_load_frac": "fraction of rated capacity",
            "min_load_t_h": "tonnes/hour",
            "thermal_kwh_per_tonne": "kWh_th/tonne clinker",
            "avg_heat_value_gj_t": "GJ/tonne clinker",
            "process_co2_kg_t": "kg CO2/tonne clinker (calcination only)",
            "energy_co2_kg_t": "kg CO2/tonne clinker (fuel combustion)",
        },
    }

    params["annual_elec_demand_GWh"] = (
        params["alpha_kwh_per_tonne"] * params["total_demand_tonnes"] / 1e6
    )
    params["annual_elec_demand_TWh"] = params["annual_elec_demand_GWh"] / 1e3
    return params


def print_parameters(params: dict) -> None:
    """Pretty-print all parameters with units."""
    print("\n  Cement Industry Parameters")
    print("  " + "-" * 61)
    units = params.get("units", {})
    skip = {"units", "source", "reference", "extraction_method", "baseline_defaults"}
    for key, value in params.items():
        if key in skip:
            continue
        unit = units.get(key, "")
        if isinstance(value, float):
            print(f"  {key:<35} {value:>15.2f}   {unit}")
        else:
            print(f"  {key:<35} {str(value):>15}   {unit}")
    print(f"\n  Source: {params['source']}")
    print(f"  Method: {params['extraction_method']}")
    print("  " + "-" * 61 + "\n")


def run_task_0f() -> None:
    """Main entry point for Task 0F."""
    print("\n" + "=" * 60)
    print("  TASK 0F - VDZ Cement Industry Parameters")
    print("=" * 60)
    print("\n  Required source document:")
    print(f"  {VDZ_REFERENCE_URL}")
    print(f"  Local PDF path: {VDZ_PDF_PATH}\n")

    if CEMENT_PARAMS_JSON.exists():
        print(f"[0F] Cached parameters found: {CEMENT_PARAMS_JSON}. Skipping rebuild.")
        print("\n[0F] -------- TASK 0F COMPLETE (cached) --------\n")
        return

    pdf_values = _try_extract_from_pdf(VDZ_PDF_PATH)
    params = build_parameters(pdf_values)
    print_parameters(params)

    with open(CEMENT_PARAMS_JSON, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
    print(f"[0F] Parameters saved -> {CEMENT_PARAMS_JSON}")


if __name__ == "__main__":
    run_task_0f()
