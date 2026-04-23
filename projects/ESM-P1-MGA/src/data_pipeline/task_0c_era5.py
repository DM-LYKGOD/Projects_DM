"""
task_0c_era5.py — Task 0C: ERA5 Reanalysis via Copernicus CDS
==============================================================
Downloads ERA5 single-level variables for Germany (2023),
converts to PV and wind capacity-factor time series.

If CDS is unavailable or the API key is missing, a deterministic
synthetic fallback is used so the pipeline can proceed.

Outputs:
  data/climate/era5_pv_cf_DE_2023.csv
  data/climate/era5_wind_cf_DE_2023.csv
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    CDS_API_KEY, CDS_API_URL, DE_BBOX,
    ERA5_PV_CF_CSV, ERA5_WIND_CF_CSV,
    CLIMATE_DIR,
)

ERA5_NC_PV   = CLIMATE_DIR / "era5_ssrd_DE_2023.nc"
ERA5_NC_WIND = CLIMATE_DIR / "era5_wind_DE_2023.nc"

# ── IEC Class II power curve parameters ──────────────────────────────────────
CUT_IN_MS  =  3.0   # m/s
RATED_MS   = 13.0   # m/s
CUT_OUT_MS = 25.0   # m/s

# ── PV conversion parameters ──────────────────────────────────────────────────
PEAK_IRRADIANCE_WM2 = 1000.0
PV_PR               =  0.80

# Max CDS API retries — default was 500 (= 16 h of waiting at 120 s each)
# Capped here to 5 so a bad API session fails fast.
CDS_MAX_RETRIES = 5


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _check_api_key() -> bool:
    """Return True if a real CDS API key has been configured."""
    if not CDS_API_KEY or CDS_API_KEY == "YOUR_CDS_API_KEY":
        print(
            "[0C] WARNING: CDS_API_KEY is not set.\n"
            "[0C]   Register free at https://cds.climate.copernicus.eu\n"
            "[0C]   Set CDS_API_KEY in your .env file, then re-run the task.\n"
            "[0C]   Synthetic fallback will be used this run."
        )
        return False
    return True


def _build_synthetic_cf(year: int = 2023) -> tuple:
    """
    Build deterministic synthetic PV and wind CF series for Germany.
    Shape / dtype are identical to the real ERA5 output.
    Only used when CDS is unavailable.
    """
    print(f"[0C] *** Synthetic ERA5 CF fallback activated for {year}. ***")
    print("[0C] *** Replace era5_*_cf_DE_2023.csv with real data for research. ***")

    idx  = pd.date_range(f"{year}-01-01", periods=8760, freq="h", tz="UTC")
    t    = np.arange(8760)
    hour = (t % 24).astype(float)
    day  = t / 24.0

    # Solar
    daytime  = np.clip((hour - 6) / 6, 0, 1) * np.clip((20 - hour) / 6, 0, 1)
    seasonal = 0.5 + 0.5 * np.cos(2 * np.pi * (day - 172) / 365)
    pv_cf    = np.clip(daytime * seasonal * 0.85 * PV_PR, 0.0, 1.0)

    # Wind
    rng       = np.random.default_rng(42)
    wind_base = 0.35 + 0.15 * np.cos(2 * np.pi * (day - 30) / 365)
    wind_cf   = np.clip(wind_base + rng.normal(0, 0.10, 8760), 0.02, 1.0)

    pv   = pd.Series(pv_cf,   index=idx, name="pv_cf")
    wind = pd.Series(wind_cf, index=idx, name="wind_cf")
    pv.index.name   = "utc_timestamp"
    wind.index.name = "utc_timestamp"
    return pv, wind


def _make_cds_client():
    """Build a cdsapi Client with retry count capped at CDS_MAX_RETRIES."""
    import cdsapi
    return cdsapi.Client(
        url=CDS_API_URL,
        key=CDS_API_KEY,
        retry_max=CDS_MAX_RETRIES,
        sleep_max=120,
        quiet=False,
    )


def iec_power_curve(wind_speed: np.ndarray) -> np.ndarray:
    ws = np.asarray(wind_speed, dtype=float)
    cf = np.zeros_like(ws)
    mask_ramp  = (ws >= CUT_IN_MS) & (ws < RATED_MS)
    mask_rated = (ws >= RATED_MS)  & (ws < CUT_OUT_MS)
    cf[mask_ramp]  = (ws[mask_ramp]**3 - CUT_IN_MS**3) / (RATED_MS**3 - CUT_IN_MS**3)
    cf[mask_rated] = 1.0
    return np.clip(cf, 0.0, 1.0)


def ssrd_to_pv_cf(ssrd_j_m2: np.ndarray) -> np.ndarray:
    return np.clip(ssrd_j_m2 / 3600.0 / PEAK_IRRADIANCE_WM2 * PV_PR, 0.0, 1.0)


def area_weighted_mean(da):
    weights = np.cos(np.deg2rad(da.latitude))
    return da.weighted(weights).mean(dim=["latitude", "longitude"])


def _get_time_coord(da):
    for name in ("time", "valid_time", "forecast_reference_time"):
        if name in da.coords:
            return da.coords[name]
    for name, coord in da.coords.items():
        if np.issubdtype(coord.dtype, np.datetime64):
            return coord
    raise AttributeError(f"[0C] No time coord found. Available: {list(da.coords)}")


# ─────────────────────────────────────────────────────────────────────────────
# Download functions
# ─────────────────────────────────────────────────────────────────────────────

def download_era5_solar(year: int = 2023) -> Path:
    """Download ERA5 SSRD for Germany bounding box (all months)."""
    if ERA5_NC_PV.exists():
        print(f"[0C] ERA5 solar file already exists: {ERA5_NC_PV}. Skipping.")
        return ERA5_NC_PV

    c = _make_cds_client()
    months = [f"{m:02d}" for m in range(1, 13)]
    days   = [f"{d:02d}" for d in range(1, 32)]
    times  = [f"{h:02d}:00" for h in range(24)]

    print(f"[0C] Requesting ERA5 SSRD for Germany {year} (max {CDS_MAX_RETRIES} retries) ...")
    c.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": "reanalysis",
            "variable":     ["surface_solar_radiation_downwards"],
            "year":         str(year),
            "month":        months,
            "day":          days,
            "time":         times,
            "area":         [DE_BBOX["lat_max"], DE_BBOX["lon_min"],
                             DE_BBOX["lat_min"], DE_BBOX["lon_max"]],
            "format":       "netcdf",
        },
        str(ERA5_NC_PV),
    )
    print(f"[0C] Solar data saved -> {ERA5_NC_PV}")
    return ERA5_NC_PV


def download_era5_wind(year: int = 2023) -> Path:
    """Download ERA5 100 m u/v wind for Germany bounding box (all months)."""
    if ERA5_NC_WIND.exists():
        print(f"[0C] ERA5 wind file already exists: {ERA5_NC_WIND}. Skipping.")
        return ERA5_NC_WIND

    c = _make_cds_client()
    months = [f"{m:02d}" for m in range(1, 13)]
    days   = [f"{d:02d}" for d in range(1, 32)]
    times  = [f"{h:02d}:00" for h in range(24)]

    print(f"[0C] Requesting ERA5 100m wind for Germany {year} (max {CDS_MAX_RETRIES} retries) ...")
    c.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": "reanalysis",
            "variable":     ["100m_u_component_of_wind", "100m_v_component_of_wind"],
            "year":         str(year),
            "month":        months,
            "day":          days,
            "time":         times,
            "area":         [DE_BBOX["lat_max"], DE_BBOX["lon_min"],
                             DE_BBOX["lat_min"], DE_BBOX["lon_max"]],
            "format":       "netcdf",
        },
        str(ERA5_NC_WIND),
    )
    print(f"[0C] Wind data saved -> {ERA5_NC_WIND}")
    return ERA5_NC_WIND


def process_solar(nc_path: Path) -> pd.Series:
    import xarray as xr
    print("[0C] Processing ERA5 solar data ...")
    ds       = xr.open_dataset(nc_path)
    var_name = "ssrd" if "ssrd" in ds else list(ds.data_vars)[0]
    ssrd_de  = area_weighted_mean(ds[var_name])
    pv_cf    = ssrd_to_pv_cf(ssrd_de.values)
    times    = pd.to_datetime(_get_time_coord(ssrd_de).values)
    series   = pd.Series(pv_cf, index=times, name="pv_cf")
    series.index.name = "utc_timestamp"
    print(f"[0C] PV CF: mean={series.mean():.3f}, max={series.max():.3f}")
    return series.resample("h").mean()


def process_wind(nc_path: Path) -> pd.Series:
    import xarray as xr
    print("[0C] Processing ERA5 wind data ...")
    ds     = xr.open_dataset(nc_path)
    u_name = 'u100' if 'u100' in ds.data_vars else next(
        (v for v in ds.data_vars if v.startswith('u')), None
    )
    v_name = 'v100' if 'v100' in ds.data_vars else next(
        (v for v in ds.data_vars if v.startswith('v')), None
    )
    if u_name is None or v_name is None:
        raise KeyError(
            f"0C: Could not identify u/v wind components. Available: {list(ds.data_vars)}"
        )
    ws_de  = area_weighted_mean(np.sqrt(ds[u_name]**2 + ds[v_name]**2))
    wind_cf = iec_power_curve(ws_de.values)
    times   = pd.to_datetime(_get_time_coord(ws_de).values)
    series  = pd.Series(wind_cf, index=times, name="wind_cf")
    series.index.name = "utc_timestamp"
    print(f"[0C] Wind CF: mean={series.mean():.3f}, max={series.max():.3f}")
    return series.resample("h").mean()


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_task_0c() -> None:
    """Main entry point for Task 0C."""
    print("\n" + "=" * 60)
    print("  TASK 0C — ERA5 Reanalysis via Copernicus CDS")
    print("=" * 60)

    CLIMATE_DIR.mkdir(parents=True, exist_ok=True)

    # Skip if both outputs already exist
    if ERA5_PV_CF_CSV.exists() and ERA5_WIND_CF_CSV.exists():
        print("[0C] Both CF output files already exist — skipping.")
        print(f"[0C] PV   : {ERA5_PV_CF_CSV}")
        print(f"[0C] Wind : {ERA5_WIND_CF_CSV}")
        print("\n[0C] ── TASK 0C COMPLETE (cached) ──────────────────────────\n")
        return

    # Try real CDS; fall back to synthetic on any failure
    api_ok     = _check_api_key()
    pv_series  = None
    wind_series = None

    if api_ok:
        try:
            solar_nc    = download_era5_solar(year=2023)
            wind_nc     = download_era5_wind(year=2023)
            pv_series   = process_solar(solar_nc)
            wind_series = process_wind(wind_nc)
        except Exception as exc:
            print(f"[0C] CDS pipeline failed: {exc}")
            print("[0C] Activating synthetic CF fallback.")

    if pv_series is None or wind_series is None:
        pv_series, wind_series = _build_synthetic_cf(year=2023)

    pv_series.to_frame().to_csv(ERA5_PV_CF_CSV)
    wind_series.to_frame().to_csv(ERA5_WIND_CF_CSV)

    print(f"[0C] PV CF saved   -> {ERA5_PV_CF_CSV}")
    print(f"[0C] Wind CF saved -> {ERA5_WIND_CF_CSV}")
    print("\n[0C] ── TASK 0C COMPLETE ──────────────────────────────────\n")


if __name__ == "__main__":
    run_task_0c()
