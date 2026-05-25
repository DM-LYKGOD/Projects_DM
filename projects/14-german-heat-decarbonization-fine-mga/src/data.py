"""
Data generation module synthesizing hourly German weather profiles,
temperature-dependent Heat Pump COPs, and hourly heat demand timeseries.

Supports two modes:
- Synthetic: national-average temperature profile (original)
- Empirical: per-archetype profiles calibrated from real Kreise climate data
"""

import numpy as np
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry
import demandlib.bdew as bdew
from src.config import TOTAL_GERMAN_HEAT_DEMAND_TWH

def fetch_historical_weather(snapshots, lat=50.11, lon=8.68):
    """
    Fetches historical ERA5 reanalysis temperature data from Open-Meteo for Germany.
    Default coordinates are roughly central Germany (Frankfurt am Main).
    """
    cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": snapshots[0].strftime("%Y-%m-%d"),
        "end_date": snapshots[-1].strftime("%Y-%m-%d"),
        "hourly": "temperature_2m"
    }
    
    print(f"[DATA] Fetching historical ERA5 weather for {params['start_date']} to {params['end_date']}...")
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    
    hourly = response.Hourly()
    temps = hourly.Variables(0).ValuesAsNumpy()
    
    # Open-Meteo might return data for the full final day, so we truncate to match snapshots exact length
    if len(temps) > len(snapshots):
        temps = temps[:len(snapshots)]
        
    return temps

def generate_hourly_heat_load(snapshots, temperatures):
    """
    Generates normalized hourly heat load profiles using the official BDEW 
    standard load profiles (SLP) for German households (EFH).
    """
    # demandlib requires temperature as a pandas Series
    temp_series = pd.Series(temperatures, index=snapshots)
    
    # Initialize the BDEW household heat building profile
    demand = bdew.HeatBuilding(
        snapshots, 
        temperature=temp_series,
        shclass=1, 
        wind_class=0, 
        building_class=1,
        shlp_type="EFH",
        annual_heat_demand=1.0, # Will return a normalized profile
        name='EFH'
    )
    
    # Retrieve the normalized BDEW load curve
    bdew_load = demand.get_bdew_profile().values
    
    # The get_bdew_profile() returns the profile scaled to `annual_heat_demand`.
    # To normalize it exactly like our old synthetic function (where the sum over
    # the entire year is 1.0, and a slice retains its correct fraction):
    if bdew_load.sum() > 0:
        bdew_load = bdew_load / bdew_load.sum()
        
    return bdew_load

def compute_cop(temperatures, sink_temp_c, is_district=False):
    """
    Computes Carnot-based coefficient of performance (COP) for heat pumps.
    Air-source temperature varies with weather; district uses a ground/waste heat source.
    """
    t_sink_k = sink_temp_c + 273.15
    eta = 0.48 if is_district else 0.44
    
    if is_district:
        t_source_k = 283.15  # 10 °C fixed temperature for deep geothermal / waste heat
        cop = eta * t_sink_k / (t_sink_k - t_source_k)
        return np.full(len(temperatures), cop)
    else:
        t_source_k = temperatures + 273.15
        temp_diff = np.maximum(5.0, t_sink_k - t_source_k)
        cop = eta * t_sink_k / temp_diff
        return np.clip(cop, 1.5, 5.5)

def generate_grid_carbon_intensity(snapshots, seed=42):
    """
    Models a 2045 German electricity grid carbon intensity (gCO2/kWh).
    Assumes ~80% renewables penetration with residual fossil backup.
    Low intensity during windy/sunny hours, higher during calm winter evenings.
    """
    np.random.seed(seed + 7)
    n_steps = len(snapshots)
    hours = np.arange(n_steps)
    
    # Base intensity ~60 gCO2/kWh for a mostly-decarbonized grid
    base = 60.0
    
    # Seasonal pattern: higher in winter (less solar, more gas backup)
    seasonal_amp = 40.0
    coldest_hour = 360
    seasonal = seasonal_amp * np.cos(2 * np.pi * (hours - coldest_hour) / 8760)
    
    # Diurnal pattern: lower during midday (solar peak), higher in evening
    hod = snapshots.hour.values
    diurnal_amp = 25.0
    diurnal = diurnal_amp * np.cos(2 * np.pi * (hod - 13) / 24)
    
    # Stochastic wind-driven variation
    noise = np.zeros(n_steps)
    phi = 0.92
    sigma = 12.0
    for i in range(1, n_steps):
        noise[i] = phi * noise[i - 1] + np.random.normal(0, sigma)
    
    intensity = base + seasonal + diurnal + noise
    return np.clip(intensity, 15.0, 200.0)


def generate_representative_weeks():
    """
    Creates 3 representative weeks (504 hourly snapshots) with seasonal weighting:
    - Winter week (hours 0-167): weight 0.45 — coldest period, high demand, low COP
    - Shoulder week (hours 2160-2327): weight 0.35 — mild temperatures
    - Summer week (hours 4320-4487): weight 0.20 — warm, low demand (DHW only)
    
    Returns (snapshots, weights_series) where weights scale each hour to represent
    its annual share (weights sum to 8760).
    """
    winter_start = pd.Timestamp("2045-01-01")
    shoulder_start = pd.Timestamp("2045-04-01")
    summer_start = pd.Timestamp("2045-07-01")
    
    winter_snaps = pd.date_range(winter_start, periods=168, freq="h")
    shoulder_snaps = pd.date_range(shoulder_start, periods=168, freq="h")
    summer_snaps = pd.date_range(summer_start, periods=168, freq="h")
    
    snapshots = winter_snaps.append(shoulder_snaps).append(summer_snaps)
    
    # Weights: each representative hour stands for how many real hours it represents
    # Total annual hours = 8760, split by seasonal weighting
    winter_weight = 0.45 * 8760 / 168   # ~23.5 real hours per snapshot
    shoulder_weight = 0.35 * 8760 / 168  # ~18.25 real hours per snapshot
    summer_weight = 0.20 * 8760 / 168    # ~10.4 real hours per snapshot
    
    weights = np.concatenate([
        np.full(168, winter_weight),
        np.full(168, shoulder_weight),
        np.full(168, summer_weight),
    ])
    
    weights_series = pd.Series(weights, index=snapshots)
    return snapshots, weights_series


def get_heat_dataset(snapshots, mean_temp=None):
    """
    Generates and bundles all synthetic weather and techno-economic input variables.
    Now includes hourly grid carbon intensity for indirect emissions accounting.

    Parameters
    ----------
    snapshots : pd.DatetimeIndex
    mean_temp : float, optional
        If provided, calibrates the temperature profile to an archetype-specific
        mean derived from real Kreise climate data.
    """
    temps = fetch_historical_weather(snapshots)
    if mean_temp is not None:
        # Shift the real weather profile to match the empirical archetype mean
        temps = temps + (mean_temp - np.mean(temps))
    
    norm_load = generate_hourly_heat_load(snapshots, temps)
    cop_air = compute_cop(temps, 45.0, is_district=False)
    cop_dh = compute_cop(temps, 65.0, is_district=True)
    grid_co2 = generate_grid_carbon_intensity(snapshots)
    
    df = pd.DataFrame(
        {
            "temp": temps,
            "norm_load": norm_load,
            "cop_air_hp": cop_air,
            "cop_dh_hp": cop_dh,
            "grid_co2_grams_per_kwh": grid_co2,
        },
        index=snapshots
    )
    return df


def get_heat_dataset_empirical(snapshots, archetype_climate):
    """
    Generates per-archetype climate datasets using real mean temperatures
    from the Kreise dataset. Returns a dict of DataFrames keyed by archetype.

    Parameters
    ----------
    snapshots : pd.DatetimeIndex
    archetype_climate : dict
        {archetype: {'temperature': float, ...}} from get_archetype_climate_profiles()

    Returns
    -------
    dict
        {archetype_name: pd.DataFrame with same columns as get_heat_dataset()}
    """
    datasets = {}
    for archetype, climate in archetype_climate.items():
        mean_temp = climate.get("temperature", 9.5)
        datasets[archetype] = get_heat_dataset(snapshots, mean_temp=mean_temp)
    return datasets