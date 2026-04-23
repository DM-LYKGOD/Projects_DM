"""
config.py — Central configuration for ESM-P1 MGA project.
All API keys, directory paths, and project constants live here.
================================================
INSTRUCTIONS FOR USER:
1. Fill in ENTSOE_API_KEY  -> register free at https://transparency.entsoe.eu
2. Fill in CDS_API_KEY     -> register free at https://cds.climate.copernicus.eu
3. Fill in GENESIS_USER / GENESIS_PW -> register free at https://www-genesis.destatis.de
"""

import os
from pathlib import Path

# ─── Load credentials from .env file (if present) ─────────────────────────────
# Install: pip install python-dotenv
# Create a local '.env' file (see .env.example) — never commit it to git.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed; fall back to system environment variables

# ─── API CREDENTIALS (loaded from environment / .env file) ──────────────────
# Set these in a local .env file or as system environment variables.
# Never commit real credentials to version control.
ENTSOE_API_KEY = os.environ.get("ENTSOE_API_KEY", "YOUR_ENTSOE_API_KEY")
CDS_API_KEY = os.environ.get("CDS_API_KEY", "YOUR_CDS_API_KEY")
CDS_API_URL = "https://cds.climate.copernicus.eu/api"  # new CDS API (2024+)
GENESIS_USER = os.environ.get("GENESIS_USER", "")
GENESIS_PW = os.environ.get("GENESIS_PW", "")

# ─── PROJECT ROOT & DATA DIRECTORIES ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

DATA_DIR = PROJECT_ROOT / "data"
ENERGY_DIR = DATA_DIR / "energy"
INDUSTRIAL_DIR = DATA_DIR / "industrial"
CLIMATE_DIR = DATA_DIR / "climate"
FIGURES_DIR = DATA_DIR / "figures"

# Create all directories on import
for _d in [ENERGY_DIR, INDUSTRIAL_DIR, CLIMATE_DIR, FIGURES_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ─── OUTPUT FILE PATHS ─────────────────────────────────────────────────────────
# Task 0A
PYPSA_DE_NC_2025 = ENERGY_DIR / "pypsa_de_2025.nc"
PREFERRED_PYPSA_DE_NETWORK_FILENAME = "elec_s_37.nc"
PREFERRED_PYPSA_DE_BUS_COUNT = 37
ALLOW_DATA_FALLBACKS = True

# Task 0B
ENTSOE_LOAD_CSV = ENERGY_DIR / "entsoe_load_DE_2023.csv"
ENTSOE_GEN_CSV = ENERGY_DIR / "entsoe_generation_DE_2023.csv"

# Task 0C
ERA5_PV_CF_CSV = CLIMATE_DIR / "era5_pv_cf_DE_2023.csv"
ERA5_WIND_CF_CSV = CLIMATE_DIR / "era5_wind_cf_DE_2023.csv"

# Task 0D
ERA5_CF_HIST_CSV = CLIMATE_DIR / "era5_cf_DE_historical.csv"

# Task 0E
OPSD_TIMESERIES_CSV = ENERGY_DIR / "opsd_timeseries_DE.csv"
OPSD_POWERPLANTS_CSV = ENERGY_DIR / "opsd_powerplants_DE.csv"

# Task 0F
CEMENT_PARAMS_JSON = INDUSTRIAL_DIR / "cement_parameters.json"
NUTS3_CEMENT_WEIGHTS_CSV = INDUSTRIAL_DIR / "cement_nuts3_weights_2022.csv"

# Task 0G
DESTATIS_WZ08_CSV = INDUSTRIAL_DIR / "destatis_wz08_cement.csv"
CEMENT_SEASONALITY_CSV = INDUSTRIAL_DIR / "cement_seasonality.csv"
CEMENT_SEASONALITY_PNG = INDUSTRIAL_DIR / "cement_seasonality.png"

# Task 0H
DESTATIS_GENESIS_CSV = INDUSTRIAL_DIR / "destatis_cement_production_annual.csv"

# Task 0I
EUROSTAT_ELEC_CSV = INDUSTRIAL_DIR / "eurostat_industrial_elec_DE.csv"

# Task 0J
VALIDATION_REPORT_TXT = DATA_DIR / "validation_report.txt"

# Model phase outputs
BASELINE_SOLVED_NC = ENERGY_DIR / "baseline_solved_2025.nc"
INDUSTRIAL_SOLVED_NC = ENERGY_DIR / "industrial_solved_2025.nc"
MGA_RESULTS_CSV = INDUSTRIAL_DIR / "mga_alternatives.csv"
PHASE3_RESULTS_CSV = INDUSTRIAL_DIR / "phase3_results_summary.csv"

# ─── CYBER-PHYSICAL MODEL CONSTANTS ───────────────────────────────────────────
ALPHA_KWH_PER_TONNE = 109.0  # electricity intensity (VDZ 2023)
TOTAL_DEMAND_TONNES = 28e6  # annual German cement demand (tonnes/year)
RATED_CAPACITY_T_H = 4450.0  # installed capacity (t/h); utilisation ~72% = 28Mt/yr
RAMP_LIMIT_FRAC = 0.05  # max ramp = 5% of rated capacity per hour
S_MAX_DAYS = 5  # clinker storage horizon (days) — extended for flexibility
S_MAX_TONNES = RATED_CAPACITY_T_H * 24 * S_MAX_DAYS
MIN_LOAD_FRAC = 0.60  # minimum stable load fraction

# ─── GEOGRAPHIC CONSTANTS ─────────────────────────────────────────────────────
DE_BBOX = {"lat_min": 47, "lat_max": 55, "lon_min": 6, "lon_max": 15}
DE_BIDDING_ZONE = "10Y1001A1001A83F"  # ENTSO-E area code for DE-LU

# ─── TEMPORAL CONSTANTS ───────────────────────────────────────────────────────
YEAR_PROXY = 2023  # proxy data year for 2025 snapshot
OPSD_START_YEAR = 2018
OPSD_END_YEAR = 2023
DESTATIS_START_YEAR = 2010
DESTATIS_END_YEAR = 2024
DEFAULT_MODEL_YEAR = 2025

# Data provenance / fallback policy
# Keep these False for research runs so the pipeline never fabricates inputs.

# ─── PATHWAY-VARYING ELECTRICITY INTENSITY (kWh / tonne cement) ──────────────
# Source: VDZ 2023 (2025 base) + IEA/Conch 2035 kiln electrification roadmap
ALPHA_BY_YEAR = {
    2025: 109.0,  # current wet-grinding electricity only
    2035: 380.0,  # partial kiln electrification (Leilac pilot at scale)
    2045: 480.0,  # full pyro-processing + CCS compression electricity
}

# Stylised electricity split used in the clinker/grinding formulation.
# The sums equal ALPHA_BY_YEAR for each pathway year.
ALPHA_GRINDING_BY_YEAR = {
    2025: 109.0,
    2035: 140.0,
    2045: 160.0,
}
ALPHA_KILN_BY_YEAR = {
    2025: 0.0,
    2035: 240.0,
    2045: 320.0,
}

# Stylised ETS prices for scenario analysis (€ / tCO2).
ETS_PRICE_BY_YEAR = {
    2025: 85.0,
    2035: 130.0,
    2045: 180.0,
}

RES_MULTIPLIER_BY_YEAR = {
    2025: 1.0,
    2035: 2.5,
    2045: 4.0,
}

PHASE3_SCENARIO_YEARS = tuple(ALPHA_BY_YEAR.keys())

CLINKER_TO_CEMENT_RATIO = 0.75
STORAGE_COST_EUR_PER_TONNE_H = 0.02

# ─── BIG-M MINIMUM LOAD CONSTRAINTS ──────────────────────────────────────────

# ─── BIG-M MINIMUM LOAD CONSTRAINTS ──────────────────────────────────────────
# Cement kilns cannot run below 60% rated capacity (thermal inertia)
# Big-M value must be >= rated capacity to keep the constraint tight
MIN_LOAD_FRAC = 0.60  # 60% of rated capacity minimum
BIG_M = RATED_CAPACITY_T_H * 1.01  # slightly above max, keeps LP tight

# ─── REGIONAL PLANT DISAGGREGATION ───────────────────────────────────────────
# 8 major German cement plants mapped to approximate grid nodes.
# Capacity in t/h (VDZ 2023 public plant list, scaled to total 3200 t/h).
CEMENT_PLANTS = [
    {
        "name": "Heidelberg_Leimen",
        "bus": "DE122",  # Karlsruhe / Heidelberg area
        "capacity_t_h": 500,
        "alpha": 109.0,
    },
    {
        "name": "Dyckerhoff_Amoeneburg",
        "bus": "DE714",  # Wiesbaden area
        "capacity_t_h": 450,
        "alpha": 109.0,
    },
    {
        "name": "Holcim_Dotternhausen",
        "bus": "DE119",  # Tubingen / Dotternhausen area
        "capacity_t_h": 380,
        "alpha": 109.0,
    },
    {"name": "Cemex_Rudersdorf", "bus": "DE403", "capacity_t_h": 420, "alpha": 109.0}, # Oder-Spree
    {
        "name": "Schwenk_Karlstadt",
        "bus": "DE262",  # Wurzburg / Karlstadt area
        "capacity_t_h": 370,
        "alpha": 109.0,
    },
    {
        "name": "Lafarge_Wossingen",
        "bus": "DE12B",  # Karlsruhe / Wossingen area
        "capacity_t_h": 360,
        "alpha": 109.0,
    },
    {
        "name": "Rohrdorf_Rohrdorf",
        "bus": "DE212",  # Upper Bavaria / Rohrdorf
        "capacity_t_h": 330,
        "alpha": 109.0,
    },
    {"name": "Opterra_Karsdorf", "bus": "DEE02", "capacity_t_h": 390, "alpha": 109.0}, # Burgenlandkreis
]

# ─── MGA CONFIGURATION ──────────────────────────────────────────────────────────

# ─── TECHNO-ECONOMIC ASSUMPTIONS (CENTRALIZED) ────────────────────────────────
# These values parameterize the PyPSA framework directly without hardcoding loops
FALLBACK_SOLAR_CAP_MW = 90_000.0
FALLBACK_ONWIND_CAP_MW = 70_000.0
FALLBACK_OFFWIND_CAP_MW = 8_000.0
FALLBACK_SYS_LOAD_MW = 55_000.0

CC_SOLAR_EUR_MW = 50_000.0
CC_ONWIND_EUR_MW = 120_000.0
CC_OFFWIND_EUR_MW = 180_000.0
CC_OCGT_EUR_MW = 40_000.0
CC_LIGNITE_EUR_MW = 60_000.0

MC_OCGT_EUR_MWH = 60.0
MC_LIGNITE_EUR_MWH = 45.0
MC_NUCLEAR_EUR_MWH = 10.0

EFF_OCGT = 0.40
EFF_LIGNITE = 0.35
EFF_NUCLEAR = 0.33

PROCESS_CO2_KG_T_DEFAULT = 520.0
ENERGY_CO2_KG_T_DEFAULT = 160.0

ANALYSIS_CARRIER_MC = {
    "solar": 0.0,
    "onwind": 0.0,
    "offwind": 0.0,
    "OCGT": MC_OCGT_EUR_MWH,
    "gas": MC_OCGT_EUR_MWH,
    "lignite": MC_LIGNITE_EUR_MWH,
    "nuclear": MC_NUCLEAR_EUR_MWH,
    "load_shedding": 10000.0,
    "industrial_demand": 0.0,
}

# ─── MGA SETTINGS ─────────────────────────────────────────────────────────────
MGA_EPSILON_VALUES = [0.05, 0.10]  # epsilon sweep


MGA_N_ALTERNATIVES = (
    12  # alternatives per epsilon run (≥50 recommended: Berntsen & Trutnevyte 2017)
)
MGA_DEFAULT_EPSILON = 0.05  # default 5% cost relaxation
MGA_STORAGE_SENSITIVITY_EPSILON_VALUES = [0.05, 0.10, 0.20]
STORAGE_SENSITIVITY_SILO_DAYS = (5, 30)

# ─── WEATHER YEAR ENSEMBLE ────────────────────────────────────────────────────
WEATHER_ENSEMBLE_YEARS = list(
    range(2000, 2011)
)  # 11 years (2000-2010) for sensitivity matching historical data

# ─── EXTENDED MODEL FEATURES (Phases B/C/D) ──────────────────────────────────
KILN_STARTUP_COST_EUR = 5000.0  # Penalty per kiln start-up event
CCUS_CAPTURE_RATE = 0.90  # 90% CO2 capture fraction if active
CCUS_ENERGY_MWH_PER_TCO2 = 0.30  # 300 kWh/tCO2 for capture process (power demand)
CCUS_OPEX_EUR_PER_TCO2 = 15.0  # variable OPEX of amine capture system
ENABLE_ENDOGENOUS_INVESTMENT = False  # Let PyPSA optimize VRE and Battery capacity

# ─── FIGURE SETTINGS ──────────────────────────────────────────────────────────
FIGURE_DPI = 300
FIGURE_FORMAT = "png"

# ─── OUTPUT PATHS (resolved after DATA_DIR is available) ─────────────────────
