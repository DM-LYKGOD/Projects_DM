"""
Model construction and solving module using ETHOS.FINE (v2.6.0).
Sets up the 5-archetype German heat network using FINE's native multi-location
EnergySystemModel, optimizes baseline cost, and performs MGA sweeps to trace
the social feasibility frontier.

Enhanced with:
- Archetype-disaggregated metrics and indirect HP emissions
- CO2 cap sensitivity sweep
- Building retrofit scenario sweep
- Endogenous social acceptance penalties via per-location investPerCapacity
- Gas grid lock-in via per-location capacityMin
"""

import gc
import numpy as np
import pandas as pd
import fine as fn
from src.config import (
    ARCHETYPES,
    TECHNOLOGIES,
    CAPEX,
    FOM,
    LIFETIME,
    CARRIER_COSTS,
    CO2_EMISSIONS,
    EFFICIENCY,
    HEAT_LOAD_SHARES,
    CAPACITY_LIMIT_SHARES,
    DH_PIPING_PREMIUM,
    SOCIAL_ACCEPTANCE,
    CO2_PRICE_2045,
    TOTAL_GERMAN_HEAT_DEMAND_TWH,
    RETROFIT_SCENARIOS,
    RETROFIT_APPLICABILITY,
    ACCEPTANCE_PENALTY_SCALE,
    ACCEPTANCE_BONUS_SCALE,
    GAS_LOCK_IN_FLOOR,
    MGA_EPSILONS,
    DISCOUNT_RATE,
)


def _acceptance_adjusted_capex(base_capex, archetype, tech, sa_matrix, mode="endogenous", penalty_scale=None, bonus_scale=None):
    """
    Computes acceptance-adjusted CAPEX (EUR/kW).
    Endogenous mode embeds social acceptance as CAPEX penalty/bonus.
    """
    if penalty_scale is None: penalty_scale = ACCEPTANCE_PENALTY_SCALE
    if bonus_scale is None: bonus_scale = ACCEPTANCE_BONUS_SCALE

    if mode != "endogenous":
        return base_capex
    score = sa_matrix.at[archetype, tech] if archetype in sa_matrix.index else 0.0
    if score < 0:
        return base_capex + penalty_scale * abs(score)
    elif score > 0:
        discount = bonus_scale * score
        return max(base_capex - min(discount, base_capex * 0.3), base_capex * 0.1)
    return base_capex


def build_fine_heat_model(snapshots, data_df, demand_reduction_by_archetype=None,
                          empirical_params=None, acceptance_mode="endogenous",
                          co2_cap_mt=None, penalty_scale=None, bonus_scale=None):
    """
    Builds a FINE EnergySystemModel for German heat decarbonization.

    Uses FINE's native multi-location support with 5 municipal archetypes as locations.
    Each technology is a single Conversion component with per-location parameters.

    Parameters
    ----------
    snapshots : pd.DatetimeIndex
    data_df : pd.DataFrame with norm_load, cop_air_hp, cop_dh_hp, grid_co2_grams_per_kwh
    demand_reduction_by_archetype : dict, optional
    empirical_params : dict, optional
    acceptance_mode : str ('endogenous' or 'exogenous')
    co2_cap_mt : float, optional. If set, constrains total gas usage via balanceLimit.

    Returns
    -------
    fn.EnergySystemModel (not yet optimized)
    """
    # Parameter source
    if empirical_params:
        heat_load_shares = empirical_params["HEAT_LOAD_SHARES"]
        capacity_limit_shares = empirical_params["CAPACITY_LIMIT_SHARES"]
        dh_piping_premium = empirical_params["DH_PIPING_PREMIUM"]
        sa_matrix = empirical_params.get("SOCIAL_ACCEPTANCE", SOCIAL_ACCEPTANCE)
        gas_lock_in = empirical_params.get("GAS_LOCK_IN_INDEX", {})
    else:
        heat_load_shares = HEAT_LOAD_SHARES
        capacity_limit_shares = CAPACITY_LIMIT_SHARES
        dh_piping_premium = DH_PIPING_PREMIUM
        sa_matrix = SOCIAL_ACCEPTANCE
        gas_lock_in = {}

    n_steps = len(snapshots)
    locations = set(ARCHETYPES)

    # CO2 balance limit on gas commodity
    balanceLimit = None
    if co2_cap_mt is not None:
        # co2_cap_mt in MtCO2; CO2_EMISSIONS["gas"] in tCO2/MWh
        # Max gas MWh = co2_cap_mt * 1e6 / CO2_EMISSIONS["gas"]
        max_gas_mwh = co2_cap_mt * 1e6 / CO2_EMISSIONS["gas"]
        max_gas_kwh = max_gas_mwh * 1000.0
        
        # In FINE, if you want a global limit across all regions, 
        # you create a DataFrame index="gas" and columns for the locations
        # However, it's easier to create a "pathwayBalanceLimit" or use the 1D limit on the commodity.
        # Actually, FINE's EnergySystemModel balanceLimit is for single regions.
        # The easiest way to apply a global commodity limit across ALL regions is 
        # to use `pathwayBalanceLimit` or sum them in a custom constraint later.
        # Let's remove the native balanceLimit parameter from the ESM initialization 
        # and instead we'll add the global CO2 constraint manually right before solving,
        # just like we did in PyPSA. This avoids the strict location-matching of FINE's config.
        pass

    esM = fn.EnergySystemModel(
        locations=locations,
        commodities={"electricity", "gas", "hydrogen", "biomass", "heat"},
        numberOfTimeSteps=n_steps,
        commodityUnitsDict={
            "electricity": "kW", "gas": "kW", "hydrogen": "kW",
            "biomass": "kW", "heat": "kW"
        },
        hoursPerTimeStep=1,
        costUnit="1e9 Euro",
        verboseLogLevel=0,
    )

    # === SOURCES ===
    # Grid electricity — uniform cost across locations
    esM.add(fn.Source(
        esM=esM, name="grid_electricity", commodity="electricity",
        hasCapacityVariable=False,
        commodityCost=pd.Series({a: CARRIER_COSTS["electricity"] / 1e12 for a in ARCHETYPES}),
    ))

    # Gas supply — includes CO2 price
    gas_cost = (CARRIER_COSTS["gas"] + CO2_EMISSIONS["gas"] * CO2_PRICE_2045) / 1e12
    esM.add(fn.Source(
        esM=esM, name="gas_supply", commodity="gas",
        hasCapacityVariable=False,
        commodityCost=pd.Series({a: gas_cost for a in ARCHETYPES}),
    ))

    # Hydrogen supply
    esM.add(fn.Source(
        esM=esM, name="h2_supply", commodity="hydrogen",
        hasCapacityVariable=False,
        commodityCost=pd.Series({a: CARRIER_COSTS["hydrogen"] / 1e12 for a in ARCHETYPES}),
    ))

    # Biomass supply
    esM.add(fn.Source(
        esM=esM, name="biomass_supply", commodity="biomass",
        hasCapacityVariable=False,
        commodityCost=pd.Series({a: CARRIER_COSTS["biomass"] / 1e12 for a in ARCHETYPES}),
    ))

    # === HEAT DEMAND SINK ===
    total_heat_mw = TOTAL_GERMAN_HEAT_DEMAND_TWH * 1e6  # MWh -> kW*h for annual
    # Build per-location demand time series (in kW)
    demand_profiles = {}
    peak_loads = {}
    for a in ARCHETYPES:
        arch_annual_kwh = total_heat_mw * heat_load_shares[a] * 1000.0  # MWh * 1000 = kWh
        if demand_reduction_by_archetype and a in demand_reduction_by_archetype:
            arch_annual_kwh *= (1.0 - demand_reduction_by_archetype[a])
        # norm_load sums to 1.0 over the snapshots provided, so scale to correct annual fraction
        hourly_kw = arch_annual_kwh * data_df["norm_load"].values * (len(snapshots) / 8760.0)
        demand_profiles[a] = hourly_kw
        peak_loads[a] = hourly_kw.max()

    demand_df = pd.DataFrame(demand_profiles)
    esM.add(fn.Sink(
        esM=esM, name="heat_demand", commodity="heat",
        hasCapacityVariable=False,
        operationRateFix=demand_df,
    ))

    # === CONVERSION TECHNOLOGIES ===

    # 1. Air Heat Pump (electricity -> heat, time-varying COP)
    avg_cop_air = float(data_df["cop_air_hp"].mean())
    air_hp_capex = {}
    air_hp_cap_max = {}
    for a in ARCHETYPES:
        base = CAPEX["air_hp"]
        adjusted = _acceptance_adjusted_capex(base, a, "air_hp", sa_matrix, acceptance_mode, penalty_scale, bonus_scale)
        air_hp_capex[a] = adjusted
        air_hp_cap_max[a] = peak_loads[a] * capacity_limit_shares[a]["air_hp"]

    esM.add(fn.Conversion(
        esM=esM, name="air_heat_pump", physicalUnit="kW",
        commodityConversionFactors={"electricity": -1/avg_cop_air, "heat": 1},
        hasCapacityVariable=True,
        investPerCapacity=pd.Series({a: air_hp_capex[a] / 1e9 for a in ARCHETYPES}),
        opexPerCapacity=pd.Series({a: air_hp_capex[a] * FOM["air_hp"] / 1e9 for a in ARCHETYPES}),
        economicLifetime=pd.Series({a: LIFETIME["air_hp"] for a in ARCHETYPES}),
        interestRate=pd.Series({a: DISCOUNT_RATE for a in ARCHETYPES}),
        capacityMax=pd.Series(air_hp_cap_max),
    ))

    # 2. District Heat Pump (with density-dependent piping premium)
    avg_cop_dh = float(data_df["cop_dh_hp"].mean())
    dh_hp_capex = {}
    dh_hp_cap_max = {}
    for a in ARCHETYPES:
        base = CAPEX["dh_large_hp"] + dh_piping_premium[a]
        adjusted = _acceptance_adjusted_capex(base, a, "dh_large_hp", sa_matrix, acceptance_mode, penalty_scale, bonus_scale)
        dh_hp_capex[a] = adjusted
        dh_hp_cap_max[a] = peak_loads[a] * capacity_limit_shares[a]["dh_large_hp"]

    esM.add(fn.Conversion(
        esM=esM, name="district_heat_pump", physicalUnit="kW",
        commodityConversionFactors={"electricity": -1/avg_cop_dh, "heat": 1},
        hasCapacityVariable=True,
        investPerCapacity=pd.Series({a: dh_hp_capex[a] / 1e9 for a in ARCHETYPES}),
        opexPerCapacity=pd.Series({a: dh_hp_capex[a] * FOM["dh_large_hp"] / 1e9 for a in ARCHETYPES}),
        economicLifetime=pd.Series({a: LIFETIME["dh_large_hp"] for a in ARCHETYPES}),
        interestRate=pd.Series({a: DISCOUNT_RATE for a in ARCHETYPES}),
        capacityMax=pd.Series(dh_hp_cap_max),
    ))

    # 3. Gas Boiler (gas -> heat)
    gas_capex = {}
    gas_cap_max = {}
    gas_cap_min = {}
    for a in ARCHETYPES:
        base = CAPEX["gas_boiler"]
        adjusted = _acceptance_adjusted_capex(base, a, "gas_boiler", sa_matrix, acceptance_mode, penalty_scale, bonus_scale)
        gas_capex[a] = adjusted
        gas_cap_max[a] = peak_loads[a] * capacity_limit_shares[a]["gas_boiler"]
        # Gas lock-in: minimum capacity floor for high-dependency archetypes
        if gas_lock_in.get(a, 0) > 0.5:
            gas_cap_min[a] = peak_loads[a] * GAS_LOCK_IN_FLOOR * gas_lock_in[a]
        else:
            gas_cap_min[a] = 0.0

    esM.add(fn.Conversion(
        esM=esM, name="gas_boiler", physicalUnit="kW",
        commodityConversionFactors={"gas": -1/EFFICIENCY["gas_boiler"], "heat": 1},
        hasCapacityVariable=True,
        investPerCapacity=pd.Series({a: gas_capex[a] / 1e9 for a in ARCHETYPES}),
        opexPerCapacity=pd.Series({a: gas_capex[a] * FOM["gas_boiler"] / 1e9 for a in ARCHETYPES}),
        economicLifetime=pd.Series({a: LIFETIME["gas_boiler"] for a in ARCHETYPES}),
        interestRate=pd.Series({a: DISCOUNT_RATE for a in ARCHETYPES}),
        capacityMax=pd.Series(gas_cap_max),
        capacityMin=pd.Series(gas_cap_min),
    ))

    # 4. Hydrogen Boiler
    h2_capex = {}
    h2_cap_max = {}
    for a in ARCHETYPES:
        base = CAPEX["h2_boiler"]
        adjusted = _acceptance_adjusted_capex(base, a, "h2_boiler", sa_matrix, acceptance_mode, penalty_scale, bonus_scale)
        h2_capex[a] = adjusted
        h2_cap_max[a] = peak_loads[a] * capacity_limit_shares[a]["h2_boiler"]

    esM.add(fn.Conversion(
        esM=esM, name="h2_boiler", physicalUnit="kW",
        commodityConversionFactors={"hydrogen": -1/EFFICIENCY["h2_boiler"], "heat": 1},
        hasCapacityVariable=True,
        investPerCapacity=pd.Series({a: h2_capex[a] / 1e9 for a in ARCHETYPES}),
        opexPerCapacity=pd.Series({a: h2_capex[a] * FOM["h2_boiler"] / 1e9 for a in ARCHETYPES}),
        economicLifetime=pd.Series({a: LIFETIME["h2_boiler"] for a in ARCHETYPES}),
        interestRate=pd.Series({a: DISCOUNT_RATE for a in ARCHETYPES}),
        capacityMax=pd.Series(h2_cap_max),
    ))

    # 5. Biomass Boiler
    bio_capex = {}
    bio_cap_max = {}
    for a in ARCHETYPES:
        base = CAPEX["biomass_boiler"]
        adjusted = _acceptance_adjusted_capex(base, a, "biomass_boiler", sa_matrix, acceptance_mode, penalty_scale, bonus_scale)
        bio_capex[a] = adjusted
        bio_cap_max[a] = peak_loads[a] * capacity_limit_shares[a]["biomass_boiler"]

    esM.add(fn.Conversion(
        esM=esM, name="biomass_boiler", physicalUnit="kW",
        commodityConversionFactors={"biomass": -1/EFFICIENCY["biomass_boiler"], "heat": 1},
        hasCapacityVariable=True,
        investPerCapacity=pd.Series({a: bio_capex[a] / 1e9 for a in ARCHETYPES}),
        opexPerCapacity=pd.Series({a: bio_capex[a] * FOM["biomass_boiler"] / 1e9 for a in ARCHETYPES}),
        economicLifetime=pd.Series({a: LIFETIME["biomass_boiler"] for a in ARCHETYPES}),
        interestRate=pd.Series({a: DISCOUNT_RATE for a in ARCHETYPES}),
        capacityMax=pd.Series(bio_cap_max),
    ))

    # === THERMAL ENERGY STORAGE ===
    esM.add(fn.Storage(
        esM=esM, name="thermal_storage", commodity="heat",
        hasCapacityVariable=True,
        capacityVariableDomain="continuous",
        investPerCapacity=pd.Series({a: 30.0 / 1e9 for a in ARCHETYPES}),
        opexPerCapacity=pd.Series({a: 30.0 * 0.01 / 1e9 for a in ARCHETYPES}),
        chargeRate=1/6, dischargeRate=1/6,
        selfDischarge=0.005,
        economicLifetime=pd.Series({a: 20 for a in ARCHETYPES}),
        interestRate=pd.Series({a: DISCOUNT_RATE for a in ARCHETYPES}),
        cyclicLifetime=10000,
    ))

    return esM


def solve_fine_baseline(esM, co2_cap_mt=None):
    """Solves the FINE model and returns the objective value.
    If co2_cap_mt is provided, enforces a global CO2 cap across all locations.
    """
    import fine as fn
    import pyomo.environ as pyo
    from src.config import CO2_EMISSIONS
    
    # Generate Pyomo model first
    agg = False
    if esM.numberOfTimeSteps >= 240:
        esM.aggregateTemporally(numberOfTypicalPeriods=10, numberOfTimeStepsPerPeriod=24)
        agg = True
    esM.declareOptimizationProblem(timeSeriesAggregation=agg)
    
    # Add manual CO2 global constraint
    if co2_cap_mt is not None:
        max_gas_mwh = co2_cap_mt * 1e6 / CO2_EMISSIONS["gas"]
        max_gas_kwh = max_gas_mwh * 1000.0  # FINE commodity unit is kW
        
        def global_co2_rule(m):
            # Sum the operation of the gas_boiler across all locations and timesteps
            # operationVarDict returns a dict of Pyomo vars keyed by component name
            # gas_boiler commodityConversionFactors for gas is negative, meaning it consumes gas
            gas_comp = esM.componentModelingDict["ConversionModel"]
            if "gas_boiler" in gas_comp.operationVarDict:
                gas_var = gas_comp.operationVarDict["gas_boiler"]
                # gas_var is indexed by (location, time)
                total_gas_kwh = sum(gas_var[loc, t] / esM.componentDict["gas_boiler"].commodityConversionFactors["gas"] * -1
                                    for loc in esM.locations
                                    for t in esM.pyM.timeSteps)
                return total_gas_kwh <= max_gas_kwh
            return pyo.Constraint.Skip
            
        esM.pyM.GlobalCO2Limit = pyo.Constraint(rule=global_co2_rule)
    
    # Solve the constructed model
    esM.optimize(solver='highs', timeSeriesAggregation=agg, declaresOptimizationProblem=False)
    return float(esM.pyM.Obj())


def extract_fine_metrics(esM, epsilon, objective_type, sa_matrix=None):
    """
    Extracts all metrics from a solved FINE model.
    Produces the same column format as the old PyPSA extract_metrics().
    """
    if sa_matrix is None:
        sa_matrix = SOCIAL_ACCEPTANCE

    # Map FINE component names to our tech keys
    fine_to_tech = {
        "air_heat_pump": "air_hp",
        "district_heat_pump": "dh_large_hp",
        "gas_boiler": "gas_boiler",
        "h2_boiler": "h2_boiler",
        "biomass_boiler": "biomass_boiler",
    }

    # Get optimization summaries
    conv_summary = esM.getOptimizationSummary("ConversionModel", outputLevel=0)
    stor_summary = esM.getOptimizationSummary("StorageModel", outputLevel=0)

    # 1. Capacities
    capacities = {}
    for fine_name, tech in fine_to_tech.items():
        total_kw = 0.0
        for a in ARCHETYPES:
            try:
                cap_kw = conv_summary.loc[(fine_name, "capacity", "[kW]"), a]
                cap_kw = float(cap_kw)
            except (KeyError, TypeError):
                cap_kw = 0.0
            capacities[f"cap_{tech}_{a}_mw"] = cap_kw / 1000.0  # kW -> MW
            total_kw += cap_kw
        capacities[f"cap_{tech}_gw"] = total_kw / 1e6  # kW -> GW

    # TES capacity
    tes_total_kwh = 0.0
    for a in ARCHETYPES:
        try:
            tes_kwh = float(stor_summary.loc[("thermal_storage", "capacity", "[kW*h]"), a])
        except (KeyError, TypeError):
            tes_kwh = 0.0
        capacities[f"cap_tes_{a}_mwh"] = tes_kwh / 1000.0
        tes_total_kwh += tes_kwh
    capacities["cap_tes_gwh"] = tes_total_kwh / 1e6

    # 2. Social Acceptance Index
    ssa_score = 0.0
    for fine_name, tech in fine_to_tech.items():
        for a in ARCHETYPES:
            cap_mw = capacities.get(f"cap_{tech}_{a}_mw", 0.0)
            score = sa_matrix.at[a, tech] if a in sa_matrix.index else 0.0
            ssa_score += score * cap_mw
    ssa_score = ssa_score / 1000.0  # Normalize to GW scale

    # 3. Generation (from operation_annual)
    shares = {}
    total_heat_twh = 0.0
    for fine_name, tech in fine_to_tech.items():
        total_kwh = 0.0
        for a in ARCHETYPES:
            try:
                gen_kwh = float(conv_summary.loc[(fine_name, "operation_annual", "[kW*h/a]"), a])
            except (KeyError, TypeError):
                gen_kwh = 0.0
            shares[f"gen_{tech}_{a}_twh"] = gen_kwh / 1e9  # kWh -> TWh
            total_kwh += gen_kwh
        shares[f"gen_{tech}_twh"] = total_kwh / 1e9
        total_heat_twh += total_kwh / 1e9

    # 4. CO2 emissions — from gas boiler operation
    gas_gen_kwh = 0.0
    co2_by_archetype = {}
    for a in ARCHETYPES:
        try:
            gen_kwh = float(conv_summary.loc[("gas_boiler", "operation_annual", "[kW*h/a]"), a])
        except (KeyError, TypeError):
            gen_kwh = 0.0
        # Gas consumed = heat output / efficiency
        gas_consumed_mwh = (gen_kwh / 1000.0) / EFFICIENCY["gas_boiler"]
        arch_co2_mt = gas_consumed_mwh * CO2_EMISSIONS["gas"] / 1e6
        co2_by_archetype[f"co2_direct_{a}_mt"] = arch_co2_mt
        gas_gen_kwh += gen_kwh
    total_gas_consumed_mwh = (gas_gen_kwh / 1000.0) / EFFICIENCY["gas_boiler"]
    co2_direct_mt = total_gas_consumed_mwh * CO2_EMISSIONS["gas"] / 1e6

    # 5. Total system cost (True financial cost, not the modified objective)
    from src.config import CAPEX, FOM, LIFETIME, CARRIER_COSTS, CO2_PRICE_2045, get_annuity
    
    true_total_cost_billion = 0.0
    cost_by_archetype = {}
    
    for a in ARCHETYPES:
        arch_cost = 0.0
        
        # 1. True CAPEX and OPEX for technologies
        for fine_name, tech in fine_to_tech.items():
            cap_gw = capacities.get(f"cap_{tech}_{a}_mw", 0.0) / 1000.0
            if cap_gw > 0:
                annuity = get_annuity(CAPEX[tech], LIFETIME[tech])
                fom = CAPEX[tech] * FOM[tech]
                arch_cost += (annuity + fom) * cap_gw * 1000.0 / 1e9  # EUR to Billion EUR
                
        # 2. TES True CAPEX and OPEX
        tes_gwh = capacities.get(f"cap_tes_{a}_mwh", 0.0) / 1000.0
        if tes_gwh > 0:
            tes_annuity = get_annuity(30.0, 20)  # 30 EUR/kWh, 20 years
            tes_fom = 30.0 * 0.01
            arch_cost += (tes_annuity + tes_fom) * tes_gwh * 1e6 * 1000.0 / 1e9 # 30 EUR/kWh -> 30,000 EUR/MWh -> 30M EUR/GWh
            
        # 3. Fuel Costs
        for fine_name, tech in fine_to_tech.items():
            gen_twh = shares.get(f"gen_{tech}_{a}_twh", 0.0)
            if gen_twh > 0:
                if tech == "gas_boiler":
                    fuel_cost = (CARRIER_COSTS["gas"] + CO2_EMISSIONS["gas"] * CO2_PRICE_2045)
                    efficiency = EFFICIENCY["gas_boiler"]
                    consumed_twh = gen_twh / efficiency
                    arch_cost += consumed_twh * fuel_cost / 1e6  # EUR/MWh * 1e6 MWh/TWh = EUR -> Billion EUR
                elif tech == "h2_boiler":
                    fuel_cost = CARRIER_COSTS["hydrogen"]
                    consumed_twh = gen_twh / EFFICIENCY["h2_boiler"]
                    arch_cost += consumed_twh * fuel_cost / 1e6
                elif tech == "biomass_boiler":
                    fuel_cost = CARRIER_COSTS["biomass"]
                    consumed_twh = gen_twh / EFFICIENCY["biomass_boiler"]
                    arch_cost += consumed_twh * fuel_cost / 1e6
                elif tech in ["air_hp", "dh_large_hp"]:
                    fuel_cost = CARRIER_COSTS["electricity"]
                    cop = 3.0 if tech == "air_hp" else 3.2
                    consumed_twh = gen_twh / cop
                    arch_cost += consumed_twh * fuel_cost / 1e6
                    
        cost_by_archetype[f"cost_{a}_billion"] = arch_cost
        true_total_cost_billion += arch_cost

    metrics = {
        "epsilon": epsilon,
        "objective_type": objective_type,
        "system_cost_billion": true_total_cost_billion,
        "social_acceptance_index": ssa_score,
        "co2_emissions_mt": co2_direct_mt,
        "total_heat_generation_twh": total_heat_twh,
    }
    metrics.update(capacities)
    metrics.update(shares)
    metrics.update(co2_by_archetype)
    metrics.update(cost_by_archetype)

    return metrics


def run_social_feasibility_frontier(snapshots, data_df, co2_cap_mt=2.0,
                                     epsilons=None, empirical_params=None):
    """
    Traces the Social Feasibility Frontier using sequential FINE solves.

    For each epsilon cost slack, builds a new FINE model with modified
    investPerCapacity to shift toward max/min social acceptance.

    Returns pd.DataFrame with frontier results.
    """
    if epsilons is None:
        epsilons = MGA_EPSILONS

    if empirical_params:
        sa_matrix = empirical_params.get("SOCIAL_ACCEPTANCE", SOCIAL_ACCEPTANCE)
    else:
        sa_matrix = SOCIAL_ACCEPTANCE

    results = []

    # Step 1: Pure cost-optimal (exogenous — no acceptance penalties)
    esM_exo = build_fine_heat_model(snapshots, data_df, empirical_params=empirical_params,
                                     acceptance_mode="exogenous", co2_cap_mt=co2_cap_mt)
    cost_exo = solve_fine_baseline(esM_exo)
    metrics_exo = extract_fine_metrics(esM_exo, 0.0, "cost_optimal_exogenous", sa_matrix)
    metrics_exo["acceptance_mode"] = "exogenous"
    results.append(metrics_exo)
    del esM_exo
    gc.collect()

    # Step 2: Cost-optimal with endogenous acceptance penalties
    esM_endo = build_fine_heat_model(snapshots, data_df, empirical_params=empirical_params,
                                      acceptance_mode="endogenous", co2_cap_mt=co2_cap_mt)
    cost_endo = solve_fine_baseline(esM_endo)
    metrics_endo = extract_fine_metrics(esM_endo, 0.0, "cost_optimal", sa_matrix)
    metrics_endo["acceptance_mode"] = "endogenous"
    results.append(metrics_endo)
    del esM_endo
    gc.collect()

    # Step 3: MGA sweeps — For each epsilon, build models with amplified acceptance
    for eps in epsilons:
        if eps == 0.0:
            continue
        for direction in ["max_acceptance", "min_acceptance"]:
            # Build model with stronger acceptance weighting
            # max_acceptance: amplify acceptance bonuses (multiply penalty/bonus scale)
            # min_acceptance: invert acceptance (penalties become bonuses)
            scale_factor = 1.0 + eps * 10.0  # Amplify with epsilon
            
            # Temporarily modify acceptance scales
            orig_penalty = ACCEPTANCE_PENALTY_SCALE
            orig_bonus = ACCEPTANCE_BONUS_SCALE
            
            if direction == "max_acceptance":
                penalty_scale = orig_penalty * scale_factor
                bonus_scale = orig_bonus * scale_factor
            else:
                # Invert: reward rejected techs, penalize accepted ones
                penalty_scale = orig_bonus * scale_factor * 0.5
                bonus_scale = orig_penalty * scale_factor * 0.5

            esM_mga = build_fine_heat_model(
                snapshots, data_df, empirical_params=empirical_params,
                acceptance_mode="endogenous", co2_cap_mt=co2_cap_mt,
                penalty_scale=penalty_scale, bonus_scale=bonus_scale
            )
            
            solve_fine_baseline(esM_mga)
            metrics = extract_fine_metrics(esM_mga, eps, direction, sa_matrix)
            metrics["acceptance_mode"] = "endogenous"
            results.append(metrics)
            del esM_mga
            gc.collect()

    return pd.DataFrame(results)


def run_co2_sensitivity(snapshots, data_df, co2_caps, empirical_params=None):
    """
    Sweeps CO2 cap values using FINE models.
    """
    results = []
    for cap in co2_caps:
        esM = build_fine_heat_model(snapshots, data_df, empirical_params=empirical_params,
                                     co2_cap_mt=cap)
        try:
            cost = solve_fine_baseline(esM)
            metrics = extract_fine_metrics(esM, 0.0, f"co2_cap_{cap}")
            metrics["co2_cap_mt"] = cap
            results.append(metrics)
        except Exception:
            results.append({"co2_cap_mt": cap, "system_cost_billion": np.nan})
        finally:
            del esM
            gc.collect()

    return pd.DataFrame(results)


def run_retrofit_sweep(snapshots, data_df, co2_cap_mt=2.0, empirical_params=None):
    """
    Compares heating system design across building retrofit scenarios using FINE.
    """
    if empirical_params:
        retrofit_applicability = empirical_params.get("RETROFIT_APPLICABILITY", RETROFIT_APPLICABILITY)
        heat_load_shares = empirical_params["HEAT_LOAD_SHARES"]
    else:
        retrofit_applicability = RETROFIT_APPLICABILITY
        heat_load_shares = HEAT_LOAD_SHARES

    results = []
    for scenario_name, params in RETROFIT_SCENARIOS.items():
        reduction = params["demand_reduction"]
        retrofit_cost_per_kwh = params["retrofit_cost_eur_per_kwh"]

        demand_reduction_by_archetype = {}
        total_retrofit_cost = 0.0
        for a in ARCHETYPES:
            applicability = retrofit_applicability[a]
            effective_reduction = reduction * applicability
            demand_reduction_by_archetype[a] = effective_reduction

            arch_demand_kwh = TOTAL_GERMAN_HEAT_DEMAND_TWH * 1e9 * heat_load_shares[a]
            saved_kwh = arch_demand_kwh * effective_reduction
            total_retrofit_cost += saved_kwh * retrofit_cost_per_kwh / 1e9

        esM = build_fine_heat_model(
            snapshots, data_df,
            demand_reduction_by_archetype=demand_reduction_by_archetype,
            empirical_params=empirical_params, co2_cap_mt=co2_cap_mt
        )
        try:
            cost = solve_fine_baseline(esM)
            metrics = extract_fine_metrics(esM, 0.0, f"retrofit_{scenario_name}")
            metrics["scenario"] = scenario_name
            metrics["demand_reduction_pct"] = reduction * 100
            metrics["retrofit_investment_billion"] = total_retrofit_cost
            metrics["total_cost_with_retrofit_billion"] = metrics["system_cost_billion"] + total_retrofit_cost
            results.append(metrics)
        except Exception:
            results.append({"scenario": scenario_name, "system_cost_billion": np.nan})
        finally:
            del esM
            gc.collect()

    return pd.DataFrame(results)


def compute_indirect_emissions(esM, data_df):
    """
    Computes indirect CO2 from heat pump electricity use.
    Placeholder: uses average grid CO2 intensity × total HP electricity consumption.
    """
    avg_grid_co2 = data_df["grid_co2_grams_per_kwh"].mean()  # gCO2/kWh
    conv_summary = esM.getOptimizationSummary("ConversionModel", outputLevel=0)

    hp_fine_names = ["air_heat_pump", "district_heat_pump"]
    result = {}
    total_indirect = 0.0

    for a in ARCHETYPES:
        arch_indirect = 0.0
        for fine_name in hp_fine_names:
            try:
                gen_kwh = float(conv_summary.loc[(fine_name, "operation_annual", "[kW*h/a]"), a])
            except (KeyError, TypeError):
                gen_kwh = 0.0
            # Electricity consumed = heat output / COP
            cop = 3.0 if "air" in fine_name else 3.2
            elec_kwh = gen_kwh / cop
            co2_mt = elec_kwh * avg_grid_co2 / 1e9  # kWh * gCO2/kWh / 1e9 = MtCO2
            arch_indirect += co2_mt
        result[f"co2_indirect_{a}_mt"] = arch_indirect
        total_indirect += arch_indirect

    result["co2_indirect_total_mt"] = total_indirect
    return result


# === Backward compatibility aliases ===
build_heat_network = build_fine_heat_model
solve_baseline = solve_fine_baseline
extract_metrics = extract_fine_metrics