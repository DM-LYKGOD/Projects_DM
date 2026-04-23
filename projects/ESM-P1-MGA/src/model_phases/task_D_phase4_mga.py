"""
Phase 4: modelling to generate alternatives (MGA).
"""

import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pypsa

# matplotlib.use("Agg")  # Commented to allow inline display in notebook
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import (
    DEFAULT_MODEL_YEAR,
    ENABLE_ENDOGENOUS_INVESTMENT,
    FIGURES_DIR,
    INDUSTRIAL_DIR,
    MGA_DEFAULT_EPSILON,
    MGA_EPSILON_VALUES,
    MGA_N_ALTERNATIVES,
    MGA_RESULTS_CSV,
    RES_MULTIPLIER_BY_YEAR,
)
from src.model_phases import task_B_phase2_industrial as industry
from src.model_phases.task_A_phase1_baseline import (
    inject_actual_load,
    inject_capacity_factors,
    load_network,
)


MGA_SCATTER_PNG = FIGURES_DIR / "mga_alternatives_scatter.png"
MGA_FRONTIER_PNG = FIGURES_DIR / "mga_flexibility_frontier.png"


def _prepare_network(year: int = DEFAULT_MODEL_YEAR) -> pypsa.Network:
    n = load_network()
    inject_actual_load(n)
    inject_capacity_factors(n)
    industry.remove_exogenous_cement_load(n, year=year)
    plants = industry.load_regional_plants(n)
    industry.add_cement_dummy_generators(n, plants)

    multiplier = RES_MULTIPLIER_BY_YEAR.get(year, 1.0)
    if ENABLE_ENDOGENOUS_INVESTMENT:
        for generator in n.generators.index:
            if n.generators.at[generator, "carrier"] in {"solar", "onwind", "offwind"}:
                n.generators.at[generator, "p_nom_min"] = n.generators.at[
                    generator, "p_nom"
                ]
                n.generators.at[generator, "p_nom_extendable"] = True
        if not n.storage_units.empty:
            for storage_unit in n.storage_units.index:
                if n.storage_units.at[storage_unit, "carrier"] in {"battery", "H2"}:
                    n.storage_units.at[storage_unit, "p_nom_min"] = n.storage_units.at[
                        storage_unit, "p_nom"
                    ]
                    n.storage_units.at[storage_unit, "p_nom_extendable"] = True
    else:
        for generator in n.generators.index:
            if n.generators.at[generator, "carrier"] in {"solar", "onwind", "offwind"}:
                n.generators.at[generator, "p_nom"] *= multiplier

    return n


def _extract_shadow_prices(n: pypsa.Network, year: int) -> None:
    shadow_path = INDUSTRIAL_DIR / f"shadow_price_cement_{year}.csv"
    try:
        dual = n.model.dual["cement_hourly_balance"]
        if hasattr(dual, "to_series"):
            dual_series = dual.to_series()
        else:
            values = np.asarray(getattr(dual, "values", dual)).reshape(-1)
            dual_series = pd.Series(
                values, index=pd.Index(n.snapshots[: len(values)], name="snapshot")
            )

        if (
            isinstance(dual_series.index, pd.MultiIndex)
            and "snapshot" in dual_series.index.names
        ):
            dual_series.index = dual_series.index.get_level_values("snapshot")

        dual_series.index = pd.to_datetime(dual_series.index)
        dual_series = dual_series.sort_index()
        dual_series.name = "shadow_price_eur_per_t"
        dual_series.to_csv(shadow_path, header=True)
        print(
            "[MGA] Shadow price (eur/t cement rescheduled): "
            f"mean={dual_series.mean():.3f} "
            f"min={dual_series.min():.3f} "
            f"max={dual_series.max():.3f}"
        )
        print(f"[MGA] Shadow prices saved -> {shadow_path.name}")
    except Exception as exc:
        print(f"[MGA] Shadow price extraction skipped: {exc}")


def _solve_base(n: pypsa.Network, year: int) -> float:
    print("[MGA] Step 1: solving baseline minimum-cost objective...")
    n.sanitize()
    status, condition = n.optimize(
        solver_name="highs",
        solver_options={
            "solver": "ipm",
            "run_crossover": "on",
            "threads": 8,
        },
        extra_functionality=lambda net, snapshots: industry.add_endogenous_industry(
            net, snapshots, year=year
        ),
    )
    if status not in ["ok", "warning"]:
        raise RuntimeError(f"Baseline failed: status={status}, condition={condition}")
    
    if condition == "infeasible":
        print(f"[MGA] WARNING: Solver reported infeasibility. Proceeding cautiously. Status={status}")

    # GUARD FIX: Ensure objective is not None before casting
    if n.objective is None:
        raise RuntimeError(
            f"Baseline solver completed but no objective found. "
            f"status={status}, condition={condition}"
        )
    c_opt = float(n.objective)
    print(f"[MGA] C_opt = EUR {c_opt / 1e9:.4f} billion")
    _extract_shadow_prices(n, year=year)
    return c_opt


def _directional_vector(
    n_dims: int, previous_directions: list[np.ndarray]
) -> np.ndarray:
    direction = np.random.normal(size=n_dims)
    for previous in previous_directions:
        previous_norm = previous / (np.linalg.norm(previous) + 1e-12)
        direction -= np.dot(direction, previous_norm) * previous_norm
    return direction / (np.linalg.norm(direction) + 1e-12)


def run_mga_epsilon(
    c_opt: float,
    epsilon: float,
    n_alts: int,
    year: int = DEFAULT_MODEL_YEAR,
) -> list[dict]:
    max_cost = c_opt * (1.0 + epsilon)
    print(
        f"\n[MGA] epsilon={epsilon * 100:.0f}% | "
        f"budget=EUR {max_cost / 1e9:.4f} billion | alternatives={n_alts}"
    )

    n_template = _prepare_network(year=year)
    snapshots = n_template.snapshots
    plants = industry.load_regional_plants(n_template)
    idx_p = plants["plant"].tolist()
    
    n_dims = len(snapshots) * len(idx_p)
    results: list[dict] = []
    previous_directions: list[np.ndarray] = []

    for alternative in range(n_alts):
        direction_flat = _directional_vector(n_dims, previous_directions)
        # Reshape to match [snapshot, plant]
        direction = direction_flat.reshape(len(snapshots), len(idx_p))
        n_fresh = n_template.copy()

        def _mga_cb(n_inner, snapshots, _direction=direction, _max_cost=max_cost):
            # Capture system cost BEFORE add_endogenous_industry overwrites it
            system_cost_expr = n_inner.model.objective.expression
            industry.add_endogenous_industry(n_inner, snapshots, year=year)
            model = n_inner.model
            # Constrain the full system cost, not the industrial sub-cost
            model.add_constraints(
                system_cost_expr <= _max_cost,
                name="mga_slack_cost"
            )
            clk = model.variables["ClinkerProduction"]
            model.objective = (clk * _direction).sum()

        n_fresh.sanitize()
        status, condition = n_fresh.optimize(
            solver_name="highs",
            solver_options={
                "solver": "ipm",
                "run_crossover": "on",
                "threads": 8,
            },
            extra_functionality=_mga_cb,
        )
        if status != "ok":
            print(f"    Alt {alternative + 1:02d} failed ({status}, {condition})")
            continue

        clinker, _, storage = industry._extract_solution(n_fresh)
        clinker_total = clinker.sum(axis=1)
        previous_directions.append(direction_flat)
        hour_weights = clinker_total.index.hour

        timing_weighted_hour = float(
            (clinker_total * hour_weights).sum() / (clinker_total.sum() + 1e-9)
        )
        mean_storage_t = float(storage_total.mean())
        night_prod_t_h = float(clinker_total[clinker_total.index.hour < 6].mean())
        day_mask = (clinker_total.index.hour >= 10) & (clinker_total.index.hour < 18)
        day_prod_t_h = float(clinker_total[day_mask].mean())
        total_prod_mt = float(clinker_total.sum() / 1e6)
        cost_delta_pct = float((float(n_fresh.objective) - c_opt) / c_opt * 100)

        results.append(
            {
                "epsilon": epsilon,
                "alternative": alternative,
                "timing_weighted_hour": timing_weighted_hour,
                "mean_storage_t": mean_storage_t,
                "night_prod_t_h": night_prod_t_h,
                "day_prod_t_h": day_prod_t_h,
                "total_prod_Mt": total_prod_mt,
                "cost_above_optimal_pct": cost_delta_pct,
            }
        )

        standardized = clinker_total.values - clinker_total.values.mean()
        standardized = standardized / (standardized.std() + 1e-12)
        previous_directions.append(standardized)

        print(
            f"    Alt {alternative + 1:02d} | "
            f"timing={timing_weighted_hour:.2f}h | "
            f"storage={mean_storage_t:.0f} t | "
            f"night={night_prod_t_h:.0f} t/h | "
            f"cost={cost_delta_pct:.2f}%"
        )

    return results


def _plot_mga_scatter(df: pd.DataFrame) -> None:
    if df.empty:
        return

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.suptitle("MGA near-optimal alternative space", fontsize=13, fontweight="bold")

    epsilon_values = sorted(df["epsilon"].unique())
    import matplotlib
    cmap = matplotlib.colormaps.get_cmap("plasma")
    panels = [
        ("timing_weighted_hour", "Weighted mean production hour"),
        ("night_prod_t_h", "Mean night production (t/h)"),
        ("cost_above_optimal_pct", "Cost above optimal (%)"),
    ]

    for axis, (x_col, x_label) in zip(axes, panels):
        for idx, epsilon in enumerate(epsilon_values):
            subset = df[df["epsilon"] == epsilon]
            axis.scatter(
                subset[x_col],
                subset["mean_storage_t"],
                color=cmap(idx),
                alpha=0.75,
                s=50,
                edgecolors="k",
                linewidths=0.3,
                label=f"eps={epsilon * 100:.0f}%",
            )
        axis.set_xlabel(x_label)
        axis.set_ylabel("Mean clinker storage level (t)")
        axis.grid(alpha=0.4, linestyle="--")
        axis.legend(fontsize=8, title="Cost slack")

    plt.tight_layout()
    fig.savefig(MGA_SCATTER_PNG, dpi=300)
    plt.close(fig)
    print(f"[MGA] Scatter plot saved -> {MGA_SCATTER_PNG.name}")


def _plot_flexibility_frontier(df: pd.DataFrame) -> None:
    if df.empty or df["epsilon"].nunique() < 2:
        return

    frontier = (
        df.groupby("epsilon")
        .agg(
            timing_range=(
                "timing_weighted_hour",
                lambda values: values.max() - values.min(),
            ),
            storage_range=(
                "mean_storage_t",
                lambda values: values.max() - values.min(),
            ),
            cost_mean=("cost_above_optimal_pct", "mean"),
        )
        .reset_index()
    )

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(13, 5))
    ax_right_twin = ax_left.twinx()

    ax_left.plot(
        frontier["epsilon"] * 100,
        frontier["timing_range"],
        "o-",
        color="#0055a4",
        linewidth=2,
        label="Timing spread (h)",
    )
    ax_right_twin.plot(
        frontier["epsilon"] * 100,
        frontier["storage_range"] / 1e3,
        "s--",
        color="#cc0000",
        linewidth=2,
        label="Storage spread (kt)",
    )
    ax_left.set_xlabel("Cost relaxation epsilon (%)")
    ax_left.set_ylabel("Timing spread (hours)", color="#0055a4")
    ax_right_twin.set_ylabel("Clinker storage spread (kt)", color="#cc0000")
    ax_left.grid(alpha=0.4, linestyle="--")
    left_handles, left_labels = ax_left.get_legend_handles_labels()
    right_handles, right_labels = ax_right_twin.get_legend_handles_labels()
    ax_left.legend(
        left_handles + right_handles, left_labels + right_labels, loc="upper left"
    )

    ax_right.scatter(
        frontier["cost_mean"],
        frontier["storage_range"] / 1e3,
        c=frontier["epsilon"] * 100,
        cmap="viridis",
        s=90,
        edgecolors="k",
        linewidths=0.4,
    )
    for _, row in frontier.iterrows():
        ax_right.annotate(
            f"eps={row['epsilon'] * 100:.0f}%",
            (row["cost_mean"], row["storage_range"] / 1e3),
            textcoords="offset points",
            xytext=(5, 4),
            fontsize=8,
        )
    ax_right.set_xlabel("Mean cost above optimal (%)")
    ax_right.set_ylabel("Clinker storage spread (kt)")
    ax_right.grid(alpha=0.4, linestyle="--")

    plt.tight_layout()
    fig.savefig(MGA_FRONTIER_PNG, dpi=300)
    plt.close(fig)
    print(f"[MGA] Flexibility frontier saved -> {MGA_FRONTIER_PNG.name}")


def run_mga(
    year: int = DEFAULT_MODEL_YEAR,
    epsilon: float = MGA_DEFAULT_EPSILON,
    full_sweep: bool = False,
) -> None:
    print("\n" + "=" * 60)
    print(f"  PHASE 4 - MGA ({year})")
    print("=" * 60)

    n_base = _prepare_network(year=year)
    c_opt = _solve_base(n_base, year=year)

    epsilon_values = MGA_EPSILON_VALUES if full_sweep else [epsilon]
    all_results: list[dict] = []
    for epsilon_value in epsilon_values:
        all_results.extend(
            run_mga_epsilon(c_opt, epsilon_value, MGA_N_ALTERNATIVES, year=year)
        )

    if not all_results:
        print("[MGA] No alternatives generated.")
        return

    df = pd.DataFrame(all_results)
    df.to_csv(MGA_RESULTS_CSV, index=False)
    print(f"[MGA] Results saved -> {MGA_RESULTS_CSV}")
    print(df.describe(include="all").to_string())

    _plot_mga_scatter(df)
    _plot_flexibility_frontier(df)


if __name__ == "__main__":
    run_mga()
