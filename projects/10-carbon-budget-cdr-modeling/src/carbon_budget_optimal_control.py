import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from gekko import GEKKO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def build_model(
    initial_pollution: float = 400.0,
    initial_cdr_capacity: float = 100.0,
    carbon_budget: float = 1200.0,
    remote: bool = True,
) -> tuple[GEKKO, dict[str, object]]:
    model = GEKKO(remote=remote)
    model.time = np.linspace(0, 100, 101)

    # Economic parameters
    rho = 0.014
    sigma = 0.5
    alpha = 0.3
    delta = 0.05
    total_factor_productivity = 11.97

    # Energy costs
    fossil_cost = 0.05
    renewable_cost = 0.01
    nuclear_cost = 0.015

    # Climate parameters
    emissions_intensity = 0.005
    natural_decay = 0.003
    cdr_effectiveness = 0.05

    # CDR stock dynamics
    cdr_from_fossils = 0.02
    cdr_pollution_drag = 0.001
    cdr_renewable_crowding = 0.05
    cdr_nuclear_crowding = 0.05
    cdr_depreciation = 0.05

    consumption = model.MV(value=50, lb=1.0, ub=500, name="consumption")
    fossils = model.MV(value=10, lb=0.0, ub=100, name="fossils")
    renewables = model.MV(value=1, lb=0.0, ub=100, name="renewables")
    nuclear = model.MV(value=1, lb=0.0, ub=100, name="nuclear")
    for control in [consumption, fossils, renewables, nuclear]:
        control.STATUS = 1
        control.DCOST = 0

    capital = model.Var(value=200, lb=10, name="capital")
    pollution = model.Var(value=initial_pollution, lb=0, name="pollution")
    cdr_capacity = model.Var(value=initial_cdr_capacity, lb=0, name="cdr_capacity")

    total_energy = model.Intermediate(fossils + renewables + nuclear)
    production = model.Intermediate(
        total_factor_productivity * (capital**alpha) * (total_energy ** (1 - alpha))
    )

    model.Equation(
        capital.dt()
        == production
        - fossil_cost * fossils
        - renewable_cost * renewables
        - nuclear_cost * nuclear
        - consumption
        - delta * capital
    )
    model.Equation(
        pollution.dt()
        == emissions_intensity * fossils - natural_decay * pollution - cdr_effectiveness * cdr_capacity
    )
    model.Equation(
        cdr_capacity.dt()
        == cdr_from_fossils * fossils
        - cdr_pollution_drag * pollution
        - cdr_renewable_crowding * renewables
        - cdr_nuclear_crowding * nuclear
        - cdr_depreciation * cdr_capacity
    )
    model.Equation(pollution <= carbon_budget)

    utility = (consumption ** (1 - sigma) - 1) / (1 - sigma)
    discount_factor = model.Param(value=np.exp(-rho * model.time))
    accumulated_utility = model.Var(value=0, lb=-1e10, ub=1e10, name="accumulated_utility")
    model.Equation(accumulated_utility.dt() == utility * discount_factor)
    model.Maximize(accumulated_utility)

    model.options.IMODE = 6
    model.options.NODES = 3
    model.options.SOLVER = 3

    variables = {
        "consumption": consumption,
        "fossils": fossils,
        "renewables": renewables,
        "nuclear": nuclear,
        "capital": capital,
        "pollution": pollution,
        "cdr_capacity": cdr_capacity,
        "carbon_budget": carbon_budget,
    }
    return model, variables


def plot_solution(model: GEKKO, variables: dict[str, object], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "carbon_budget_optimal_control.png"

    plt.figure(figsize=(12, 10))

    plt.subplot(3, 2, 1)
    plt.plot(model.time, variables["capital"].value, label="Capital", color="steelblue")
    plt.ylabel("Capital")
    plt.grid(True)
    plt.legend()

    plt.subplot(3, 2, 2)
    plt.plot(model.time, variables["consumption"].value, label="Consumption", color="green")
    plt.ylabel("Consumption")
    plt.grid(True)
    plt.legend()

    plt.subplot(3, 2, 3)
    plt.plot(model.time, variables["pollution"].value, label="Pollution", color="firebrick")
    plt.plot(
        model.time,
        [variables["carbon_budget"]] * len(model.time),
        linestyle="--",
        color="black",
        label="Carbon budget",
    )
    plt.ylabel("GtC")
    plt.grid(True)
    plt.legend()

    plt.subplot(3, 2, 4)
    plt.plot(model.time, variables["cdr_capacity"].value, label="CDR capacity", color="purple")
    plt.ylabel("CDR capacity")
    plt.grid(True)
    plt.legend()

    plt.subplot(3, 1, 3)
    plt.plot(model.time, variables["fossils"].value, label="Fossils", color="black")
    plt.plot(model.time, variables["renewables"].value, label="Renewables", color="green")
    plt.plot(model.time, variables["nuclear"].value, label="Nuclear", color="orange")
    plt.ylabel("Energy units")
    plt.xlabel("Time (years)")
    plt.grid(True)
    plt.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solve the carbon-budget optimal control model.")
    parser.add_argument("--initial-pollution", type=float, default=400.0)
    parser.add_argument("--initial-cdr-capacity", type=float, default=100.0)
    parser.add_argument("--carbon-budget", type=float, default=1200.0)
    parser.add_argument(
        "--local-solver",
        action="store_true",
        help="Use a local GEKKO solver instead of the remote server.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model, variables = build_model(
        initial_pollution=args.initial_pollution,
        initial_cdr_capacity=args.initial_cdr_capacity,
        carbon_budget=args.carbon_budget,
        remote=not args.local_solver,
    )
    model.solve(disp=True)
    output_path = plot_solution(model, variables, OUTPUT_DIR)
    print(f"Saved plot: {output_path}")


if __name__ == "__main__":
    main()
