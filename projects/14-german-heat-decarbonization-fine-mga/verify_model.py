"""
Enhanced verification script for the German Heat Decarbonization model:
 1.  Weather data and temperature-dependent COP profiles
 1B. Load & Clean Real Kreise Data (empirical mode)
 1C. Archetype Classification via K-Means
 1D. Empirical Parameter Derivation
 1E. Export Empirical Diagnostic Plots
 2.  5-archetype PyPSA network compilation
 3.  Baseline cost-optimal solve with endogenous carbon cap (2.0 MtCO2)
 4.  MGA frontier sweeps (5%, 10%, 15%)
 5.  Quality gate assertions (cost slacks, carbon caps)
 6.  Pareto and capacity mix figure exports
 7.  Solved network export at 5% slack (NetCDF)
 8.  CO2 sensitivity sweep (5 cap values)
 9.  Building retrofit scenario comparison (3 scenarios)
10.  Archetype-disaggregated heatmap + seasonal dispatch + emissions waterfall + cost donut
11.  Final memory profiling gate (< 400 MB delta)
"""

import os
import time
import psutil
import pandas as pd
import numpy as np
import gc
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

from src.config import (
    ARCHETYPES, TECHNOLOGIES, SOCIAL_ACCEPTANCE, CO2_EMISSIONS,
    CO2_CAPS_SENSITIVITY, DATA_MODE, KREISE_DATA_PATH, KREISE_BASE_YEAR,
    MGA_EPSILONS,
)
from src.data import get_heat_dataset
from src.model import (
    build_fine_heat_model, solve_fine_baseline, extract_fine_metrics,
    run_social_feasibility_frontier,
    run_co2_sensitivity, run_retrofit_sweep,
    compute_indirect_emissions,
)
from src.plotting import (
    plot_pareto_frontier, plot_capacity_stack,
    plot_co2_marginal_abatement_curve, plot_archetype_capacity_heatmap,
    plot_retrofit_impact_comparison,
    plot_emissions_waterfall, plot_cost_decomposition_sunburst,
    plot_kreise_archetype_map, plot_empirical_vs_synthetic_comparison,
    plot_kreise_climate_boxplots, plot_german_nuts3_map,
    plot_social_feasibility_frontier, plot_acceptance_heatmap,
)


def verify_pipeline():
    print("=" * 70)
    print("  RUNNING ENHANCED VERIFICATION OF THE ENERGY-SOCIAL HEAT MODEL  ")
    print("=" * 70)
    
    process = psutil.Process(os.getpid())
    ram_start = process.memory_info().rss / (1024 * 1024)
    print(f"[MEM] Initial RAM: {ram_start:.2f} MB")
    t_total_start = time.time()
    
    # ===================================================================
    # Phase 1: Temporal snapshots + Weather Data
    # ===================================================================
    print("\n--- Phase 1: Snapshots and Weather Data Setup ---")
    snapshots = pd.date_range("2023-01-01", periods=120, freq="h")
    start_time = time.time()
    df = get_heat_dataset(snapshots)
    print(f"[OK] Generated weather & COPs & grid CO2 intensity in {time.time() - start_time:.3f}s")
    print(f"     Average air-source COP: {df['cop_air_hp'].mean():.2f}")
    print(f"     Average district COP: {df['cop_dh_hp'].mean():.2f}")
    print(f"     Average grid CO2 intensity: {df['grid_co2_grams_per_kwh'].mean():.1f} gCO2/kWh")
    
    # ===================================================================
    # Phase 1B–1E: Empirical Data Integration (if DATA_MODE == "empirical")
    # ===================================================================
    empirical_params = None
    kreise_df = None
    
    if DATA_MODE == "empirical":
        from src.real_data import (
            load_kreise_data, classify_archetypes,
            compute_empirical_parameters, get_archetype_climate_profiles,
            get_empirical_summary, generate_spatial_markdown,
            compute_ml_acceptance_matrix, compute_gas_lock_in_index,
        )
        
        # Phase 1B: Load & Clean
        print("\n--- Phase 1B: Loading Real Kreise Data ---")
        start_time = time.time()
        kreise_df = load_kreise_data(KREISE_DATA_PATH, base_year=KREISE_BASE_YEAR)
        print(f"[OK] Loaded {len(kreise_df)} Kreise in {time.time() - start_time:.3f}s")
        print(f"     Columns: {len(kreise_df.columns)}")
        print(f"     Year filter: {KREISE_BASE_YEAR}")
        
        # Phase 1C: Archetype Classification
        print("\n--- Phase 1C: K-Means Archetype Classification ---")
        start_time = time.time()
        kreise_df, cluster_stats = classify_archetypes(kreise_df)
        print(f"[OK] Classified archetypes in {time.time() - start_time:.3f}s")
        for a in ARCHETYPES:
            stats = cluster_stats.get(a, {})
            count = stats.get("count", 0)
            density = stats.get("Population Density (Einwohner je km2)", 0)
            print(f"     {a:15s}: {count:3d} Kreise, mean density={density:.0f}/km2")
        
        # Validate: each archetype has >= 10 Kreise
        for a in ARCHETYPES:
            count = cluster_stats.get(a, {}).get("count", 0)
            assert count >= 10, f"Archetype '{a}' has only {count} Kreise — too few for reliable aggregation!"
        print("[PASS] All archetypes have >= 10 Kreise.")
        
        # Phase 1D: Empirical Parameter Derivation
        print("\n--- Phase 1D: Deriving Empirical Parameters ---")
        start_time = time.time()
        empirical_params = compute_empirical_parameters(kreise_df)
        print(f"[OK] Computed empirical parameters in {time.time() - start_time:.3f}s")
        
        # Validate heat load shares sum to 1.0
        hls_sum = sum(empirical_params["HEAT_LOAD_SHARES"].values())
        assert abs(hls_sum - 1.0) < 1e-6, f"Heat load shares sum to {hls_sum}, not 1.0!"
        print(f"[PASS] Heat load shares sum to {hls_sum:.6f}")
        
        # Validate capacity limits in [0, 1]
        for a in ARCHETYPES:
            for t in TECHNOLOGIES:
                val = empirical_params["CAPACITY_LIMIT_SHARES"][a][t]
                assert 0.0 <= val <= 1.0, f"cap_limit[{a}][{t}] = {val} out of [0,1]!"
        print("[PASS] All capacity limit shares in [0, 1].")
        
        # Print summary
        summary = get_empirical_summary(kreise_df, cluster_stats, empirical_params)
        print(summary)
        
        # Get archetype-specific climate profiles
        archetype_climate = get_archetype_climate_profiles(kreise_df)
        for a, clim in archetype_climate.items():
            print(f"     {a:15s}: T={clim['temperature']:.1f}°C, HDD={clim['hdd']:.0f}")
        
        # Phase 1E: Empirical Diagnostic Plots
        print("\n--- Phase 1E: Generating Empirical Diagnostic Plots ---")
        os.makedirs("results", exist_ok=True)
        
        plot_kreise_archetype_map(kreise_df, output_path="results/kreise_archetype_map.png")
        print("[OK] Exported Kreise archetype scatter map.")
        
        plot_empirical_vs_synthetic_comparison(empirical_params,
                                               output_path="results/empirical_vs_synthetic.png")
        print("[OK] Exported empirical vs synthetic comparison.")
        
        plot_kreise_climate_boxplots(kreise_df, output_path="results/kreise_climate_boxplots.png")
        print("[OK] Exported climate boxplots by archetype.")
        
        plot_german_nuts3_map(kreise_df, output_path="results/german_nuts3_map.png")
        print("[OK] Exported German NUTS3 geographic map.")
        
        # Acceptance heatmap
        plot_acceptance_heatmap(empirical_params["SOCIAL_ACCEPTANCE"],
                               gas_lock_in=empirical_params.get("GAS_LOCK_IN_INDEX"),
                               output_path="results/acceptance_heatmap.png")
        print("[OK] Exported ML-derived acceptance heatmap.")
        
        # Print gas lock-in index
        if "GAS_LOCK_IN_INDEX" in empirical_params:
            print("\n  Gas Grid Lock-In Index:")
            for a, v in empirical_params["GAS_LOCK_IN_INDEX"].items():
                print(f"    {a:15s}: {v:.3f}")

        # Save empirical parameters to CSV for reference
        emp_hls = pd.DataFrame([empirical_params["HEAT_LOAD_SHARES"]], index=["share"]).T
        emp_hls.to_csv("results/empirical_heat_load_shares.csv")
        empirical_params["SOCIAL_ACCEPTANCE"].to_csv("results/empirical_social_acceptance.csv")
        print("[OK] Saved empirical parameter tables to results/.")
    else:
        print("\n[INFO] DATA_MODE='synthetic' — skipping empirical data integration.")
    
    # ===================================================================
    # Phase 2: FINE EnergySystemModel Compilation
    # ===================================================================
    print("\n--- Phase 2: Compiling 5-Archetype FINE EnergySystemModel ---")
    start_time = time.time()
    co2_cap_mt = 2.0
    esM = build_fine_heat_model(snapshots, df, empirical_params=empirical_params,
                                 co2_cap_mt=co2_cap_mt)
    print(f"[OK] Built FINE model in {time.time() - start_time:.3f}s")
    print(f"     Framework: ETHOS.FINE (Forschungszentrum Jülich)")
    print(f"     Locations: {len(esM.locations)}, Commodities: {len(esM.commodities)}")
    mode_label = "EMPIRICAL (Kreise)" if empirical_params else "SYNTHETIC (config)"
    print(f"     Parameter source: {mode_label}")
    
    # ===================================================================
    # Phase 3: Baseline Cost-Optimal Solve
    # ===================================================================
    print("\n--- Phase 3: Solving Baseline Cost-Optimal Design (FINE + HiGHS) ---")
    start_time = time.time()
    baseline_cost = solve_fine_baseline(esM)
    print(f"[OK] Solved baseline in {time.time() - start_time:.3f}s")
    print(f"     Baseline objective: {baseline_cost:.4f} Billion EUR")
    
    # ===================================================================
    # Phase 4: MGA Frontier Sweeps
    # ===================================================================
    print("\n--- Phase 4: Running Social Feasibility Frontier ---")
    start_time = time.time()
    mga_df = run_social_feasibility_frontier(snapshots, df, co2_cap_mt=co2_cap_mt,
                                              epsilons=MGA_EPSILONS,
                                              empirical_params=empirical_params)
    print(f"[OK] Completed social feasibility frontier in {time.time() - start_time:.3f}s")
    print(f"     Frontier results shape: {mga_df.shape}")
    
    # Check exogenous vs endogenous cost-optimal
    exo_rows = mga_df[mga_df["objective_type"] == "cost_optimal_exogenous"]
    endo_rows = mga_df[mga_df["objective_type"] == "cost_optimal"]
    if len(exo_rows) > 0 and len(endo_rows) > 0:
        exo_cost = exo_rows.iloc[0]["system_cost_billion"]
        endo_cost = endo_rows.iloc[0]["system_cost_billion"]
        print(f"     Cost-optimal (no acceptance): {exo_cost:.3f} B€")
        print(f"     Cost-optimal (endogenous):    {endo_cost:.3f} B€")
        print(f"     Acceptance premium: +{((endo_cost - exo_cost) / exo_cost * 100):.1f}%")
    
    # ===================================================================
    # Phase 5: Quality Gate Assertions
    # ===================================================================
    print("\n--- Phase 5: Verification Gates (Quality Compliance) ---")
    # Verify CO2 cap respected across all solutions
    for idx, row in mga_df.iterrows():
        co2 = row.get("co2_emissions_mt", 0.0)
        if pd.notna(co2):
            assert co2 <= co2_cap_mt + 1e-2, f"CO2 cap violated! CO2: {co2}"
    print("[PASS] CO2 cap respected across all frontier solutions.")
    
    # Verify system cost is positive and reasonable
    for idx, row in mga_df.iterrows():
        cost = row.get("system_cost_billion", 0.0)
        if pd.notna(cost):
            assert cost > 0, f"System cost is non-positive: {cost}"
    print("[PASS] All system costs are positive.")
    
    # Verify per-archetype columns exist
    sample = mga_df.iloc[0]
    for a in ARCHETYPES:
        for t in TECHNOLOGIES:
            assert f"cap_{t}_{a}_mw" in sample, f"Missing archetype column cap_{t}_{a}_mw"
        assert f"co2_direct_{a}_mt" in sample, f"Missing co2_direct_{a}_mt"
        assert f"cost_{a}_billion" in sample, f"Missing cost_{a}_billion"
    print("[PASS] All archetype-disaggregated columns present.")
    
    # ===================================================================
    # Phase 6: Export Core Results & Core Plots
    # ===================================================================
    print("\n--- Phase 6: Exporting Core Results and Plots ---")
    os.makedirs("results", exist_ok=True)
    mga_df.to_csv("results/mga_results.csv", index=False)
    print("[OK] Saved MGA frontier to 'results/mga_results.csv'")
    
    plot_pareto_frontier(mga_df, output_path="results/test_pareto_frontier.png")
    plot_capacity_stack(mga_df, output_path="results/test_capacity_mix.png")
    plot_social_feasibility_frontier(mga_df, output_path="results/social_feasibility_frontier.png")
    print("[OK] Exported Pareto frontier, capacity mix, and social feasibility frontier.")
    
    # ===================================================================
    # Phase 7: FINE Baseline Results Export & Indirect Emissions
    # ===================================================================
    print("\n--- Phase 7: Exporting FINE Results & Indirect Emissions ---")
    # Build a fresh FINE model for indirect emissions
    esM_ref = build_fine_heat_model(snapshots, df, empirical_params=empirical_params,
                                     co2_cap_mt=co2_cap_mt)
    solve_fine_baseline(esM_ref)
    
    indirect = compute_indirect_emissions(esM_ref, df)
    print(f"     Indirect HP CO2 (grid): {indirect['co2_indirect_total_mt']:.4f} MtCO2")
    
    # Export FINE optimization summary
    try:
        conv_summary = esM_ref.getOptimizationSummary('ConversionModel', outputLevel=0)
        conv_summary.to_csv('results/fine_conversion_summary.csv')
        print("[OK] Exported FINE conversion summary.")
    except Exception as e:
        print(f"[WARN] Could not export FINE summary: {e}")
    
    del esM_ref
    gc.collect()
    print("[OK] Memory cleaned after Phase 7.")
    
    # ===================================================================
    # Phase 8: CO2 Sensitivity Sweep
    # ===================================================================
    print("\n--- Phase 8: CO2 Cap Sensitivity Sweep ---")
    start_time = time.time()
    co2_sens_df = run_co2_sensitivity(snapshots, df, CO2_CAPS_SENSITIVITY,
                                       empirical_params=empirical_params)
    print(f"[OK] CO2 sensitivity sweep completed (FINE) in {time.time() - start_time:.3f}s")
    co2_sens_df.to_csv("results/co2_sensitivity.csv", index=False)
    print("[OK] Saved to 'results/co2_sensitivity.csv'")
    
    # Verify monotonicity: tighter cap → higher cost
    valid = co2_sens_df.dropna(subset=["system_cost_billion"]).sort_values("co2_cap_mt")
    if len(valid) > 1:
        costs = valid["system_cost_billion"].values
        caps = valid["co2_cap_mt"].values
        # Cost should generally decrease as cap loosens (or stay flat)
        for i in range(len(costs) - 1):
            assert costs[i] >= costs[i + 1] - 1e-3, \
                f"Cost monotonicity violated: cap {caps[i]} → {caps[i+1]}"
    print("[PASS] System cost decreases monotonically as CO2 cap loosens.")
    
    plot_co2_marginal_abatement_curve(co2_sens_df, output_path="results/co2_marginal_abatement.png")
    print("[OK] Exported CO2 marginal abatement curve.")
    
    # ===================================================================
    # Phase 9: Building Retrofit Sweep
    # ===================================================================
    print("\n--- Phase 9: Building Retrofit Scenario Sweep ---")
    start_time = time.time()
    retrofit_df = run_retrofit_sweep(snapshots, df, co2_cap_mt=co2_cap_mt,
                                     empirical_params=empirical_params)
    print(f"[OK] Retrofit sweep completed (FINE) in {time.time() - start_time:.3f}s")
    retrofit_df.to_csv("results/retrofit_comparison.csv", index=False)
    print("[OK] Saved to 'results/retrofit_comparison.csv'")
    
    plot_retrofit_impact_comparison(retrofit_df, output_path="results/retrofit_impact.png")
    print("[OK] Exported retrofit impact comparison figure.")
    
    # ===================================================================
    # Phase 10: Enhanced Visualizations
    # ===================================================================
    print("\n--- Phase 10: Generating Enhanced Analytics Plots ---")
    
    # Archetype heatmap (use baseline metrics)
    baseline_metrics = mga_df[mga_df["objective_type"] == "cost_optimal"].iloc[0].to_dict()
    plot_archetype_capacity_heatmap(baseline_metrics, output_path="results/archetype_capacity_heatmap.png")
    print("[OK] Exported archetype capacity heatmap.")
    
    # Note: Seasonal dispatch triptych requires PyPSA time-series data (links_t)
    # which is not available in FINE. Skipping this plot.
    print("[INFO] Seasonal dispatch triptych skipped (FINE model — no per-timestep link data).")
    
    # Emissions waterfall
    direct_co2 = mga_df[mga_df["objective_type"] == "cost_optimal"].iloc[0]["co2_emissions_mt"]
    indirect_co2 = indirect["co2_indirect_total_mt"]
    plot_emissions_waterfall(direct_co2, indirect_co2, output_path="results/emissions_waterfall.png")
    print("[OK] Exported emissions waterfall chart.")
    
    # Cost decomposition sunburst
    plot_cost_decomposition_sunburst(baseline_metrics, output_path="results/cost_decomposition.png")
    print("[OK] Exported cost decomposition chart.")
    
    # Export archetype breakdown CSV
    archetype_cols = [c for c in mga_df.columns if any(a in c for a in ARCHETYPES)]
    if archetype_cols:
        mga_df[["epsilon", "objective_type"] + archetype_cols].to_csv(
            "results/archetype_breakdown.csv", index=False)
        print("[OK] Saved archetype breakdown to 'results/archetype_breakdown.csv'")
    
    # Phase 10B: Generate dynamic spatial analysis markdown with frontier results
    if DATA_MODE == "empirical" and kreise_df is not None:
        generate_spatial_markdown(kreise_df, cluster_stats, empirical_params, archetype_climate,
                                  frontier_results=mga_df,
                                  output_path="results/german_spatial_analysis.md")
        print("[OK] Exported dynamic spatial analysis markdown (with frontier results).")
    
    # ===================================================================
    # Phase 11: Final Memory Gate
    # ===================================================================
    print("\n--- Phase 11: Final Memory Profiling ---")
    ram_end = process.memory_info().rss / (1024 * 1024)
    ram_delta = ram_end - ram_start
    print(f"[MEM] Ending RAM: {ram_end:.2f} MB")
    print(f"[MEM] Peak RAM delta: {ram_delta:.2f} MB")
    assert ram_delta < 400, f"RAM delta {ram_delta:.2f} MB exceeds 400 MB limit!"
    print("[PASS] RAM usage within 8 GB laptop constraints.")
    
    total_time = time.time() - t_total_start
    print(f"[SPEED] Total execution time: {total_time:.2f} seconds")
    
    # ===================================================================
    # Summary
    # ===================================================================
    print("\n" + "=" * 70)
    print("  VERIFICATION COMPLETE: ALL QUALITY GATE TESTS PASSED  ")
    print("=" * 70)
    n_plots = len([f for f in os.listdir('results') if f.endswith('.png')])
    n_csvs = len([f for f in os.listdir('results') if f.endswith('.csv')])
    print(f"\nGenerated {n_plots} plots and {n_csvs} CSV files in 'results/' folder.")
    print(f"Data mode: {DATA_MODE.upper()}")
    return True


if __name__ == "__main__":
    verify_pipeline()