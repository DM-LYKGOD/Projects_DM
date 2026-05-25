import pandas as pd
from src.config import CAPEX, FOM, LIFETIME, CARRIER_COSTS, CO2_PRICE_2045, EFFICIENCY, CO2_EMISSIONS, ARCHETYPES, get_annuity

def recalc_cost(row):
    cost = 0.0
    for a in ARCHETYPES:
        for tech in ["air_hp", "dh_large_hp", "gas_boiler", "h2_boiler", "biomass_boiler"]:
            # CAPEX
            cap_gw = row.get(f"cap_{tech}_{a}_mw", 0.0) / 1000.0
            if cap_gw > 0:
                ann = get_annuity(CAPEX[tech], LIFETIME[tech])
                fom = CAPEX[tech] * FOM[tech]
                cost += (ann + fom) * cap_gw * 1e-3

            # OPEX
            gen_twh = row.get(f"gen_{tech}_{a}_twh", 0.0)
            if gen_twh > 0:
                if tech == "gas_boiler":
                    fc = CARRIER_COSTS["gas"] + CO2_EMISSIONS["gas"] * CO2_PRICE_2045
                    eff = EFFICIENCY["gas_boiler"]
                elif tech == "h2_boiler":
                    fc = CARRIER_COSTS["hydrogen"]
                    eff = EFFICIENCY["h2_boiler"]
                elif tech == "biomass_boiler":
                    fc = CARRIER_COSTS["biomass"]
                    eff = EFFICIENCY["biomass_boiler"]
                elif tech == "air_hp":
                    fc = CARRIER_COSTS["electricity"]
                    eff = 3.0
                elif tech == "dh_large_hp":
                    fc = CARRIER_COSTS["electricity"]
                    eff = 3.2
                
                cost += (gen_twh / eff) * fc * 1e-3
                
        # TES
        tes_mwh = row.get(f"cap_tes_{a}_mwh", 0.0)
        if tes_mwh > 0:
            tes_gwh = tes_mwh / 1000.0
            t_ann = get_annuity(30.0, 20)
            t_fom = 30.0 * 0.01
            cost += (t_ann + t_fom) * tes_gwh * 1e-3
            
    return cost

def fix_csv(path):
    df = pd.read_csv(path)
    df["system_cost_billion"] = df.apply(recalc_cost, axis=1)
    df.to_csv(path, index=False)
    return df

df_mga = fix_csv("results/mga_results.csv")
print("MGA true costs:")
print(df_mga[["epsilon", "objective_type", "system_cost_billion"]])

from src.plotting import plot_pareto_frontier, plot_capacity_stack, plot_co2_marginal_abatement_curve, plot_retrofit_impact_comparison

plot_pareto_frontier(df_mga, "results/social_feasibility_frontier.png")
plot_capacity_stack(df_mga, "results/test_capacity_mix.png")

df_co2 = fix_csv("results/co2_sensitivity.csv")
plot_co2_marginal_abatement_curve(df_co2, "results/co2_marginal_abatement.png")

print("Plots regenerated!")
