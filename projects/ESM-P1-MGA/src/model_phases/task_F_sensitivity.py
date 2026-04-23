"""
Phase 6: weather-year and storage sensitivity analysis.
"""

import argparse
import sys
from functools import lru_cache
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

# matplotlib.use("Agg")  # Commented to allow inline display in notebook
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import (
    DEFAULT_MODEL_YEAR,
    ERA5_CF_HIST_CSV,
    FIGURES_DIR,
    INDUSTRIAL_DIR,
    MGA_N_ALTERNATIVES,
    MGA_STORAGE_SENSITIVITY_EPSILON_VALUES,
    RES_MULTIPLIER_BY_YEAR,
    STORAGE_SENSITIVITY_SILO_DAYS,
    WEATHER_ENSEMBLE_YEARS,
)
from src.model_phases import task_B_phase2_industrial as industry
from src.model_phases import task_D_phase4_mga as mga
from src.model_phases.task_A_phase1_baseline import inject_actual_load, load_network


WEATHER_RESULTS_CSV = INDUSTRIAL_DIR / "sensitivity_weather_results.csv"
STORAGE_RESULTS_CSV = INDUSTRIAL_DIR / "sensitivity_storage_results.csv"
WEATHER_PLOT_PNG = FIGURES_DIR / "sensitivity_weather.png"
STORAGE_PLOT_PNG = FIGURES_DIR / "sensitivity_storage.png"


@lru_cache(maxsize=1)
def _load_historical_cf() -> pd.DataFrame:
    if not ERA5_CF_HIST_CSV.exists():
        raise FileNotFoundError(
            f"Historical ERA5 capacity factor file not found: {ERA5_CF_HIST_CSV}"
        )
    return pd.read_csv(ERA5_CF_HIST_CSV, index_col=0, parse_dates=True)


def _resolve_weather_years() -> list[int]:
    hist_df = _load_historical_cf()
    available = sorted(hist_df.index.year.unique())
    configured = [year for year in WEATHER_ENSEMBLE_YEARS if year in available]
    return configured or available


def _inject_historical_cf(n, weather_year: int) -> bool:
    hist_df = _load_historical_cf()
    year_df = hist_df[hist_df.index.year == weather_year]
    if year_df.empty:
        print(f"[Sensitivity] No ERA5 data for weather year {weather_year}. Skipping.")
        return False

    length = min(len(year_df), len(n.snapshots))
    pv_cf = year_df["solar_pv_cf"].iloc[:length].to_numpy()
    wind_cf = year_df["wind_onshore_cf"].iloc[:length].to_numpy()
    if length < len(n.snapshots):
        pv_cf = np.pad(pv_cf, (0, len(n.snapshots) - length), mode="edge")
        wind_cf = np.pad(wind_cf, (0, len(n.snapshots) - length), mode="edge")

    solar_generators = [
        generator for generator in n.generators.index if "solar" in generator.lower()
    ]
    wind_generators = [
        generator
        for generator in n.generators.index
        if "onwind" in generator.lower() or "onshore" in generator.lower()
    ]

    for generator in solar_generators:
        n.generators_t.p_max_pu[generator] = pv_cf
    for generator in wind_generators:
        n.generators_t.p_max_pu[generator] = wind_cf
    return True


def _run_weather_scenario(
    model_year: int, weather_year: int, renewable_multiplier: float
) -> dict | None:
    print(
        f"[Sensitivity] model_year={model_year}, "
        f"weather_year={weather_year}, RESx{renewable_multiplier:.1f}"
    )

    n = load_network()
    inject_actual_load(n)
    if not _inject_historical_cf(n, weather_year):
        return None

    industry.remove_exogenous_cement_load(n, year=model_year)
    plants = industry.load_regional_plants(n)
    industry.add_cement_dummy_generators(n, plants)

    for generator in n.generators.index:
        if n.generators.at[generator, "carrier"] in {"solar", "onwind", "offwind"}:
            n.generators.at[generator, "p_nom"] *= renewable_multiplier

    n.sanitize()
    status, condition = n.optimize(
        solver_name="highs",
        solver_options={
            "solver": "ipm",
            "run_crossover": "on",
            "threads": 8,
        },
        extra_functionality=lambda net, snapshots: industry.add_endogenous_industry(
            net, snapshots, year=model_year
        ),
    )
    if status not in ["ok", "warning"]:
        print(f"[Sensitivity] Weather scenario failed: status={status}, condition={condition}")
        return None

    clinker, _, storage = industry._extract_solution(n)
    gen_by_carrier = (
        n.generators_t.p.T.groupby(n.generators.carrier).sum().T.sum() / 1e6
    )
    # GUARD FIX: Ensure objective is not None before casting
    if n.objective is None:
        raise RuntimeError(
            f"Baseline solver completed but no objective found. "
            f"status={status}, condition={condition}"
        )
    return {
        "weather_year": weather_year,
        "system_cost_B_EUR": float(n.objective / 1e9),
        "industrial_twh": float(-gen_by_carrier.get("industrial_demand", 0.0)),
        "max_storage_kt": float(storage.sum(axis=1).max() / 1e3),
        "clinker_prod_mt": float(clinker.sum().sum() / 1e6),
    }


def _plot_weather_sensitivity(df: pd.DataFrame) -> None:
    if df.empty:
        return

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Weather-year sensitivity", fontsize=13, fontweight="bold")

    panel_specs = [
        ("system_cost_B_EUR", "System cost (B EUR)", "#003f5c"),
        ("max_storage_kt", "Peak clinker storage (kt)", "#ffa600"),
        ("industrial_twh", "Industrial grid load (TWh)", "#bc5090"),
    ]

    for axis, (column, ylabel, color) in zip(axes, panel_specs):
        axis.bar(
            df["weather_year"],
            df[column],
            color=color,
            alpha=0.75,
            edgecolor="k",
            linewidth=0.4,
        )
        mean_value = df[column].mean()
        axis.axhline(
            mean_value,
            color="k",
            linestyle="--",
            linewidth=1.2,
            label=f"Mean: {mean_value:.2f}",
        )
        axis.set_xlabel("Weather year")
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.4, linestyle="--")
        axis.legend(fontsize=8)

    plt.tight_layout()
    fig.savefig(WEATHER_PLOT_PNG, dpi=300)
    plt.close(fig)
    print(f"[Sensitivity] Weather plot saved -> {WEATHER_PLOT_PNG.name}")


def run_weather_sensitivity(model_year: int = DEFAULT_MODEL_YEAR) -> pd.DataFrame:
    print("\n" + "=" * 65)
    print(f"  SENSITIVITY A - Weather year ensemble (model year {model_year})")
    print("=" * 65)

    weather_years = _resolve_weather_years()
    if not weather_years:
        print("[Sensitivity] No historical weather years available.")
        return pd.DataFrame()

    print(
        f"[Sensitivity] Using historical ERA5 years: {weather_years[0]}-{weather_years[-1]}"
    )
    renewable_multiplier = RES_MULTIPLIER_BY_YEAR.get(model_year, 1.0)
    records = []
    for weather_year in weather_years:
        record = _run_weather_scenario(model_year, weather_year, renewable_multiplier)
        if record is not None:
            records.append(record)

    if not records:
        print("[Sensitivity] No successful weather runs.")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df.to_csv(WEATHER_RESULTS_CSV, index=False)
    print(f"[Sensitivity] Weather results saved -> {WEATHER_RESULTS_CSV.name}")
    _plot_weather_sensitivity(df)
    return df


def run_mga_with_silo(
    c_opt: float,
    epsilon: float,
    n_alts: int,
    year: int,
    s_max_days: int,
) -> list[dict]:
    max_cost = c_opt * (1.0 + epsilon)
    n_template = mga._prepare_network(year=year)
    n_dims = len(n_template.snapshots)
    results: list[dict] = []
    previous_directions: list[np.ndarray] = []

    for alternative in range(n_alts):
        direction = mga._directional_vector(n_dims, previous_directions)
        n_fresh = n_template.copy()

        def _callback(
            net, snapshots, _direction=direction, _max_cost=max_cost, _days=s_max_days
        ):
            industry.add_endogenous_industry(
                net, snapshots, year=year, s_max_days_override=_days
            )
            model = net.model
            model.add_constraints(
                model.objective.expression <= _max_cost, name="mga_slack_cost"
            )
            clinker = model.variables["ClinkerProduction"].sum("plant")
            model.objective = (clinker * _direction).sum()

        n_fresh.sanitize()
        status, condition = n_fresh.optimize(
            solver_name="highs",
            solver_options={
                "solver": "ipm",
                "run_crossover": "on",
                "threads": 8,
            },
            extra_functionality=_callback,
        )
        if status != "ok":
            print(
                f"    [S={s_max_days}d, eps={epsilon * 100:.0f}%] Alt {alternative + 1:02d} failed ({status}, {condition})"
            )
            continue

        clinker, _, storage = industry._extract_solution(n_fresh)
        clinker_total = clinker.sum(axis=1)
        storage_total = storage.sum(axis=1)
        results.append(
            {
                "s_max_days": s_max_days,
                "epsilon": epsilon,
                "alternative": alternative,
                "timing_weighted_hour": float(
                    (clinker_total * clinker_total.index.hour).sum()
                    / (clinker_total.sum() + 1e-9)
                ),
                "mean_storage_t": float(storage_total.mean()),
                "max_storage_t": float(storage_total.max()),
                "cost_above_optimal_pct": float(
                    (float(n_fresh.objective) - c_opt) / c_opt * 100
                ),
            }
        )

        standardized = clinker_total.values - clinker_total.values.mean()
        standardized = standardized / (standardized.std() + 1e-12)
        previous_directions.append(standardized)

    return results


def _plot_storage_sensitivity(df: pd.DataFrame, silo_days: tuple[int, ...]) -> None:
    if df.empty:
        return

    frontier = (
        df.groupby(["s_max_days", "epsilon"])
        .agg(
            storage_spread=(
                "mean_storage_t",
                lambda values: values.max() - values.min(),
            ),
            timing_spread=(
                "timing_weighted_hour",
                lambda values: values.max() - values.min(),
            ),
        )
        .reset_index()
    )

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Silo-horizon sensitivity", fontsize=13, fontweight="bold")
    colors = {silo_days[0]: "#003f5c"}
    if len(silo_days) > 1:
        colors[silo_days[1]] = "#ffa600"

    for axis, (column, ylabel) in zip(
        axes,
        [
            ("storage_spread", "Storage level spread (t)"),
            ("timing_spread", "Timing spread (h)"),
        ],
    ):
        for days in silo_days:
            subset = frontier[frontier["s_max_days"] == days]
            axis.plot(
                subset["epsilon"] * 100,
                subset[column],
                marker="o",
                linewidth=2,
                color=colors.get(days, "#7a5195"),
                label=f"Silo={days}d",
            )
        axis.set_xlabel("Cost relaxation epsilon (%)")
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.4, linestyle="--")
        axis.legend()

    plt.tight_layout()
    fig.savefig(STORAGE_PLOT_PNG, dpi=300)
    plt.close(fig)
    print(f"[Sensitivity] Storage plot saved -> {STORAGE_PLOT_PNG.name}")


def run_storage_sensitivity(
    year: int = DEFAULT_MODEL_YEAR,
    silo_days: tuple[int, ...] = STORAGE_SENSITIVITY_SILO_DAYS,
) -> pd.DataFrame:
    print("\n" + "=" * 65)
    print(f"  SENSITIVITY B - Silo horizon sensitivity (year {year})")
    print("=" * 65)

    n_base = mga._prepare_network(year=year)
    c_opt = mga._solve_base(n_base, year=year)

    all_records: list[dict] = []
    for days in silo_days:
        print(f"[Sensitivity] Silo horizon: {days} days")
        for epsilon in MGA_STORAGE_SENSITIVITY_EPSILON_VALUES:
            all_records.extend(
                run_mga_with_silo(c_opt, epsilon, MGA_N_ALTERNATIVES, year, days)
            )

    if not all_records:
        print("[Sensitivity] No storage sensitivity records generated.")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    df.to_csv(STORAGE_RESULTS_CSV, index=False)
    print(f"[Sensitivity] Storage results saved -> {STORAGE_RESULTS_CSV.name}")
    _plot_storage_sensitivity(df, silo_days)
    return df


def run_sensitivity(
    weather: bool = True, storage: bool = True, year: int = DEFAULT_MODEL_YEAR
) -> None:
    if weather:
        run_weather_sensitivity(model_year=year)
    if storage:
        run_storage_sensitivity(year=year)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 6 - sensitivity analysis")
    parser.add_argument("--year", type=int, default=DEFAULT_MODEL_YEAR)
    parser.add_argument("--weather", action="store_true")
    parser.add_argument("--storage", action="store_true")
    args = parser.parse_args()

    run_both = not (args.weather or args.storage)
    run_sensitivity(
        weather=args.weather or run_both,
        storage=args.storage or run_both,
        year=args.year,
    )
