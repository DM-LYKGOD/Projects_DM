"""
Visualization module containing plotting routines for publication-ready figures:
1. Social Feasibility Frontier (Cost-Acceptance Pareto Curve)
2. Capacity & Generation Stacked Bar Charts across slacks
3. Hourly Dispatch Dynamics with Thermal Energy Storage (TES)
4. CO2 Marginal Abatement Cost Curve
5. Archetype-Technology Capacity Heatmap
6. Building Retrofit Impact Comparison
7. Seasonal Dispatch Triptych
8. Emissions Waterfall (Direct + Indirect)
9. Cost Decomposition Donut/Sunburst
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
import numpy as np
from src.config import ARCHETYPES, TECHNOLOGIES

# Configure modern premium styles
if "seaborn-v0_8-whitegrid" in plt.style.available:
    plt.style.use("seaborn-v0_8-whitegrid")
else:
    plt.style.use("default")

plt.rcParams["font.sans-serif"] = "Inter, Outfit, Helvetica, Arial"
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.edgecolor"] = "#cbd5e1"
plt.rcParams["axes.linewidth"] = 1.0
plt.rcParams["grid.color"] = "#f1f5f9"
plt.rcParams["grid.alpha"] = 1.0

# Curated, harmonious colors matching high aesthetics
TECH_COLORS = {
    "air_hp": "#3b82f6",        # Slate blue
    "dh_large_hp": "#8b5cf6",   # Deep violet
    "gas_boiler": "#ef4444",    # Muted coral/red
    "h2_boiler": "#10b981",     # Soft emerald
    "biomass_boiler": "#b45309",# Warm brown/amber
    "tes": "#f59e0b",            # Amber/yellow
}

TECH_LABELS = {
    "air_hp": "Air Heat Pump",
    "dh_large_hp": "District Heat Pump",
    "gas_boiler": "Gas Boiler",
    "h2_boiler": "Hydrogen Boiler",
    "biomass_boiler": "Biomass Boiler",
    "tes": "Thermal Storage (TES)",
}

ARCHETYPE_COLORS = {
    "Metropolitan": "#6366f1",
    "Suburban": "#22d3ee",
    "Rural-Dense": "#84cc16",
    "Rural-Sparse": "#f97316",
    "Industrial": "#a855f7",
}


def plot_pareto_frontier(df, output_path=None):
    """
    Plots the Socio-Technical Cost-Acceptance Pareto Curve.
    Highlights the optimal space and MGA sweep solutions.
    """
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=150)
    
    # Extract Pareto-dominant points for Max Acceptance
    max_candidates = df[df["objective_type"].isin(["max_acceptance", "cost_optimal_exogenous"])].sort_values("system_cost_billion")
    pareto_max_x = []
    pareto_max_y = []
    pareto_max_eps = []
    current_max_acc = -np.inf
    
    for idx, row in max_candidates.iterrows():
        if row["social_acceptance_index"] > current_max_acc:
            pareto_max_x.append(row["system_cost_billion"])
            pareto_max_y.append(row["social_acceptance_index"])
            pareto_max_eps.append(row["epsilon"])
            current_max_acc = row["social_acceptance_index"]
            
    # Extract Pareto-dominant points for Min Acceptance (worst case)
    min_candidates = df[df["objective_type"].isin(["min_acceptance", "cost_optimal_exogenous"])].sort_values("system_cost_billion")
    pareto_min_x = []
    pareto_min_y = []
    current_min_acc = np.inf
    
    for idx, row in min_candidates.iterrows():
        if row["social_acceptance_index"] < current_min_acc:
            pareto_min_x.append(row["system_cost_billion"])
            pareto_min_y.append(row["social_acceptance_index"])
            current_min_acc = row["social_acceptance_index"]
            
    base_pt = df[df["objective_type"] == "cost_optimal_exogenous"].iloc[0]
    
    all_x = pareto_max_x + pareto_min_x[::-1]
    all_y = pareto_max_y + pareto_min_y[::-1]
    
    # Fill feasibility space
    ax.fill(all_x, all_y, color="#c084fc", alpha=0.15, label="Socio-Technical Flexibility Space")
    
    # Plot curves
    ax.plot(pareto_max_x, pareto_max_y,
            color="#8b5cf6", linestyle="-", linewidth=2.5, marker="o", markersize=6,
            label="Social Feasibility Frontier (Max)")
            
    ax.plot(pareto_min_x, pareto_min_y,
            color="#64748b", linestyle="--", linewidth=1.5, marker="v", markersize=5,
            label="Worst Social Case (Min)")
            
    # Baseline scatter
    ax.scatter(base_pt["system_cost_billion"], base_pt["social_acceptance_index"],
               color="#ef4444", s=140, marker="o", zorder=5, edgecolors="white", linewidths=2.0,
               label="Cost-Optimal Baseline (ε = 0%)")
               
    # Annotate points
    for x, y, eps in zip(pareto_max_x, pareto_max_y, pareto_max_eps):
        if eps > 0:
            eps_pct = int(eps * 100)
            ax.annotate(f"ε={eps_pct}%",
                        xy=(x, y),
                        xytext=(8, -3), textcoords="offset points",
                        fontsize=9, weight="600", color="#7c3aed")
                    
    ax.set_title("Cost-Acceptance Pareto Frontier (Germany 2045)", fontsize=14, weight="700", pad=15)
    ax.set_xlabel("Annual Heat System Cost [Billion EUR / year]", fontsize=11, labelpad=10)
    ax.set_ylabel("System Social Acceptance Index [GW-equiv]", fontsize=11, labelpad=10)
    
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#e2e8f0", framealpha=0.9, fontsize=10)
    ax.tick_params(colors="#475569", labelsize=10)
    
    if output_path:
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_capacity_stack(df, output_path=None):
    """
    Plots a stacked bar chart of optimized technology capacities across MGA slacks.
    """
    plot_df = df[df["objective_type"].isin(["cost_optimal", "max_acceptance"])].sort_values("epsilon")
    
    labels = ["Baseline\n(ε=0%)"] + [f"Max Accept\n(ε={int(e*100)}%)" for e in plot_df["epsilon"].values[1:]]
    
    cap_data = {}
    for t in TECH_LABELS.keys():
        if t == "tes":
            continue
        cap_data[t] = plot_df[f"cap_{t}_gw"].values
        
    fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
    bottom = np.zeros(len(labels))
    
    for tech, vals in cap_data.items():
        ax.bar(labels, vals, bottom=bottom, color=TECH_COLORS[tech], width=0.55,
               edgecolor="white", linewidth=0.5, label=TECH_LABELS[tech])
        bottom += vals
        
    ax.set_title("Optimal Heating Capacity Mix under Social Acceptance Slack", fontsize=13, weight="700", pad=15)
    ax.set_ylabel("Total Installed Capacity [GW]", fontsize=11, labelpad=10)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=True, facecolor="white", edgecolor="#e2e8f0", fontsize=10)
    
    # Add values on top of bars
    for i, val in enumerate(bottom):
        ax.annotate(f"{val:.1f} GW",
                    xy=(i, val),
                    xytext=(0, 5), textcoords="offset points",
                    ha="center", va="bottom", fontsize=9, weight="600", color="#334155")
                    
    ax.tick_params(colors="#475569", labelsize=10)
    
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_hourly_dispatch(n, archetype, start_hour=0, duration_hours=168, output_path=None):
    """
    Plots the hourly dispatch profiles for a specific archetype during a specific time window.
    Displays the contribution of heating technologies and TES state-of-charge.
    """
    snapshots = n.snapshots[start_hour:start_hour + duration_hours]
    load_name = f"heat_load_{archetype}"
    
    demand = n.loads_t.p[load_name].loc[snapshots]
    
    dispatch_data = {}
    for t in TECH_LABELS.keys():
        if t == "tes":
            continue
        link_name = f"{t}_{archetype}"
        if link_name in n.links.index:
            dispatch_data[t] = n.links_t.p1[link_name].loc[snapshots]
            
    tes_name = f"tes_{archetype}"
    tes_soc = n.stores_t.e[tes_name].loc[snapshots] if tes_name in n.stores.index else None
    tes_p = n.stores_t.p[tes_name].loc[snapshots] if tes_name in n.stores.index else None
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True, dpi=150,
                                   gridspec_kw={"height_ratios": [2, 1]})
                                   
    bottom = np.zeros(len(snapshots))
    for tech, vals in dispatch_data.items():
        ax1.fill_between(snapshots, bottom, bottom + vals, color=TECH_COLORS[tech],
                         alpha=0.85, step="post", label=TECH_LABELS[tech])
        bottom += vals.values
        
    if tes_p is not None:
        discharging = np.clip(-tes_p.values, 0, None)
        charging = np.clip(tes_p.values, 0, None)
        ax1.fill_between(snapshots, bottom, bottom + discharging, color=TECH_COLORS["tes"],
                         alpha=0.6, step="post", label="TES Discharge")
        ax1.fill_between(snapshots, -charging, 0, color=TECH_COLORS["tes"],
                         alpha=0.3, step="post", hatch="//", label="TES Charge")
                         
    ax1.plot(snapshots, demand, color="#0f172a", linestyle="-", linewidth=2.0, label="Thermal Demand")
    
    ax1.set_title(f"Hourly Thermal Dispatch — {archetype} Archetype", fontsize=13, weight="700", pad=15)
    ax1.set_ylabel("Heat Power [MW]", fontsize=11, labelpad=10)
    ax1.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#e2e8f0", ncol=3, fontsize=9)
    
    if tes_p is not None and charging.max() > 0:
        ax1.set_ylim(-charging.max() * 1.1, None)
    else:
        ax1.set_ylim(0, None)
        
    if tes_soc is not None:
        ax2.plot(snapshots, tes_soc, color=TECH_COLORS["tes"], linewidth=2.2, label="TES State of Charge")
        ax2.fill_between(snapshots, 0, tes_soc, color=TECH_COLORS["tes"], alpha=0.1)
        ax2.set_ylabel("Storage Energy [MWh]", fontsize=11, labelpad=10)
        ax2.set_xlabel("Snapshot Timestamp", fontsize=11, labelpad=10)
        ax2.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#e2e8f0", fontsize=9)
        
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


# ============================================================================
# NEW ENHANCEMENT PLOTS
# ============================================================================

def plot_co2_marginal_abatement_curve(co2_df, output_path=None):
    """
    Plots CO2 cap (x-axis) vs System Cost (y-axis).
    The slope between adjacent points gives the marginal abatement cost.
    """
    df = co2_df.dropna(subset=["system_cost_billion"]).sort_values("co2_cap_mt")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=150)
    
    # Left panel: Cost vs CO2 Cap
    ax1.plot(df["co2_cap_mt"], df["system_cost_billion"],
             color="#8b5cf6", linewidth=2.5, marker="o", markersize=8,
             markerfacecolor="white", markeredgewidth=2, markeredgecolor="#8b5cf6")
    
    ax1.fill_between(df["co2_cap_mt"], df["system_cost_billion"].min() * 0.95,
                     df["system_cost_billion"], color="#8b5cf6", alpha=0.08)
    
    for _, row in df.iterrows():
        ax1.annotate(f"€{row['system_cost_billion']:.1f}B",
                     xy=(row["co2_cap_mt"], row["system_cost_billion"]),
                     xytext=(5, 10), textcoords="offset points",
                     fontsize=9, weight="600", color="#5b21b6")
    
    ax1.set_xlabel("CO2 Emission Cap [MtCO2]", fontsize=11, labelpad=10)
    ax1.set_ylabel("Annual System Cost [Billion EUR/yr]", fontsize=11, labelpad=10)
    ax1.set_title("System Cost vs Carbon Stringency", fontsize=13, weight="700", pad=15)
    ax1.tick_params(colors="#475569", labelsize=10)
    
    # Right panel: Marginal Abatement Cost
    if len(df) > 1:
        caps = df["co2_cap_mt"].values
        costs = df["system_cost_billion"].values
        # MAC = Δcost / Δemissions_avoided (EUR/tCO2)
        mac = []
        mac_labels = []
        for i in range(len(caps) - 1):
            delta_cost = (costs[i] - costs[i + 1]) * 1e9  # EUR
            delta_co2 = (caps[i + 1] - caps[i]) * 1e6     # tCO2
            if delta_co2 != 0:
                mac_val = delta_cost / delta_co2
                mac.append(mac_val)
                mac_labels.append(f"{caps[i]:.1f}→{caps[i+1]:.1f}")
        
        colors_mac = plt.cm.RdYlGn_r(np.linspace(0.2, 0.9, len(mac)))
        bars = ax2.bar(mac_labels, mac, color=colors_mac, width=0.6, edgecolor="white", linewidth=1)
        
        for bar, val in zip(bars, mac):
            ax2.annotate(f"€{val:.0f}/t",
                         xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                         xytext=(0, 5), textcoords="offset points",
                         ha="center", fontsize=9, weight="600", color="#334155")
        
        ax2.set_xlabel("CO2 Cap Transition", fontsize=11, labelpad=10)
        ax2.set_ylabel("Marginal Abatement Cost [EUR/tCO2]", fontsize=11, labelpad=10)
        ax2.set_title("Marginal Cost of CO2 Reduction", fontsize=13, weight="700", pad=15)
        ax2.tick_params(colors="#475569", labelsize=10)
    
    plt.tight_layout(w_pad=4)
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_archetype_capacity_heatmap(metrics_dict, output_path=None):
    """
    Draws a heatmap (5 archetypes × 5 technologies) of optimal capacity allocations.
    metrics_dict: a single row from extract_metrics containing per-archetype caps.
    """
    data = np.zeros((len(ARCHETYPES), len(TECHNOLOGIES)))
    for i, a in enumerate(ARCHETYPES):
        for j, t in enumerate(TECHNOLOGIES):
            key = f"cap_{t}_{a}_mw"
            data[i, j] = metrics_dict.get(key, 0.0) / 1000.0  # Convert to GW
    
    df_heatmap = pd.DataFrame(data,
                               index=ARCHETYPES,
                               columns=[TECH_LABELS.get(t, t) for t in TECHNOLOGIES])
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    
    sns.heatmap(df_heatmap, annot=True, fmt=".1f", cmap="YlOrRd",
                linewidths=2, linecolor="white", cbar_kws={"label": "Installed Capacity [GW]"},
                ax=ax, annot_kws={"fontsize": 11, "weight": "600"})
    
    ax.set_title("Spatial Technology Allocation across Municipal Archetypes",
                 fontsize=13, weight="700", pad=15)
    ax.set_ylabel("Municipal Archetype", fontsize=11, labelpad=10)
    ax.set_xlabel("Heating Technology", fontsize=11, labelpad=10)
    ax.tick_params(colors="#475569", labelsize=10)
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_retrofit_impact_comparison(retrofit_df, output_path=None):
    """
    Grouped bar chart comparing system cost, total capacity, and CO2 emissions
    across building retrofit scenarios.
    """
    df = retrofit_df.dropna(subset=["system_cost_billion"]).copy()
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), dpi=150)
    
    scenarios = df["scenario"].values
    x = np.arange(len(scenarios))
    width = 0.55
    
    # Panel 1: System Cost (with and without retrofit investment)
    ax = axes[0]
    bars1 = ax.bar(x, df["system_cost_billion"], width, color="#3b82f6", alpha=0.85,
                   edgecolor="white", label="Heating System Cost")
    if "retrofit_investment_billion" in df.columns:
        bars2 = ax.bar(x, df["retrofit_investment_billion"], width,
                       bottom=df["system_cost_billion"], color="#f59e0b",
                       alpha=0.85, edgecolor="white", label="Retrofit Investment")
    ax.set_ylabel("Cost [Billion EUR/yr]", fontsize=10, labelpad=8)
    ax.set_title("Total System Cost", fontsize=12, weight="700", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], fontsize=9)
    ax.legend(fontsize=9, frameon=True, facecolor="white", edgecolor="#e2e8f0")
    
    # Panel 2: Total Installed Capacity
    ax = axes[1]
    total_cap = []
    for _, row in df.iterrows():
        cap = sum(row.get(f"cap_{t}_gw", 0) for t in TECHNOLOGIES)
        total_cap.append(cap)
    ax.bar(x, total_cap, width, color="#8b5cf6", alpha=0.85, edgecolor="white")
    for i, v in enumerate(total_cap):
        ax.annotate(f"{v:.1f}", xy=(i, v), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=10, weight="600", color="#5b21b6")
    ax.set_ylabel("Installed Capacity [GW]", fontsize=10, labelpad=8)
    ax.set_title("Total Heating Capacity", fontsize=12, weight="700", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], fontsize=9)
    
    # Panel 3: CO2 Emissions
    ax = axes[2]
    ax.bar(x, df["co2_emissions_mt"], width, color="#ef4444", alpha=0.85, edgecolor="white")
    for i, v in enumerate(df["co2_emissions_mt"]):
        ax.annotate(f"{v:.2f}", xy=(i, v), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=10, weight="600", color="#991b1b")
    ax.set_ylabel("Direct CO2 [MtCO2]", fontsize=10, labelpad=8)
    ax.set_title("Carbon Emissions", fontsize=12, weight="700", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], fontsize=9)
    
    fig.suptitle("Impact of Building Retrofit on Heat System Design",
                 fontsize=14, weight="700", y=1.02)
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_seasonal_dispatch_triptych(n, archetype, output_path=None):
    """
    Three side-by-side dispatch panels: Winter / Shoulder / Summer weeks.
    Assumes the network uses 504-snapshot representative weeks (3×168).
    """
    n_snaps = len(n.snapshots)
    if n_snaps < 504:
        # Fall back to equal thirds of available snapshots
        chunk = n_snaps // 3
        ranges = [(0, chunk), (chunk, 2*chunk), (2*chunk, n_snaps)]
        season_labels = ["Period 1", "Period 2", "Period 3"]
    else:
        ranges = [(0, 168), (168, 336), (336, 504)]
        season_labels = ["Winter Week", "Shoulder Week", "Summer Week"]
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), dpi=150, sharey=True)
    
    for ax, (start, end), label in zip(axes, ranges, season_labels):
        snaps = n.snapshots[start:end]
        load_name = f"heat_load_{archetype}"
        demand = n.loads_t.p[load_name].loc[snaps]
        
        bottom = np.zeros(len(snaps))
        for t in TECHNOLOGIES:
            link_name = f"{t}_{archetype}"
            if link_name in n.links_t.p1.columns:
                vals = n.links_t.p1[link_name].loc[snaps].values
                ax.fill_between(range(len(snaps)), bottom, bottom + vals,
                               color=TECH_COLORS[t], alpha=0.8, step="post",
                               label=TECH_LABELS[t])
                bottom += vals
        
        ax.plot(range(len(snaps)), demand.values, color="#0f172a", linewidth=1.5,
                label="Demand", linestyle="-")
        ax.set_title(label, fontsize=12, weight="700", pad=10)
        ax.set_xlabel("Hour", fontsize=10)
        ax.tick_params(colors="#475569", labelsize=9)
    
    axes[0].set_ylabel("Heat Power [MW]", fontsize=11, labelpad=10)
    
    # Shared legend
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=6, frameon=True,
              facecolor="white", edgecolor="#e2e8f0", fontsize=9,
              bbox_to_anchor=(0.5, -0.05))
    
    fig.suptitle(f"Seasonal Dispatch Dynamics — {archetype} Archetype",
                 fontsize=14, weight="700", y=1.02)
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_emissions_waterfall(direct_co2_mt, indirect_co2_mt, output_path=None):
    """
    Waterfall chart decomposing total lifecycle emissions:
    Direct gas CO2 → Indirect HP CO2 (grid) → Net total.
    """
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    
    total = direct_co2_mt + indirect_co2_mt
    
    categories = ["Direct\n(Gas Boilers)", "Indirect\n(HP Grid)", "Total\nLifecycle"]
    values = [direct_co2_mt, indirect_co2_mt, total]
    colors = ["#ef4444", "#f59e0b", "#6366f1"]
    
    # Waterfall logic: first two are additive, third is the total
    bottoms = [0, direct_co2_mt, 0]
    
    bars = ax.bar(categories, values, bottom=bottoms, color=colors, width=0.5,
                  edgecolor="white", linewidth=2, alpha=0.9)
    
    # Connector lines
    ax.plot([0.25, 0.75], [direct_co2_mt, direct_co2_mt],
            color="#94a3b8", linewidth=1.5, linestyle="--")
    ax.plot([1.25, 1.75], [total, total],
            color="#94a3b8", linewidth=1.5, linestyle="--")
    
    # Value annotations
    for i, (bar, val) in enumerate(zip(bars, values)):
        y_pos = bottoms[i] + val
        ax.annotate(f"{val:.3f} Mt",
                    xy=(bar.get_x() + bar.get_width() / 2, y_pos),
                    xytext=(0, 8), textcoords="offset points",
                    ha="center", fontsize=11, weight="700", color=colors[i])
    
    ax.set_title("Lifecycle CO2 Emissions Decomposition", fontsize=14, weight="700", pad=15)
    ax.set_ylabel("CO2 Emissions [MtCO2]", fontsize=11, labelpad=10)
    ax.tick_params(colors="#475569", labelsize=10)
    ax.set_ylim(0, total * 1.3)
    
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_cost_decomposition_sunburst(metrics_dict, output_path=None):
    """
    Nested donut chart: inner ring = CAPEX vs OPEX split;
    outer ring = breakdown by technology.
    """
    fig, ax = plt.subplots(figsize=(9, 9), dpi=150)
    
    # Calculate CAPEX and OPEX components by technology
    capex_by_tech = {}
    opex_total = 0.0
    
    for t in TECHNOLOGIES:
        cap_gw = metrics_dict.get(f"cap_{t}_gw", 0.0)
        if cap_gw > 0:
            from src.config import CAPEX as CAPEX_DICT, LIFETIME as LIFETIME_DICT, FOM as FOM_DICT, get_annuity as _annuity
            ann = _annuity(CAPEX_DICT[t], LIFETIME_DICT[t])
            fom = CAPEX_DICT[t] * FOM_DICT[t]
            capex_by_tech[t] = (ann + fom) * cap_gw * 1e-3  # Billion EUR
        else:
            capex_by_tech[t] = 0.0
    
    total_capex = sum(capex_by_tech.values())
    total_system = metrics_dict.get("system_cost_billion", 0.0)
    opex_total = max(0, total_system - total_capex)
    
    # Inner ring: CAPEX vs OPEX
    inner_sizes = [total_capex, opex_total]
    inner_labels = [f"CAPEX\n€{total_capex:.1f}B", f"OPEX\n€{opex_total:.1f}B"]
    inner_colors = ["#6366f1", "#10b981"]
    
    # Outer ring: By technology + OPEX
    outer_sizes = []
    outer_labels = []
    outer_colors = []
    for t in TECHNOLOGIES:
        if capex_by_tech[t] > 0:
            outer_sizes.append(capex_by_tech[t])
            outer_labels.append(f"{TECH_LABELS[t]}\n€{capex_by_tech[t]:.1f}B")
            outer_colors.append(TECH_COLORS[t])
    if opex_total > 0:
        outer_sizes.append(opex_total)
        outer_labels.append(f"Fuel & Grid\n€{opex_total:.1f}B")
        outer_colors.append("#10b981")
    
    # Draw inner donut
    wedges1, texts1 = ax.pie(inner_sizes, radius=0.65, labels=inner_labels,
                              colors=inner_colors, startangle=90,
                              wedgeprops=dict(width=0.3, edgecolor="white", linewidth=3),
                              textprops={"fontsize": 10, "weight": "700"})
    
    # Draw outer donut
    wedges2, texts2 = ax.pie(outer_sizes, radius=1.0, labels=outer_labels,
                              colors=outer_colors, startangle=90,
                              wedgeprops=dict(width=0.3, edgecolor="white", linewidth=2),
                              textprops={"fontsize": 9, "weight": "600"})
    
    ax.set_title(f"Cost Decomposition — Total €{total_system:.1f}B/yr",
                 fontsize=14, weight="700", pad=20, y=1.05)
    
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


# ═══════════════════════════════════════════════════════════════════════════
# EMPIRICAL DIAGNOSTIC PLOTS (Kreise Integration)
# ═══════════════════════════════════════════════════════════════════════════

ARCHETYPE_COLORS = {
    "Metropolitan": "#ef4444",
    "Suburban": "#3b82f6",
    "Rural-Dense": "#10b981",
    "Rural-Sparse": "#f59e0b",
    "Industrial": "#8b5cf6",
}


def plot_kreise_archetype_map(df, output_path=None):
    """
    Scatter plot of ~400 Kreise on Population Density vs Industrial VA Share,
    colored by K-Means archetype assignment.
    """
    fig, ax = plt.subplots(figsize=(10, 7))

    for archetype in ARCHETYPES:
        mask = df["archetype"] == archetype
        subset = df[mask]
        ax.scatter(
            subset["Population Density (Einwohner je km2)"],
            subset["Proportion of Industrial Value Added in Total Value Added"],
            c=ARCHETYPE_COLORS.get(archetype, "#94a3b8"),
            label=f"{archetype} (n={len(subset)})",
            alpha=0.65,
            s=30,
            edgecolors="white",
            linewidth=0.4,
        )

    ax.set_xscale("log")
    ax.set_xlabel("Population Density (inhabitants/km²) — log scale",
                  fontsize=12, weight="600")
    ax.set_ylabel("Industrial Value Added Share",
                  fontsize=12, weight="600")
    ax.set_title("German Kreise: Archetype Classification via K-Means Clustering",
                 fontsize=14, weight="700", pad=12)
    ax.legend(fontsize=10, loc="upper right", framealpha=0.9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_empirical_vs_synthetic_comparison(empirical_params, output_path=None):
    """
    Side-by-side grouped bar charts comparing synthetic (hardcoded) vs
    empirical (data-derived) archetype parameters.
    """
    from src.config import (
        HEAT_LOAD_SHARES as SYN_HLS,
        DH_PIPING_PREMIUM as SYN_DHP,
        RETROFIT_APPLICABILITY as SYN_RA,
    )

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
    archetypes = ARCHETYPES
    x = np.arange(len(archetypes))
    width = 0.35

    # Panel 1: Heat Load Shares
    ax = axes[0]
    syn_vals = [SYN_HLS[a] for a in archetypes]
    emp_vals = [empirical_params["HEAT_LOAD_SHARES"][a] for a in archetypes]
    ax.bar(x - width/2, syn_vals, width, label="Synthetic", color="#94a3b8", edgecolor="white")
    ax.bar(x + width/2, emp_vals, width, label="Empirical", color="#3b82f6", edgecolor="white")
    ax.set_ylabel("Share", fontsize=11, weight="600")
    ax.set_title("Heat Load Shares", fontsize=12, weight="700")
    ax.set_xticks(x)
    ax.set_xticklabels(archetypes, rotation=35, ha="right", fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    # Panel 2: DH Piping Premium
    ax = axes[1]
    syn_vals = [SYN_DHP[a] for a in archetypes]
    emp_vals = [empirical_params["DH_PIPING_PREMIUM"][a] for a in archetypes]
    ax.bar(x - width/2, syn_vals, width, label="Synthetic", color="#94a3b8", edgecolor="white")
    ax.bar(x + width/2, emp_vals, width, label="Empirical", color="#8b5cf6", edgecolor="white")
    ax.set_ylabel("EUR/kW", fontsize=11, weight="600")
    ax.set_title("DH Piping Premium", fontsize=12, weight="700")
    ax.set_xticks(x)
    ax.set_xticklabels(archetypes, rotation=35, ha="right", fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    # Panel 3: Retrofit Applicability
    ax = axes[2]
    syn_vals = [SYN_RA[a] for a in archetypes]
    emp_vals = [empirical_params["RETROFIT_APPLICABILITY"][a] for a in archetypes]
    ax.bar(x - width/2, syn_vals, width, label="Synthetic", color="#94a3b8", edgecolor="white")
    ax.bar(x + width/2, emp_vals, width, label="Empirical", color="#10b981", edgecolor="white")
    ax.set_ylabel("Fraction", fontsize=11, weight="600")
    ax.set_title("Retrofit Applicability", fontsize=12, weight="700")
    ax.set_xticks(x)
    ax.set_xticklabels(archetypes, rotation=35, ha="right", fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Empirical vs Synthetic Archetype Parameters",
                 fontsize=15, weight="700", y=1.02)
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_kreise_climate_boxplots(df, output_path=None):
    """
    Box plots of HDD, Temperature, and Renewable Heating share by archetype,
    showing intra-archetype variation across real Kreise.
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

    plot_vars = [
        ("Heating Degree Days", "HDD (degree-days/yr)", "#ef4444"),
        ("Temperature", "Mean Temperature (°C)", "#3b82f6"),
        ("Residential Building with Renewable Heating", "Renewable Heating (%)", "#10b981"),
    ]

    order = ARCHETYPES

    for ax, (col, ylabel, color) in zip(axes, plot_vars):
        if col not in df.columns:
            ax.text(0.5, 0.5, f"'{col}' not found", transform=ax.transAxes,
                    ha="center", fontsize=12)
            continue

        data_to_plot = []
        labels = []
        for a in order:
            vals = df.loc[df["archetype"] == a, col].dropna().values
            if len(vals) > 0:
                data_to_plot.append(vals)
                labels.append(a)

        bp = ax.boxplot(data_to_plot, patch_artist=True, labels=labels,
                        widths=0.6, showfliers=True,
                        flierprops={"marker": ".", "markersize": 3, "alpha": 0.4})

        for i, patch in enumerate(bp["boxes"]):
            arch_name = labels[i]
            c = ARCHETYPE_COLORS.get(arch_name, color)
            patch.set_facecolor(c)
            patch.set_alpha(0.5)
            patch.set_edgecolor(c)

        ax.set_ylabel(ylabel, fontsize=11, weight="600")
        ax.tick_params(axis="x", rotation=35, labelsize=9)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Climate & Energy Variables by Archetype (Real Kreise Data)",
                 fontsize=15, weight="700", y=1.02)
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_german_nuts3_map(df, output_path=None):
    """
    Plots a 1x2 side-by-side geographic NUTS3 map of Germany:
    - Left Panel: Municipal Archetype typology (K-Means clusters)
    - Right Panel: Empirical renewable heating penetration (%)
    
    Caches boundaries locally in results/ to avoid repeated Eurostat downloads.
    """
    import os
    import geopandas as gpd
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    
    # 1. Load NUTS3 boundaries (cache locally to results/)
    geojson_path = "results/nuts3_boundaries.geojson"
    os.makedirs("results", exist_ok=True)
    
    if not os.path.exists(geojson_path):
        print("[INFO] Fetching German NUTS3 boundaries from Eurostat...")
        url = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2021_4326.geojson"
        try:
            gdf = gpd.read_file(url)
            # Filter to German NUTS3
            de_gdf = gdf[(gdf["CNTR_CODE"] == "DE") & (gdf["LEVL_CODE"] == 3)].copy()
            de_gdf.to_file(geojson_path, driver="GeoJSON")
            print("[INFO] NUTS3 boundaries cached successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to download from Eurostat: {e}. Falling back to unmapped plotting.")
            return
    else:
        de_gdf = gpd.read_file(geojson_path)
        
    # 2. Merge boundaries with district dataframe
    # Make sure Code is str and clean
    df_clean = df.copy()
    df_clean["Code"] = df_clean["Code"].astype(str).str.strip()
    de_gdf["NUTS_ID"] = de_gdf["NUTS_ID"].astype(str).str.strip()
    
    merged = de_gdf.merge(df_clean, left_on="NUTS_ID", right_on="Code", how="left")
    
    # 3. Create the figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9.5), dpi=200)
    
    # Define archetype colors matching project palette
    colors_dict = {
        "Metropolitan": "#ef4444", # Red
        "Suburban": "#3b82f6",     # Blue
        "Rural-Dense": "#10b981", # Emerald green
        "Rural-Sparse": "#f59e0b", # Amber
        "Industrial": "#8b5cf6",   # Purple
    }
    
    # Left Map: Archetypes
    merged.plot(ax=ax1, color="#f1f5f9", edgecolor="#cbd5e1", linewidth=0.2)
    
    for archetype, color in colors_dict.items():
        sub = merged[merged["archetype"] == archetype]
        if not sub.empty:
            sub.plot(ax=ax1, color=color, edgecolor="#ffffff", linewidth=0.15,
                     label=archetype)
            
    ax1.set_axis_off()
    ax1.set_title("German Heating Typology\n(K-Means Municipal Archetypes)", fontsize=13, weight="700", pad=12)
    
    # Custom legend for Left Map
    patches = [mpatches.Patch(color=color, label=arch) for arch, color in colors_dict.items()]
    ax1.legend(handles=patches, loc="lower left", frameon=True, facecolor="white",
               edgecolor="#e2e8f0", fontsize=9, title="Archetypes")
    
    # Right Map: Renewable Heating Penetration
    col_name = "Residential Building with Renewable Heating"
    if col_name in merged.columns:
        merged.plot(ax=ax2, color="#f1f5f9", edgecolor="#cbd5e1", linewidth=0.2)
        
        merged.plot(
            column=col_name,
            ax=ax2,
            cmap="YlOrRd",
            edgecolor="#ffffff",
            linewidth=0.1,
            legend=True,
            legend_kwds={
                "label": "Residential Buildings with Renewable Heating [%]",
                "orientation": "horizontal",
                "pad": 0.05,
                "shrink": 0.75,
                "aspect": 30,
            }
        )
        ax2.set_title("Current Energy Transition Status\n(Renewable Heating Share in Buildings)", fontsize=13, weight="700", pad=12)
    else:
        ax2.text(0.5, 0.5, f"'{col_name}' column not found!", ha="center", transform=ax2.transAxes)
        
    ax2.set_axis_off()
    
    # Add key city annotations to make it instantly recognizable
    cities = {
        "Berlin": (13.4050, 52.5200),
        "Hamburg": (9.9937, 53.5511),
        "München": (11.5820, 48.1351),
        "Köln": (6.9583, 50.9375),
        "Frankfurt": (8.6821, 50.1109),
    }
    
    for ax in [ax1, ax2]:
        for city, coords in cities.items():
            ax.scatter(coords[0], coords[1], color="#0f172a", s=15, zorder=5, edgecolor="white", linewidth=0.5)
            ax.annotate(city, xy=coords, xytext=(4, 2), textcoords="offset points",
                        fontsize=8, weight="700", color="#1e293b", zorder=6)
            
    fig.suptitle("Empirical Mapping of the German Space (NUTS3 / Kreise)", fontsize=16, weight="800", y=0.98)
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_social_feasibility_frontier(df, output_path=None):
    """
    Plots the Social Feasibility Frontier showing the trade-off between
    system cost and social acceptance under endogenous acceptance penalties.
    
    Shows: feasibility space, endogenous vs exogenous cost-optimal points,
    and the cost premium for social feasibility.
    """
    fig, ax = plt.subplots(figsize=(10, 7), dpi=150)
    
    # Filter data
    max_pts = df[df["objective_type"] == "max_acceptance"].sort_values("system_cost_billion")
    min_pts = df[df["objective_type"] == "min_acceptance"].sort_values("system_cost_billion")
    cost_opt = df[df["objective_type"] == "cost_optimal"]
    cost_opt_exo = df[df["objective_type"] == "cost_optimal_exogenous"]
    
    # Fill feasibility space
    if len(max_pts) > 0 and len(min_pts) > 0:
        all_x = pd.concat([max_pts["system_cost_billion"], min_pts["system_cost_billion"].iloc[::-1]])
        all_y = pd.concat([max_pts["social_acceptance_index"], min_pts["social_acceptance_index"].iloc[::-1]])
        ax.fill(all_x, all_y, color="#a78bfa", alpha=0.15, label="Social Feasibility Space")
        
        ax.plot(max_pts["system_cost_billion"], max_pts["social_acceptance_index"],
                "o-", color="#7c3aed", lw=2.5, ms=8, label="Max Social Acceptance", zorder=5)
        ax.plot(min_pts["system_cost_billion"], min_pts["social_acceptance_index"],
                "s--", color="#f97316", lw=2, ms=7, label="Min Social Acceptance", zorder=5)
    
    # Cost-optimal points
    if len(cost_opt) > 0:
        co = cost_opt.iloc[0]
        ax.scatter(co["system_cost_billion"], co["social_acceptance_index"],
                   s=200, color="#10b981", marker="*", zorder=10, edgecolors="white", linewidth=1.5,
                   label=f"Cost-Optimal (endogenous)")
    
    if len(cost_opt_exo) > 0:
        ce = cost_opt_exo.iloc[0]
        ax.scatter(ce["system_cost_billion"], ce["social_acceptance_index"],
                   s=180, color="#ef4444", marker="D", zorder=10, edgecolors="white", linewidth=1.5,
                   label=f"Cost-Optimal (no acceptance)")
    
    # Annotate the cost premium
    if len(cost_opt) > 0 and len(max_pts) > 0:
        best_acc = max_pts.loc[max_pts["social_acceptance_index"].idxmax()]
        co = cost_opt.iloc[0]
        premium_pct = ((best_acc["system_cost_billion"] - co["system_cost_billion"]) / co["system_cost_billion"]) * 100
        ax.annotate(
            f"Social premium:\n+{premium_pct:.1f}% cost",
            xy=(best_acc["system_cost_billion"], best_acc["social_acceptance_index"]),
            xytext=(best_acc["system_cost_billion"] + 0.3, best_acc["social_acceptance_index"] - 3),
            fontsize=10, weight="600", color="#7c3aed",
            arrowprops=dict(arrowstyle="->", color="#7c3aed", lw=1.5),
        )
    
    ax.set_xlabel("System Cost (Billion EUR)", fontsize=13, weight="600")
    ax.set_ylabel("Social Acceptance Index (GW-weighted)", fontsize=13, weight="600")
    ax.set_title("Social Feasibility Frontier\nMunicipally-Differentiated Heat Decarbonization with Endogenous Acceptance",
                 fontsize=14, weight="700", pad=15)
    ax.legend(loc="lower right", fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_acceptance_heatmap(sa_matrix, gas_lock_in=None, output_path=None):
    """
    Plots a styled heatmap of the ML-derived social acceptance matrix.
    Optionally overlays gas lock-in indices.
    """
    fig, axes = plt.subplots(1, 2 if gas_lock_in else 1,
                             figsize=(14 if gas_lock_in else 8, 5), dpi=150,
                             gridspec_kw={"width_ratios": [4, 1] if gas_lock_in else [1]})
    
    if gas_lock_in:
        ax_main, ax_lock = axes
    else:
        ax_main = axes
    
    # Acceptance heatmap
    tech_labels = {
        "air_hp": "Air HP", "dh_large_hp": "District HP",
        "gas_boiler": "Gas Boiler", "h2_boiler": "H₂ Boiler",
        "biomass_boiler": "Biomass"
    }
    sa_display = sa_matrix.copy()
    sa_display.columns = [tech_labels.get(c, c) for c in sa_display.columns]
    
    sns.heatmap(sa_display, annot=True, fmt="+.2f", cmap="RdYlGn", center=0,
                vmin=-1.0, vmax=1.0, linewidths=1, linecolor="white",
                ax=ax_main, cbar_kws={"label": "Acceptance Score", "shrink": 0.8})
    ax_main.set_title("ML-Derived Social Acceptance Matrix\n(9 empirical features from Kreise dataset)",
                      fontsize=13, weight="700", pad=10)
    ax_main.set_ylabel("Municipal Archetype", fontsize=11, weight="600")
    ax_main.set_xlabel("Technology", fontsize=11, weight="600")
    ax_main.tick_params(axis="x", rotation=30)
    
    # Gas lock-in bar
    if gas_lock_in:
        archetypes = list(gas_lock_in.keys())
        values = list(gas_lock_in.values())
        colors = ["#ef4444" if v > 0.6 else "#f59e0b" if v > 0.4 else "#10b981" for v in values]
        ax_lock.barh(archetypes, values, color=colors, edgecolor="white", linewidth=1)
        ax_lock.set_xlim(0, 1)
        ax_lock.set_xlabel("Gas Lock-In\nIndex", fontsize=10, weight="600")
        ax_lock.set_title("Lock-In", fontsize=12, weight="700", pad=10)
        ax_lock.invert_yaxis()
        for i, v in enumerate(values):
            ax_lock.text(v + 0.02, i, f"{v:.3f}", va="center", fontsize=9, weight="500")
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()
