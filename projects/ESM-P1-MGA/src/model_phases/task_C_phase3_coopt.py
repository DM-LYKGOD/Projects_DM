"""
Phase 3: co-optimisation across 2025, 2035, 2045 with the improved
regional clinker-grinding-storage module.
"""

import sys
from pathlib import Path

import matplotlib

# matplotlib.use("Agg")  # Commented to allow inline display in notebook
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    ALPHA_BY_YEAR,
    ETS_PRICE_BY_YEAR,
    FIGURES_DIR,
    PHASE3_RESULTS_CSV,
    ENABLE_ENDOGENOUS_INVESTMENT,
    PHASE3_SCENARIO_YEARS,
    PROCESS_CO2_KG_T_DEFAULT,
    ENERGY_CO2_KG_T_DEFAULT,
    RES_MULTIPLIER_BY_YEAR,
)
from src.model_phases.task_A_phase1_baseline import (
    inject_actual_load,
    inject_capacity_factors,
    load_network,
)
from src.model_phases import task_B_phase2_industrial as industry


DISPATCH_COMPARISON_PNG = FIGURES_DIR / "scenario_comparison.png"


def _extract_metrics(n, year: int, renewable_multiplier: float) -> dict:
    params = industry.load_cement_parameters()
    clinker = n.model.variables["ClinkerProduction"].solution.to_pandas()
    grinding = n.model.variables["CementGrinding"].solution.to_pandas()
    storage = n.model.variables["ClinkerStorage"].solution.to_pandas()

    gen = n.generators_t.p
    gen_by_carrier = gen.T.groupby(n.generators.carrier).sum().T.sum() / 1e6
    load_twh = n.loads_t.p_set.sum().sum() / 1e6
    industrial_load_twh = -gen_by_carrier.get("industrial_demand", 0.0)
    direct_emissions_mt = (
        clinker.sum().sum()
        * (
            params.get("process_co2_kg_t", PROCESS_CO2_KG_T_DEFAULT)
            + params.get("energy_co2_kg_t", ENERGY_CO2_KG_T_DEFAULT)
        )
        / 1e9
    )

    return {
        "year": year,
        "status": "ok",
        "res_multiplier": renewable_multiplier,
        "alpha_kwh_t": ALPHA_BY_YEAR[year],
        "ets_eur_tco2": ETS_PRICE_BY_YEAR[year],
        "non_industrial_load_twh": float(load_twh),
        "industrial_load_twh": float(industrial_load_twh),
        "total_electricity_twh": float(load_twh + industrial_load_twh),
        "clinker_prod_mt": float(clinker.sum().sum() / 1e6),
        "cement_prod_mt": float(grinding.sum().sum() / 1e6),
        "max_storage_kt": float(storage.sum(axis=1).max() / 1e3),
        "mean_storage_kt": float(storage.sum(axis=1).mean() / 1e3),
        "solar_twh": float(gen_by_carrier.get("solar", 0.0)),
        "onwind_twh": float(gen_by_carrier.get("onwind", 0.0)),
        "offwind_twh": float(gen_by_carrier.get("offwind", 0.0)),
        "ocgt_twh": float(gen_by_carrier.get("OCGT", 0.0)),
        "lignite_twh": float(gen_by_carrier.get("lignite", 0.0)),
        "load_shedding_twh": float(gen_by_carrier.get("load_shedding", 0.0)),
        "direct_emissions_mtco2": float(direct_emissions_mt),
    }


def run_scenario(year: int, renewable_multiplier: float, weather_year: int | None = None) -> dict:
    print(
        f"\n[Phase 3] Setting up scenario {year} with RES x{renewable_multiplier:.1f}"
    )
    n = load_network(weather_year_override=weather_year) if weather_year is not None else load_network()
    inject_actual_load(n)
    inject_capacity_factors(n)
    industry.remove_exogenous_cement_load(n, year=year)
    plants = industry.load_regional_plants(n)
    industry.add_cement_dummy_generators(n, plants)

    if ENABLE_ENDOGENOUS_INVESTMENT:
        print(
            f"[Phase 3] Enabling endogenous capacity investment (extendable VRE & Storage) for scenario {year}..."
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
    else:
        for generator in n.generators.index:
            if n.generators.at[generator, "carrier"] in ["solar", "onwind", "offwind"]:
                n.generators.at[generator, "p_nom"] *= renewable_multiplier

    def _callback(n_inner, snapshots):
        return industry.add_endogenous_industry(n_inner, snapshots, year=year)

    n.sanitize()
    status, condition = n.optimize(
        solver_name="highs",
        solver_options={
            "solver": "ipm",
            "run_crossover": "on",
            "threads": 8,
            "user_bound_scale": -12,
        },
        extra_functionality=_callback,
    )
    if status != "ok":
        return {"year": year, "status": status, "condition": condition}
    metrics = _extract_metrics(n, year, renewable_multiplier)
    metrics["condition"] = condition
    return metrics


def run_phase3() -> None:
    print("\n" + "=" * 60)
    print("  PHASE 3 - Co-optimisation Pathway (2025-2045)")
    print("=" * 60)

    scenarios = [
        {"year": year, "res_mult": RES_MULTIPLIER_BY_YEAR.get(year, 1.0)}
        for year in PHASE3_SCENARIO_YEARS
    ]
    results = [run_scenario(item["year"], item["res_mult"]) for item in scenarios]
    df = pd.DataFrame(results).set_index("year")
    df.to_csv(PHASE3_RESULTS_CSV)

    print("\n[Phase 3] Scenario comparison")
    print(df.to_string())

    valid = df[df["status"] == "ok"]
    if valid.empty:
        return

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    axes[0].plot(
        valid.index,
        valid["industrial_load_twh"],
        marker="o",
        color="#003f5c",
        label="Industrial electricity",
    )
    axes[0].plot(
        valid.index,
        valid["max_storage_kt"],
        marker="s",
        color="#ffa600",
        label="Max clinker storage",
    )
    axes[0].set_ylabel("TWh / kt")
    axes[0].legend()
    axes[0].grid(alpha=0.3, linestyle="--")

    axes[1].bar(
        valid.index - 1.5, valid["solar_twh"], width=3, color="#f6d55c", label="Solar"
    )
    axes[1].bar(
        valid.index - 1.5,
        valid["onwind_twh"],
        width=3,
        bottom=valid["solar_twh"],
        color="#3caea3",
        label="Onshore wind",
    )
    axes[1].bar(
        valid.index - 1.5,
        valid["offwind_twh"],
        width=3,
        bottom=valid["solar_twh"] + valid["onwind_twh"],
        color="#20639b",
        label="Offshore wind",
    )
    axes[1].plot(
        valid.index,
        valid["direct_emissions_mtco2"],
        color="#bc5090",
        marker="D",
        label="Direct ETS emissions",
    )
    axes[1].set_ylabel("TWh / MtCO2")
    axes[1].set_xlabel("Scenario year")
    axes[1].grid(alpha=0.3, linestyle="--")
    axes[1].legend()

    plt.tight_layout()
    fig.savefig(DISPATCH_COMPARISON_PNG, dpi=300)
    plt.close(fig)
    print(f"[Phase 3] Saved summary CSV  -> {PHASE3_RESULTS_CSV}")
    print(f"[Phase 3] Saved comparison   -> {DISPATCH_COMPARISON_PNG}")


if __name__ == "__main__":
    run_phase3()
