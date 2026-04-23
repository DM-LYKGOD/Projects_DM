"""
Phase 2: Endogenous industrial cement module with regional plants,
clinker storage, grinding demand, and ETS coupling.
"""

import json
import sys
from functools import lru_cache
from pathlib import Path
import matplotlib

# matplotlib.use("Agg")  # Commented to allow inline display in notebook
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pypsa
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    ALPHA_BY_YEAR,
    ALPHA_GRINDING_BY_YEAR,
    ALPHA_KILN_BY_YEAR,
    CCUS_CAPTURE_RATE,
    CCUS_ENERGY_MWH_PER_TCO2,
    CCUS_OPEX_EUR_PER_TCO2,
    CEMENT_PARAMS_JSON,
    CEMENT_PLANTS,
    CEMENT_SEASONALITY_CSV,
    CLINKER_TO_CEMENT_RATIO,
    ETS_PRICE_BY_YEAR,
    FIGURES_DIR,
    KILN_STARTUP_COST_EUR,
    MIN_LOAD_FRAC,
    NUTS3_CEMENT_WEIGHTS_CSV,
    STORAGE_COST_EUR_PER_TONNE_H,
    TOTAL_DEMAND_TONNES,
    INDUSTRIAL_DIR,
    INDUSTRIAL_SOLVED_NC,
    PROCESS_CO2_KG_T_DEFAULT,
    ENERGY_CO2_KG_T_DEFAULT,
)

INDUSTRIAL_NC = INDUSTRIAL_SOLVED_NC
DISPATCH_PLOT_PNG = FIGURES_DIR / "industrial_dispatch.png"


@lru_cache(maxsize=1)
def _load_nuts3_centroids() -> gpd.GeoDataFrame:
    geo_url = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_10M_2021_4326_LEVL_3.geojson"
    gdf = gpd.read_file(geo_url)
    centroids = gdf.to_crs(3035).geometry.centroid.to_crs(4326)
    return gpd.GeoDataFrame(
        {"NUTS_ID": gdf["NUTS_ID"], "centroid": centroids},
        geometry="centroid",
        crs=4326,
    )


def load_cement_parameters() -> dict:
    with open(CEMENT_PARAMS_JSON) as fh:
        return json.load(fh)


def _pick_bus(n: pypsa.Network, suggested: str | None = None) -> str:
    if suggested and suggested in n.buses.index:
        return suggested
    if len(n.buses.index) == 1:
        return n.buses.index[0]
    candidates = [
        b for b in n.buses.index if suggested and suggested.lower() in b.lower()
    ]
    return candidates[0] if candidates else n.buses.index[0]


def load_regional_plants(
    n: pypsa.Network, top_n: int = 8, s_max_days_override: float = None
) -> pd.DataFrame:
    params = load_cement_parameters()
    rated_capacity = float(params["rated_capacity_t_h"])
    storage_days = (
        s_max_days_override
        if s_max_days_override is not None
        else float(params["s_max_days"])
    )

    # Robust Spatial Routing for NUTS-2/3 or Standalone
    if NUTS3_CEMENT_WEIGHTS_CSV.exists():
        print(
            f"[Phase 2] Routing Industrial Loads to {len(n.buses)} buses based on NUTS-3 weights..."
        )
        weights = pd.read_csv(NUTS3_CEMENT_WEIGHTS_CSV)

        if {"x", "y"}.issubset(n.buses.columns) and len(n.buses) > 1:
            try:
                gdf = _load_nuts3_centroids()
                weights = weights.merge(
                    gdf[["NUTS_ID", "centroid"]],
                    left_on="Code",
                    right_on="NUTS_ID",
                    how="left",
                )
                weights = weights.dropna(subset=["centroid"])

                buses = n.buses[["x", "y"]].copy()
                assigned_buses = []
                for idx, row in weights.iterrows():
                    cx, cy = row["centroid"].x, row["centroid"].y
                    distances = (buses["x"] - cx) ** 2 + (buses["y"] - cy) ** 2
                    assigned_buses.append(distances.idxmin())
                weights["bus"] = assigned_buses
            except Exception as e:
                print(
                    f"[Phase 2] GIS Router failed ({e}). Falling back to simple mapping."
                )
                weights["bus"] = weights["Code"].map(lambda c: _pick_bus(n, str(c)))
        else:
            weights["bus"] = weights["Code"].map(lambda c: _pick_bus(n, str(c)))

        # Aggregate weights by bus to avoid hundreds of tiny variables
        bus_weights = weights.groupby("bus")["weight"].sum().reset_index()
        bus_weights["weight"] = bus_weights["weight"] / bus_weights["weight"].sum()

        # IMPORTANT: Deterministic naming to avoid KeyErrors
        plants = pd.DataFrame(
            {
                "plant": [f"Industrial_Bus_{b}" for b in bus_weights["bus"]],
                "label": [f"Industry at {b}" for b in bus_weights["bus"]],
                "bus": bus_weights["bus"],
                "share": bus_weights["weight"],
            }
        )
    else:
        # Heritage 4-node hardcoded plants
        plants = pd.DataFrame(CEMENT_PLANTS).copy()
        plants["plant"] = plants["name"]
        plants["label"] = plants["name"]
        plants["bus"] = plants["bus"].map(lambda b: _pick_bus(n, b))
        plants["share"] = plants["capacity_t_h"] / plants["capacity_t_h"].sum()

    plants["capacity_t_h"] = rated_capacity * plants["share"]
    plants["annual_cement_t"] = TOTAL_DEMAND_TONNES * plants["share"]
    plants["storage_max_t"] = plants["capacity_t_h"] * 24.0 * storage_days
    plants["min_load_t_h"] = MIN_LOAD_FRAC * plants["capacity_t_h"]
    plants["ramp_limit_t_h"] = plants["capacity_t_h"] * float(params["ramp_limit_frac"])
    # Validation for Fix 8
    unmatched = [
        (orig, mapped) for orig, mapped in
        zip(plants['bus_original'] if 'bus_original' in plants.columns else plants['bus'],
            plants['bus'])
        if mapped == n.buses.index[0] and len(n.buses) > 1
    ]
    if unmatched and len(n.buses) > 1:
        import warnings
        warnings.warn(
            f"Phase 2: {len(unmatched)} cement plants mapped to fallback bus "
            f"'{n.buses.index[0]}' because their names did not match any NUTS-2 bus. "
            f"Update CEMENT_PLANTS in config to use real NUTS-2 IDs such as: "
            f"{list(n.buses.index[:5])}",
            UserWarning, stacklevel=2
        )
    return plants.reset_index(drop=True)


def load_hourly_cement_demand(snapshots, total_demand: float) -> pd.Series:
    if CEMENT_SEASONALITY_CSV.exists():
        seasonality = pd.read_csv(CEMENT_SEASONALITY_CSV)
        month_col = (
            "month" if "month" in seasonality.columns else seasonality.columns[0]
        )
        weight_col = (
            "seasonality_weight"
            if "seasonality_weight" in seasonality.columns
            else seasonality.columns[-1]
        )
        month_weights = seasonality.set_index(month_col)[weight_col].to_dict()
        raw = pd.Series(
            [month_weights.get(m, 1.0) for m in snapshots.month], index=snapshots
        )
        profile = raw * total_demand / raw.sum()
    else:
        profile = pd.Series(total_demand / len(snapshots), index=snapshots)
    return profile.astype(float)


def get_alpha_components(year: int) -> tuple:
    total = ALPHA_BY_YEAR.get(year, ALPHA_BY_YEAR[2025]) / 1000.0
    grinding = ALPHA_GRINDING_BY_YEAR.get(year, ALPHA_GRINDING_BY_YEAR[2025]) / 1000.0
    kiln = ALPHA_KILN_BY_YEAR.get(year, ALPHA_KILN_BY_YEAR[2025]) / 1000.0
    return total, grinding, kiln


def remove_exogenous_cement_load(n: pypsa.Network, year: int = 2025) -> None:
    baseline_alpha = ALPHA_BY_YEAR.get(year, ALPHA_BY_YEAR[2025])
    idx_snaps = pd.Index(n.snapshots, name="snapshot")
    hourly_t_h = load_hourly_cement_demand(idx_snaps, TOTAL_DEMAND_TONNES)
    hourly_mw = (hourly_t_h.values * baseline_alpha) / 1000.0

    total_load = np.zeros_like(hourly_mw)
    for load in n.loads.index:
        total_load += n.loads_t.p_set[load].values
    total_load = np.where(total_load > 0, total_load, 1.0)

    for load in n.loads.index:
        current = n.loads_t.p_set[load].values
        weight = current / total_load
        n.loads_t.p_set[load] = np.maximum(current - hourly_mw * weight, 0.0)
    print(
        f"[Phase 2] Removed {year} dynamic exogenous cement load from {len(n.loads)} nodes."
    )


def add_cement_dummy_generators(n: pypsa.Network, plants: pd.DataFrame) -> None:
    if "industrial_demand" not in n.carriers.index:
        n.add("Carrier", "industrial_demand")
    for _, row in plants.iterrows():
        name = f"Cement_Elec_Demand::{row['plant']}"
        if name in n.generators.index:
            continue
        n.add(
            "Generator",
            name,
            bus=row["bus"],
            carrier="industrial_demand",
            p_nom=row["capacity_t_h"],
            p_min_pu=-1.0,
            p_max_pu=0.0,
            marginal_cost=0.0,
        )


def add_endogenous_industry(
    n: pypsa.Network, snapshots, year: int = 2025, s_max_days_override=None
) -> None:
    m = n.model
    params = load_cement_parameters()

    plants = load_regional_plants(n, s_max_days_override=s_max_days_override)
    idx_s = pd.Index(snapshots, name="snapshot")
    idx_p = pd.Index(plants["plant"], name="plant")
    print(f"\n[DEBUG] Industrial Model snapshot count: {len(idx_s)}")
    print(f"[DEBUG] Industrial Model plant count: {len(idx_p)}")
    print(f"[DEBUG] Industrial Model plants: {idx_p.tolist()}")
    print(f"[DEBUG] Plants summary:\n{plants[['plant', 'bus', 'capacity_t_h']].head()}")

    _, alpha_gr, alpha_kl = get_alpha_components(year)
    ets = ETS_PRICE_BY_YEAR.get(year, ETS_PRICE_BY_YEAR[2025])
    cr = CLINKER_TO_CEMENT_RATIO
    direct_co2 = (
        float(params.get("process_co2_kg_t", 520.0))
        + float(params.get("energy_co2_kg_t", 160.0))
    ) / 1000.0

    hourly_demand = load_hourly_cement_demand(idx_s, TOTAL_DEMAND_TONNES)
    ann_tgt = plants.set_index("plant")["annual_cement_t"].reindex(idx_p)
    capacity = plants.set_index("plant")["capacity_t_h"].reindex(idx_p)
    min_load = plants.set_index("plant")["min_load_t_h"].reindex(idx_p)
    ramp_lim = plants.set_index("plant")["ramp_limit_t_h"].reindex(idx_p)
    s_cap = plants.set_index("plant")["storage_max_t"].reindex(idx_p)
    initial_s = 0.5 * s_cap

    clk = m.add_variables(coords=[idx_s, idx_p], lower=0, name="ClinkerProduction")
    grd = m.add_variables(coords=[idx_s, idx_p], lower=0, name="CementGrinding")
    sto = m.add_variables(coords=[idx_s, idx_p], lower=0, name="ClinkerStorage")
    yon = m.add_variables(coords=[idx_s, idx_p], lower=0, upper=1, name="KilnOn")
    yst = m.add_variables(coords=[idx_s, idx_p], lower=0, upper=1, name="KilnStart")

    m.add_constraints(
        grd.sum("plant") == hourly_demand.values, name="cement_hourly_balance"
    )
    m.add_constraints(grd.sum("snapshot") == ann_tgt, name="cement_regional_target")
    m.add_constraints(sto <= s_cap, name="storage_capacity")
    m.add_constraints(clk <= capacity * yon, name="kiln_max_load")

    active = idx_s[1:]
    shifted = clk.roll(snapshot=1)
    yon_shifted = yon.roll(snapshot=1)
    # Scale ramping by time-step (e.g. 5% per hour * 3 hours = 15% between snapshots)
    time_step = (
        float((snapshots[1] - snapshots[0]).total_seconds() / 3600.0)
        if len(snapshots) > 1
        else 1.0
    )
    ramp_lim_scaled = ramp_lim * time_step

    import logging as _logging
    _log = _logging.getLogger(__name__)
    _log.debug("Industrial Model: %d snapshots, %d plants: %s",
               len(idx_s), len(idx_p), idx_p.tolist())
    _log.debug("Plants summary:\n%s",
               plants[['plant', 'bus', 'capacity_t_h']].head().to_string())

    m.add_constraints(
        yst.loc[active] >= yon.loc[active] - yon_shifted.loc[active],
        name="kiln_startup_events",
    )
    m.add_constraints(
        clk.loc[active] - shifted.loc[active] <= ramp_lim_scaled, name="ramp_up"
    )
    m.add_constraints(
        shifted.loc[active] - clk.loc[active] <= ramp_lim_scaled, name="ramp_down"
    )

    first, last = idx_s[0], idx_s[-1]
    m.add_constraints(
        sto.loc[first] == initial_s + clk.loc[first] - cr * grd.loc[first],
        name="storage_init",
    )
    m.add_constraints(
        sto.loc[active]
        - sto.roll(snapshot=1).loc[active]
        - clk.loc[active]
        + cr * grd.loc[active]
        == 0,
        name="storage_balance",
    )
    m.add_constraints(sto.loc[last] >= initial_s, name="storage_cyclic")

    p_gen = m.variables["Generator-p"]
    for p in idx_p:
        name = f"Cement_Elec_Demand::{p}"
        m.add_constraints(
            p_gen.loc[:, name]
            == -(alpha_gr * grd.loc[:, p] + alpha_kl * clk.loc[:, p]) / time_step,
            name=f"cement_load_link_{p}",
        )

    cost = (
        STORAGE_COST_EUR_PER_TONNE_H * sto.sum()
        + KILN_STARTUP_COST_EUR * yst.sum()
        + ets * direct_co2 * clk.sum()
    )
    m.objective += cost


def _extract_solution(n):
    clk = n.model.variables["ClinkerProduction"].solution.to_pandas()
    grd = n.model.variables["CementGrinding"].solution.to_pandas()
    sto = n.model.variables["ClinkerStorage"].solution.to_pandas()
    clk.index = pd.to_datetime(clk.index)
    grd.index = pd.to_datetime(grd.index)
    sto.index = pd.to_datetime(sto.index)
    return clk, grd, sto


def run_phase_2(year: int = 2025) -> None:
    from src.model_phases.task_A_phase1_baseline import (
        load_network,
        inject_actual_load,
        inject_capacity_factors,
    )

    n = load_network()
    inject_actual_load(n)
    inject_capacity_factors(n)
    remove_exogenous_cement_load(n, year=year)
    plants = load_regional_plants(n)
    add_cement_dummy_generators(n, plants)
    n.sanitize()
    n.optimize(
        solver_name="highs",
        solver_options={
            "solver": "ipm",
            "run_crossover": "on",
            "threads": 8,
            "user_bound_scale": -12,
        },
        extra_functionality=lambda n_i, s: add_endogenous_industry(n_i, s, year=year),
    )
    n.export_to_netcdf(str(INDUSTRIAL_NC))


if __name__ == "__main__":
    run_phase_2()
