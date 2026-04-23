"""
task_A_phase1_baseline.py — Phase 1: PyPSA-DE Setup & Baseline Validation
========================================================================
Loads the PyPSA-DE 2025 network (or the fallback stub), injects the actual
ENTSO-E hourly load and ERA5-derived capacity factors, and runs a baseline
optimisation for a fixed exogenous industrial demand (the standard approach).

Outputs:
  data/figures/baseline_dispatch.png
  Prints: Total system cost, curtailment %, load shed.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pypsa
import matplotlib

# matplotlib.use("Agg")  # Commented to allow inline display in notebook
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    PYPSA_DE_NC_2025,
    ENTSOE_LOAD_CSV,
    ERA5_PV_CF_CSV,
    ERA5_WIND_CF_CSV,
    ERA5_CF_HIST_CSV,
    FIGURES_DIR,
    ALPHA_KWH_PER_TONNE,
    TOTAL_DEMAND_TONNES,
    ENABLE_ENDOGENOUS_INVESTMENT,
    BASELINE_SOLVED_NC,
)

BASELINE_NC = BASELINE_SOLVED_NC
DISPATCH_PLOT_PNG = FIGURES_DIR / "baseline_dispatch.png"


def load_network(network_path=None, weather_year_override=None) -> pypsa.Network:
    """Load the base 2025 PyPSA-DE NetCDF file.

    Parameters
    ----------
    network_path : str, optional
        Path to a network NetCDF file. Defaults to PYPSA_DE_NC_2025.
    weather_year_override : int, optional
        Override year for weather data proxy selection. Stored as
        n.meta["weather_year"] for downstream use in inject_capacity_factors().
    """
    if not PYPSA_DE_NC_2025.exists():
        raise FileNotFoundError(
            f"[Phase 1] Base network not found: {PYPSA_DE_NC_2025}\n"
            "Run 'python task_0a_pypsa_de.py' first."
        )
    path = network_path or str(PYPSA_DE_NC_2025)
    print(f"[Phase 1] Loading base network from {path} ...")
    n = pypsa.Network(path)
    from src.config import PREFERRED_PYPSA_DE_BUS_COUNT

    if len(n.buses) != PREFERRED_PYPSA_DE_BUS_COUNT:
        raise RuntimeError(
            f"Network has {len(n.buses)} buses but expected {PREFERRED_PYPSA_DE_BUS_COUNT}. "
            f"Loaded file: {PYPSA_DE_NC_2025}. "
            "Verify the network file is the correct multi-node file and set "
            "ALLOW_DATA_FALLBACKS=False to prevent silent fallback to single-bus network."
        )
    if weather_year_override is not None:
        n.meta["weather_year"] = weather_year_override
        print(f"[load_network] Weather year override: {weather_year_override}")
    n.sanitize()
    return n


def _group_columns_by_carrier(frame: pd.DataFrame, carriers: pd.Series) -> pd.DataFrame:
    """Group a snapshot-by-component frame into carrier totals."""
    if frame.empty:
        return pd.DataFrame(index=frame.index)

    labels = carriers.reindex(frame.columns).fillna("unknown")
    return frame.T.groupby(labels).sum().T


def inject_actual_load(n: pypsa.Network) -> None:
    """
    Replace placeholder load with actual ENTSO-E hourly load (2025).
    Includes fixed, exogenous cement demand (standard baseline representation).
    """
    if not ENTSOE_LOAD_CSV.exists():
        print("[Phase 1] WARNING: ENTSO-E load not found. Using network defaults.")
        return

    print("[Phase 1] Injecting ENTSO-E actual hourly load ...")
    load_df = pd.read_csv(ENTSOE_LOAD_CSV, index_col=0, parse_dates=True)
    load_series = load_df["load_MW"].copy()
    if getattr(load_series.index, "tz", None) is not None:
        load_series.index = load_series.index.tz_convert(None)
    load_series = load_series.sort_index().astype(float)
    load_series = load_series.interpolate().ffill().bfill()

    # Align with network snapshots
    # If the years don't match exactly (e.g. proxy year), shift the index to network year
    n_year = n.snapshots[0].year
    data_year = load_series.index[0].year

    if n_year != data_year:
        print(f"[Phase 1] Shifting load from {data_year} to {n_year} ...")
        # Shift robustly ignoring leap year misalignment issues by using hour-of-year mapped to snapshots
        snaps = n.snapshots
        length = min(len(load_series), len(snaps))
        matched = load_series.iloc[:length].values
        if length < len(snaps):
            matched = np.pad(matched, (0, len(snaps) - length), mode="edge")
    else:
        # Standard reindex
        matched = load_series.reindex(n.snapshots).ffill().bfill().astype(float).values

    total_baseline_p_set = n.loads.p_set.sum()
    for load in n.loads.index:
        weight = n.loads.at[load, "p_set"] / total_baseline_p_set
        n.loads_t.p_set[load] = matched * weight

    # Calculate baseline (fixed) cement load
    avg_cement_mw = (ALPHA_KWH_PER_TONNE * TOTAL_DEMAND_TONNES) / (8760 * 1000)
    print(f"[Phase 1] Fixed exogenous cement load portion: ~{avg_cement_mw:.0f} MW")

    total_load_twh = float(np.nansum(matched) / 1e6)
    print(
        f"[Phase 1] Total annual system load (including industry): {total_load_twh:.1f} TWh"
    )


def inject_capacity_factors(n: pypsa.Network) -> None:
    """
    Replace default renewables CF with ERA5-derived profiles.
    Falls back to Reading historical if real 2023/2025 ERA5 is missing.
    """
    print("[Phase 1] Injecting ERA5 renewable capacity factors ...")

    # Locate solar generator
    solar_gens = [g for g in n.generators.index if "solar" in g.lower()]
    wind_on = [
        g for g in n.generators.index if "onwind" in g.lower() or "onshore" in g.lower()
    ]

    # Pick source data
    pv_cf, wind_cf = None, None
    if ERA5_PV_CF_CSV.exists() and ERA5_WIND_CF_CSV.exists():
        print("[Phase 1]   Using proper ERA5 hourly derivatives (Task 0C)")
        pv_df = pd.read_csv(ERA5_PV_CF_CSV, index_col=0, parse_dates=True)
        wind_df = pd.read_csv(ERA5_WIND_CF_CSV, index_col=0, parse_dates=True)
        # Shift index if needed
        n_year = n.snapshots[0].year
        # Fix 13: Robust Proxy Year Weather Data Selection
        if pv_df.index[0].year != n_year:
            # Check for weather_year override stored by load_network()
            proxy_year = n.meta.get("weather_year")
            if proxy_year is None:
                available_years = pv_df.index.year.unique()
                proxy_year = int(min(available_years, key=lambda y: abs(y - n_year)))
                print(
                    f"[Phase 1] Using weather proxy year {proxy_year} for model year {n_year} ..."
                )
            else:
                print(
                    f"[Phase 1] Using weather_year override {proxy_year} from load_network() ..."
                )
            pv_mask = pv_df.index.year == proxy_year
            wind_mask = wind_df.index.year == proxy_year
            length = min(int(pv_mask.sum()), len(n.snapshots))
            pv_cf = pv_df[pv_mask].iloc[:length, 0].values
            wind_cf = wind_df[wind_mask].iloc[:length, 0].values
            if length < len(n.snapshots):
                pv_cf = np.pad(pv_cf, (0, len(n.snapshots) - length), mode="edge")
                wind_cf = np.pad(wind_cf, (0, len(n.snapshots) - length), mode="edge")
        else:
            pv_cf = pv_df.reindex(n.snapshots).ffill().iloc[:, 0].values
            wind_cf = wind_df.reindex(n.snapshots).ffill().iloc[:, 0].values
    elif ERA5_CF_HIST_CSV.exists():
        print("[Phase 1]   Using Reading historical/synthetic CFs (Task 0D)")
        hist_df = pd.read_csv(ERA5_CF_HIST_CSV, index_col=0, parse_dates=True)
        last_yr = hist_df.index.year.max()
        # Extract last full year mapped to snapshot length
        target_df = hist_df[hist_df.index.year == last_yr]
        length = min(len(target_df), len(n.snapshots))
        pv_cf = target_df["solar_pv_cf"].iloc[:length].values
        wind_cf = target_df["wind_onshore_cf"].iloc[:length].values
    else:
        print("[Phase 1] WARNING: No CF data found. Using network defaults.")
        return

    if solar_gens and pv_cf is not None:
        for gen in solar_gens:
            n.generators_t.p_max_pu[gen] = pv_cf
    if wind_on and wind_cf is not None:
        for gen in wind_on:
            n.generators_t.p_max_pu[gen] = wind_cf

    # Add load shedding (dummy generator with huge marginal cost) to ensure feasibility
    # applied to each bus in the multi-node network
    if "load_shedding" not in n.carriers.index:
        n.add("Carrier", "load_shedding")
    if not any("load_shedding" in g for g in n.generators.index):
        for bus_name in n.buses.index:
            n.add(
                "Generator",
                f"load_shedding_{bus_name}",
                bus=bus_name,
                carrier="load_shedding",
                p_nom=1e6,
                marginal_cost=10000.0,
            )

    # Allow some curtailable excess (dummy load with negative cost / zero cost)
    if "curtailment_dump" not in n.loads.index:
        bus_name = n.buses.index[0]
        # In PyPSA, curtailment is typically handled by setting p_max_pu and letting
        # the model dispatch less than max. We don't explicitly need a dump load
        # unless modelling negative prices.
        pass


def run_baseline_optimisation(n: pypsa.Network) -> None:
    """Solve the LOPF (Linear Optimal Power Flow) for 1 year."""
    print("\n[Phase 1] Running Linear Optimal Power Flow (baseline)...")

    if ENABLE_ENDOGENOUS_INVESTMENT:
        print(
            "[Phase 1] Enabling endogenous capacity investment (extendable VRE & Storage) for baseline..."
        )
        for g in n.generators.index:
            if n.generators.at[g, "carrier"] in ["solar", "onwind", "offwind"]:
                n.generators.at[g, "p_nom_min"] = n.generators.at[g, "p_nom"]
                n.generators.at[g, "p_nom_extendable"] = True

        if not n.storage_units.empty:
            for su in n.storage_units.index:
                if n.storage_units.at[su, "carrier"] in ["battery", "H2"]:
                    n.storage_units.at[su, "p_nom_min"] = n.storage_units.at[
                        su, "p_nom"
                    ]
                    n.storage_units.at[su, "p_nom_extendable"] = True

    # We use linopy interface built into PyPSA
    n.sanitize()
    status, condition = n.optimize(
        solver_name="highs",
        solver_options={
            "solver": "ipm",
            "run_crossover": "on",
            "threads": 8,
        },
    )

    if status not in ["ok", "warning"]:
        raise RuntimeError(
            f"Baseline Phase 1 failed: status={status}, condition={condition}"
        )

    # GUARD FIX: Ensure objective is not None before casting
    if n.objective is None:
        raise RuntimeError(
            f"Baseline Phase 1 completed but no objective found. status={status}, condition={condition}"
        )
    objective_val = float(n.objective)
    print(f"\n[Phase 1] Solver status : {status}")
    print(f"[Phase 1] Condition     : {condition}")

    if status != "ok":
        print("[Phase 1] WARNING: Model did not solve flawlessly. Check feasibility.")

    # Save solved network
    n.export_to_netcdf(str(BASELINE_SOLVED_NC))
    print(f"[Phase 1] Baseline solved network saved -> {BASELINE_NC}")


def plot_dispatch(n: pypsa.Network) -> None:
    """Generate a single week dispatch plot."""
    if n.generators_t.p.empty:
        print("[Phase 1] No dispatch results found to plot.")
        return

    print("[Phase 1] Generating dispatch visualization...")

    # Take a week in summer (e.g. July)
    summer_week = n.snapshots[(n.snapshots.month == 7) & (n.snapshots.day <= 7)]
    if len(summer_week) == 0:
        # Fallback to first 168 hours
        summer_week = n.snapshots[:168]

    p_by_carrier = _group_columns_by_carrier(
        n.generators_t.p.loc[summer_week],
        n.generators.carrier,
    )
    load = n.loads_t.p_set.loc[summer_week].sum(axis=1)

    # Handle storage (stacking charge and discharge separately)
    # n.storage_units_t.p represents net dispatch (positive = discharge, negative = charge)
    if not n.storage_units_t.p.empty:
        su_p = _group_columns_by_carrier(
            n.storage_units_t.p.loc[summer_week],
            n.storage_units.carrier,
        )
        su_charge = su_p.clip(upper=0)
        su_discharge = su_p.clip(lower=0)

        # Add discharge to generators stack
        for c in su_discharge.columns:
            p_by_carrier[c] = p_by_carrier.get(c, 0) + su_discharge[c]
    else:
        su_charge = pd.DataFrame(index=summer_week)

    fig, ax = plt.subplots(figsize=(12, 6))

    # Colors for carriers
    colors = {
        "solar": "#ffcc00",
        "onwind": "#0099ff",
        "offwind": "#0055aa",
        "OCGT": "#cc9966",
        "gas": "#cc9966",
        "lignite": "#8b4513",
        "nuclear": "#ff5500",
        "battery": "#66cc66",
        "H2": "#ffb6c1",
        "load_shedding": "#cc0000",
    }

    # Match colors dynamically
    plot_colors = [colors.get(c, "#aaaaaa") for c in p_by_carrier.columns]

    # Stackplot for generation
    ax.stackplot(
        p_by_carrier.index,
        p_by_carrier.T.values,
        labels=p_by_carrier.columns,
        colors=plot_colors,
        alpha=0.8,
    )

    # Overlay load curve (Total Load + Storage Charting)
    adjusted_load = load - su_charge.sum(axis=1)  # effective demand for generators
    ax.plot(
        adjusted_load.index,
        adjusted_load.values,
        color="black",
        linewidth=2,
        label="Load + Storage Charging",
    )

    ax.set_title("PyPSA-DE Baseline Dispatch (1 Week)", fontsize=14, pad=10)
    ax.set_ylabel("Power (MW)", fontsize=12)
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        list(reversed(handles)),
        list(reversed(labels)),
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        title="Carriers",
    )

    plt.tight_layout()
    fig.savefig(DISPATCH_PLOT_PNG, dpi=300)
    plt.close()
    print(f"[Phase 1] Plot saved -> {DISPATCH_PLOT_PNG.name}")


def print_baseline_metrics(n: pypsa.Network) -> None:
    """Compute and print key KPIs for the 2025 baseline."""
    print("\n" + "=" * 60)
    print("  PHASE 1 — Baseline KPIs (Exogenous Fixed Industry)")
    print("=" * 60)

    if n.objective is not None:
        total_cost_bn = n.objective / 1e9
        print(f"  Total System Cost       : € {total_cost_bn:.2f} billion / year")

    total_load_twh = n.loads_t.p_set.sum().sum() / 1e6
    print(f"  Total Electricity Demand: {total_load_twh:.1f} TWh")

    # Curtailment
    available_res = 0.0
    actual_res = 0.0
    for g in n.generators.index:
        c = n.generators.at[g, "carrier"]
        if c in ["solar", "onwind", "offwind", "wind"]:
            capacity = float(n.generators.at[g, "p_nom"])
            if "p_nom_opt" in n.generators.columns and pd.notna(
                n.generators.at[g, "p_nom_opt"]
            ):
                capacity = max(capacity, float(n.generators.at[g, "p_nom_opt"]))

            # Potentially available (check if dynamic max exists)
            if g in n.generators_t.p_max_pu.columns:
                p_max = n.generators_t.p_max_pu[g]
            else:
                p_max = (
                    n.generators.at[g, "p_max_pu"]
                    if "p_max_pu" in n.generators.columns
                    else 1.0
                )

            avail = p_max * capacity
            available_res += (
                avail.sum() if hasattr(avail, "sum") else (avail * len(n.snapshots))
            )
            if g in n.generators_t.p.columns:
                actual_res += n.generators_t.p[g].clip(lower=0).sum()

    curtailed = max(available_res - actual_res, 0.0)
    curtail_pct = (curtailed / available_res * 100) if available_res > 0 else 0.0

    print(f"  VRE Curtailed           : {curtailed / 1e6:.1f} TWh ({curtail_pct:.1f}%)")

    # Load shedding
    shedding_cols = [
        generator
        for generator in n.generators.index
        if n.generators.at[generator, "carrier"] == "load_shedding"
        and generator in n.generators_t.p.columns
    ]
    if shedding_cols:
        shed = n.generators_t.p[shedding_cols].clip(lower=0).sum().sum() / 1e6
        print(f"  Load Shedding / Deficit : {shed:.3f} TWh")

    print("=" * 60 + "\n")


def run_phase1() -> None:
    n = load_network()
    inject_actual_load(n)
    inject_capacity_factors(n)
    run_baseline_optimisation(n)
    plot_dispatch(n)
    print_baseline_metrics(n)


if __name__ == "__main__":
    run_phase1()
