"""
Phase 5: final evaluation and plotting.
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
    ANALYSIS_CARRIER_MC,
    BASELINE_SOLVED_NC,
    ENTSOE_GEN_CSV,
    ERA5_PV_CF_CSV,
    ERA5_WIND_CF_CSV,
    FIGURES_DIR,
    INDUSTRIAL_SOLVED_NC,
)


CORR_PLOT_PNG = FIGURES_DIR / "capacity_factor_correlations.png"
COST_PLOT_PNG = FIGURES_DIR / "cost_comparison_summary.png"


def _pick_first_series(frame: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    for column in candidates:
        if column in frame.columns:
            return frame[column].astype(float)
    return None


def _align_profile_to_generation(profile: pd.Series, generation_index: pd.Index) -> pd.Series:
    profile = profile.sort_index().astype(float)
    generation_index = pd.DatetimeIndex(generation_index)

    if len(profile) == len(generation_index):
        aligned = pd.Series(profile.to_numpy(), index=generation_index, name=profile.name)
        return aligned

    common_index = profile.index.intersection(generation_index)
    if len(common_index) >= 1000:
        return profile.reindex(generation_index).interpolate(limit_direction="both")

    profile_frame = pd.DataFrame(
        {
            "month": profile.index.month,
            "day": profile.index.day,
            "hour": profile.index.hour,
            "value": profile.to_numpy(),
        }
    )
    target_frame = pd.DataFrame(
        {
            "month": generation_index.month,
            "day": generation_index.day,
            "hour": generation_index.hour,
        },
        index=generation_index,
    )
    merged = target_frame.merge(profile_frame, on=["month", "day", "hour"], how="left")
    aligned = pd.Series(merged["value"].to_numpy(), index=generation_index, name=profile.name)
    return aligned.interpolate(limit_direction="both")


def _effective_generator_capacity(n: pypsa.Network, generator: str) -> float:
    p_nom = float(n.generators.at[generator, "p_nom"])
    if "p_nom_opt" in n.generators.columns and pd.notna(n.generators.at[generator, "p_nom_opt"]):
        return float(max(p_nom, n.generators.at[generator, "p_nom_opt"]))
    return p_nom


def _network_signature(n: pypsa.Network) -> dict:
    carrier_counts = n.generators["carrier"].value_counts().sort_index().to_dict()
    return {
        "buses": int(len(n.buses)),
        "loads": int(len(n.loads)),
        "generators": int(len(n.generators)),
        "storage_units": int(len(n.storage_units)),
        "snapshots": int(len(n.snapshots)),
        "carrier_counts": carrier_counts,
    }


def _networks_are_comparable(n_base: pypsa.Network, n_ind: pypsa.Network) -> bool:
    base_sig = _network_signature(n_base)
    ind_sig = _network_signature(n_ind)
    return all(
        base_sig[key] == ind_sig[key]
        for key in ["buses", "loads", "generators", "storage_units", "snapshots", "carrier_counts"]
    )


def plot_capacity_factors() -> None:
    print("\n[Phase 5] Step 1: evaluating capacity factor validity...")
    if not (ENTSOE_GEN_CSV.exists() and ERA5_PV_CF_CSV.exists() and ERA5_WIND_CF_CSV.exists()):
        print("[Phase 5] Missing raw CSVs for correlation plotting. Skipping.")
        return

    generation = pd.read_csv(ENTSOE_GEN_CSV, index_col=0, parse_dates=True)
    pv_cf = pd.read_csv(ERA5_PV_CF_CSV, index_col=0, parse_dates=True).iloc[:, 0].astype(float)
    wind_cf = pd.read_csv(ERA5_WIND_CF_CSV, index_col=0, parse_dates=True).iloc[:, 0].astype(float)

    solar_generation = _pick_first_series(generation, ["Solar", "Photovoltaik", "PV"])
    wind_onshore = _pick_first_series(generation, ["Wind_Onshore", "Onshore Wind"])
    wind_offshore = _pick_first_series(generation, ["Wind_Offshore", "Offshore Wind"])
    wind_generation = None
    if wind_onshore is not None or wind_offshore is not None:
        wind_generation = (
            (wind_onshore if wind_onshore is not None else 0.0)
            + (wind_offshore if wind_offshore is not None else 0.0)
        )

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Observed generation vs ERA5-derived capacity factors", fontsize=13, fontweight="bold")

    plotted_any = False
    panel_specs = [
        ("Solar", solar_generation, pv_cf, axes[0, 0], axes[0, 1], "#f6c945"),
        ("Wind", wind_generation, wind_cf, axes[1, 0], axes[1, 1], "#2b7bba"),
    ]

    for label, real_series, cf_series, time_axis, scatter_axis, color in panel_specs:
        if real_series is None or real_series.empty:
            time_axis.set_title(f"{label}: generation column not found")
            scatter_axis.set_title(f"{label}: skipped")
            continue

        aligned_cf = _align_profile_to_generation(cf_series, real_series.index)
        combined = pd.DataFrame({"generation": real_series, "cf": aligned_cf}).dropna()
        if combined.empty:
            time_axis.set_title(f"{label}: no overlapping data")
            scatter_axis.set_title(f"{label}: skipped")
            continue

        correlation = combined["generation"].corr(combined["cf"])
        print(f"[Phase 5] Pearson correlation ({label} generation vs ERA5 CF): {correlation:.3f}")

        preview = combined.iloc[:168]
        generation_scale = max(float(preview["generation"].max()), 1.0)
        time_axis.plot(preview.index, preview["generation"] / generation_scale, color=color, label="Generation (norm)")
        time_axis.plot(preview.index, preview["cf"], color="black", linewidth=1.2, label="Capacity factor")
        time_axis.set_title(f"{label}: first 168 hours")
        time_axis.grid(alpha=0.3, linestyle="--")
        time_axis.legend(fontsize=8)

        scatter_axis.scatter(combined["cf"], combined["generation"], s=10, alpha=0.3, color=color, edgecolors="none")
        scatter_axis.set_title(f"{label}: corr={correlation:.3f}")
        scatter_axis.set_xlabel("Capacity factor")
        scatter_axis.set_ylabel("Generation (MW)")
        scatter_axis.grid(alpha=0.3, linestyle="--")
        plotted_any = True

    plt.tight_layout()
    if plotted_any:
        fig.savefig(CORR_PLOT_PNG, dpi=300)
        print(f"[Phase 5] Correlation plot saved -> {CORR_PLOT_PNG.name}")
    plt.close(fig)


def compare_model_runs() -> None:
    print("\n[Phase 5] Step 2: comparing baseline vs industrial runs...")

    if not BASELINE_SOLVED_NC.exists() or not INDUSTRIAL_SOLVED_NC.exists():
        print("[Phase 5] Missing solved .nc files. Did Phase 1 and Phase 2 complete?")
        return

    n_base = pypsa.Network(str(BASELINE_SOLVED_NC))
    n_ind = pypsa.Network(str(INDUSTRIAL_SOLVED_NC))
    comparable = _networks_are_comparable(n_base, n_ind)
    base_signature = _network_signature(n_base)
    ind_signature = _network_signature(n_ind)

    if not comparable:
        print("[Phase 5] Warning: baseline and industrial solved networks are structurally different.")
        print(f"[Phase 5] Baseline signature  : {base_signature}")
        print(f"[Phase 5] Industrial signature: {ind_signature}")

    def operational_cost(n: pypsa.Network) -> float:
        if n.generators_t.p.empty:
            return 0.0
        total_cost = 0.0
        for generator in n.generators.index:
            if generator not in n.generators_t.p.columns:
                continue
            carrier = n.generators.at[generator, "carrier"]
            marginal_cost = ANALYSIS_CARRIER_MC.get(carrier, 0.0)
            total_cost += float((n.generators_t.p[generator].clip(lower=0) * marginal_cost).sum())
        return total_cost / 1e9

    def curtailment_twh(n: pypsa.Network) -> float:
        available = 0.0
        actual = 0.0
        for generator in n.generators.index:
            carrier = n.generators.at[generator, "carrier"]
            if carrier not in {"solar", "onwind", "offwind", "wind"}:
                continue
            capacity = _effective_generator_capacity(n, generator)
            if generator in n.generators_t.p_max_pu.columns:
                available += float((n.generators_t.p_max_pu[generator].clip(lower=0) * capacity).sum())
            else:
                p_max_pu = float(n.generators.at[generator, "p_max_pu"]) if "p_max_pu" in n.generators.columns else 1.0
                available += p_max_pu * capacity * len(n.snapshots)
            if generator in n.generators_t.p.columns:
                actual += float(n.generators_t.p[generator].clip(lower=0).sum())
        curtailed = max(available - actual, 0.0)
        return curtailed / 1e6

    def objective_cost(n: pypsa.Network) -> float | None:
        if n.objective is None:
            return None
        return float(n.objective) / 1e9

    base_objective = objective_cost(n_base)
    ind_objective = objective_cost(n_ind)
    base_cost = operational_cost(n_base)
    ind_cost = operational_cost(n_ind)
    base_curtail = curtailment_twh(n_base) if comparable else None
    ind_curtail = curtailment_twh(n_ind) if comparable else None

    if base_objective is not None:
        print(f"[Phase 5] Baseline total objective cost  : EUR {base_objective:.3f} billion")
    if ind_objective is not None:
        print(f"[Phase 5] Industrial total objective cost: EUR {ind_objective:.3f} billion")
    print(f"[Phase 5] Baseline operational dispatch cost : EUR {base_cost:.3f} billion")
    print(f"[Phase 5] Industrial operational dispatch cost: EUR {ind_cost:.3f} billion")
    if comparable and base_curtail is not None and ind_curtail is not None:
        print(f"[Phase 5] Baseline VRE curtailment          : {base_curtail:.2f} TWh")
        print(f"[Phase 5] Industrial VRE curtailment        : {ind_curtail:.2f} TWh")
    else:
        print("[Phase 5] Direct curtailment comparison skipped because the solved networks are not comparable.")

    fig, axis = plt.subplots(figsize=(9, 5.5))
    use_objective_cost = max(abs(base_cost), abs(ind_cost)) < 1e-9 and base_objective is not None and ind_objective is not None

    if comparable and base_curtail is not None and ind_curtail is not None:
        categories = [
            "Total objective (B EUR)" if use_objective_cost else "Operational cost (B EUR)",
            "VRE curtailment (TWh)",
        ]
        base_values = [base_objective if use_objective_cost else base_cost, base_curtail]
        ind_values = [ind_objective if use_objective_cost else ind_cost, ind_curtail]
    else:
        categories = ["Total objective (B EUR)" if use_objective_cost else "Operational cost (B EUR)"]
        base_values = [base_objective if use_objective_cost else base_cost]
        ind_values = [ind_objective if use_objective_cost else ind_cost]

    x = np.arange(len(categories))
    width = 0.35

    axis.bar(x - width / 2, base_values, width, label="Baseline", color="#8b0000")
    axis.bar(x + width / 2, ind_values, width, label="Industrial", color="#00aa00")
    title = "System benefits of endogenous industrial scheduling"
    if not comparable:
        title += " (structure mismatch detected)"
    axis.set_title(title)
    axis.set_xticks(x)
    axis.set_xticklabels(categories)
    axis.grid(axis="y", linestyle="--", alpha=0.6)
    axis.legend(loc="upper right")

    for offset, values in [(-width / 2, base_values), (width / 2, ind_values)]:
        for idx, value in enumerate(values):
            axis.text(idx + offset, value + 0.05 * abs(value) + 0.01, f"{value:.2f}", ha="center", va="bottom")

    if not comparable:
        axis.text(
            0.02,
            0.02,
            "Warning: baseline and industrial solved networks differ in topology or component counts.\nRefresh both solved .nc files from the same pipeline run before using this comparison quantitatively.",
            transform=axis.transAxes,
            fontsize=8.5,
            va="bottom",
            ha="left",
            bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "#666666"},
        )

    plt.tight_layout()
    fig.savefig(COST_PLOT_PNG, dpi=300)
    plt.close(fig)
    print(f"[Phase 5] Summary plot saved -> {COST_PLOT_PNG.name}")


def run_phase5() -> None:
    print("\n" + "=" * 60)
    print("  PHASE 5 - Final analysis and plots")
    print("=" * 60)
    plot_capacity_factors()
    compare_model_runs()


if __name__ == "__main__":
    run_phase5()
