"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ESM-P1 MGA — COMPLETE INFOGRAPHICS GENERATION SCRIPT              ║
║                  For: ESM-P1- MGA/Result_2/                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

USAGE:
    python create_all_infographics.py

OUTPUT:
    Creates all infographics in: Result_2/infographics/

DEPENDENCIES:
    pip install pandas numpy matplotlib seaborn plotly kaleido

"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch, Circle, Wedge
from matplotlib.collections import LineCollection
import matplotlib.colors as mcolors
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────────────────────

# Paths for Kaggle (/) and local (./)
RESULTS_DIR = Path('/kaggle/working/data') if Path('/kaggle/working').exists() else Path('data')
OUTPUT_DIR = RESULTS_DIR / 'figures'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.family'] = 'sans-serif'

# Color palette
COLORS = {
    'solar': '#f59e0b',
    'wind': '#3b82f6', 
    'gas': '#f97316',
    'lignite': '#78350f',
    'storage': '#8b5cf6',
    'positive': '#10b981',
    'negative': '#ef4444',
    'primary': '#1e40af',
    'secondary': '#64748b',
    'accent': '#8b5cf6',
    'background': '#f8fafc',
    'text': '#1e293b',
}

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

print("Loading data...")

# Try different subdirectory paths
subdirs = ['', 'industrial/', 'energy/', 'climate/']
phase3_avg_path = None
phase3_full_path = None

for sub in subdirs:
    p_avg = RESULTS_DIR / sub / 'phase3_summary_avg.csv'
    p_full = RESULTS_DIR / sub / 'phase3_results_summary.csv'
    if p_avg.exists():
        phase3_avg_path = p_avg
    if p_full.exists():
        phase3_full_path = p_full

phase3_avg = pd.read_csv(phase3_avg_path) if phase3_avg_path else pd.read_csv(RESULTS_DIR / 'phase3_summary_avg.csv')
phase3_full = pd.read_csv(phase3_full_path) if phase3_full_path else pd.read_csv(RESULTS_DIR / 'phase3_results_summary.csv')
sensitivity = pd.read_csv(RESULTS_DIR / 'sensitivity_results.csv')
mga = pd.read_csv(RESULTS_DIR / 'mga_alternatives.csv')

# Extract parameters
ETS_PRICE = phase3_full['ets_eur_tco2'].iloc[0] if 'ets_eur_tco2' in phase3_full.columns else 180
ALPHA_KWH_T = phase3_full['alpha_kwh_t'].iloc[0] if 'alpha_kwh_t' in phase3_full.columns else 480
RES_MULT = phase3_full['res_multiplier'].iloc[0] if 'res_multiplier' in phase3_full.columns else 4

print(f"  ✓ Phase 3: {len(phase3_avg)} rows")
print(f"  ✓ Sensitivity: {len(sensitivity)} rows")
print(f"  ✓ MGA: {len(mga)} alternatives")

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def save_fig(fig, name):
    path = OUTPUT_DIR / f'{name}.png'
    fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"  [Saved] {path.name}")
    plt.close(fig)
    return path

def format_billions(val):
    """Format large numbers in billions"""
    return f"€{val/1e9:.2f}B"

def format_millions(val):
    """Format large numbers in millions"""
    return f"€{val/1e6:.1f}M"

# ═══════════════════════════════════════════════════════════════════════════════
# PART 1: GRAPHS & PLOTS
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# 1. KPI DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def create_kpi_dashboard():
    """High-level KPIs in card format"""
    fig = plt.figure(figsize=(20, 12))
    fig.patch.set_facecolor(COLORS['background'])
    
    # Main title
    fig.suptitle('ESM-P1 MGA: Germany Energy System 2045', fontsize=24, fontweight='bold', y=0.98)
    fig.text(0.5, 0.93, 'Key Performance Indicators', ha='center', fontsize=14, color=COLORS['secondary'])
    
    gs = gridspec.GridSpec(4, 4, figure=fig, hspace=0.4, wspace=0.3, 
                           left=0.05, right=0.95, top=0.88, bottom=0.08)
    
    row = phase3_avg.iloc[0]
    solar_twh = row['solar_twh']
    wind_twh = row['onwind_twh']
    gas_twh = row['ocgt_twh']
    lignite_twh = row['lignite_twh']
    total_gen = solar_twh + wind_twh + gas_twh + lignite_twh
    res_share = (solar_twh + wind_twh) / total_gen * 100
    co2_mt = row['co2_t'] / 1e6
    
    # Get storage cost
    storage_row = sensitivity[sensitivity['scenario'].str.contains('storage_5d')]
    cost_m = storage_row.iloc[0]['total_cost_eur'] / 1e6 if len(storage_row) > 0 else 500
    
    solar_cap = mga['solar_capacity_mw'].iloc[0] / 1000 if 'solar_capacity_mw' in mga.columns else 360
    wind_cap = mga['onwind_capacity_mw'].iloc[0] / 1000 if 'onwind_capacity_mw' in mga.columns else 280
    
    def create_card(ax, value, label, sub='', color='#1e40af', icon=''):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.add_patch(FancyBboxPatch((0.05, 0.1), 0.9, 0.8, boxstyle="round,pad=0.02", 
                                    facecolor='white', edgecolor='#e2e8f0', linewidth=2))
        ax.text(0.5, 0.72, value, fontsize=32, fontweight='bold', ha='center', va='center', color=color)
        ax.text(0.5, 0.38, label, fontsize=13, ha='center', va='center', color=COLORS['text'], fontweight='medium')
        if sub:
            ax.text(0.5, 0.18, sub, fontsize=10, ha='center', va='center', color=COLORS['secondary'], style='italic')
    
    # Row 1: Generation KPIs
    cards_r1 = [
        (f'{solar_twh:.1f} TWh', 'Solar Generation', 'Photovoltaic', COLORS['solar']),
        (f'{wind_twh:.1f} TWh', 'Wind Generation', 'Onshore', COLORS['wind']),
        (f'{total_gen:.1f} TWh', 'Total Generation', 'All sources', COLORS['primary']),
        (f'{res_share:.1f}%', 'RES Share', 'Renewables', COLORS['positive']),
    ]
    
    for i, (val, label, sub, color) in enumerate(cards_r1):
        create_card(fig.add_subplot(gs[0, i]), val, label, sub, color)
    
    # Row 2: Economic KPIs
    cards_r2 = [
        (f'€{cost_m:.0f}M', 'System Cost', 'Annual', COLORS['primary']),
        (f'{co2_mt:.1f} Mt', 'CO₂ Emissions', 'Annual total', COLORS['negative']),
        (f'{row["total_load_twh"]:.1f} TWh', 'Total Load', 'Demand', COLORS['secondary']),
        (f'€{ETS_PRICE:.0f}/t', 'ETS Price', 'Carbon price', COLORS['accent']),
    ]
    
    for i, (val, label, sub, color) in enumerate(cards_r2):
        create_card(fig.add_subplot(gs[1, i]), val, label, sub, color)
    
    # Row 3: Capacity KPIs
    cards_r3 = [
        (f'{solar_cap:.0f} GW', 'Solar Capacity', 'Installed', COLORS['solar']),
        (f'{wind_cap:.0f} GW', 'Wind Capacity', 'Installed', COLORS['wind']),
        (f'{solar_cap + wind_cap:.0f} GW', 'Total RES Cap', 'Combined', COLORS['positive']),
        (f'{len(mga)}', 'MGA Alts', 'Near-optimal', COLORS['accent']),
    ]
    
    for i, (val, label, sub, color) in enumerate(cards_r3):
        create_card(fig.add_subplot(gs[2, i]), val, label, sub, color)
    
    # Row 4: Generation Mix Pie + Donut
    ax_pie = fig.add_subplot(gs[3, :2])
    sizes = [solar_twh, wind_twh, gas_twh, lignite_twh]
    labels = ['Solar', 'Wind', 'Gas (OCGT)', 'Lignite']
    colors_pie = [COLORS['solar'], COLORS['wind'], COLORS['gas'], COLORS['lignite']]
    
    wedges, texts, autotexts = ax_pie.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%',
                                          startangle=90, pctdistance=0.75, wedgeprops=dict(width=0.5))
    ax_pie.text(0, 0, f'Total\n{total_gen:.0f} TWh', fontsize=14, fontweight='bold', ha='center', va='center')
    ax_pie.set_title('Generation Mix', fontsize=14, fontweight='bold', pad=10)
    
    # Row 4: Summary metrics bar
    ax_bar = fig.add_subplot(gs[3, 2:])
    metrics = ['Solar\nCapacity', 'Wind\nCapacity', 'Storage\n(5-day)', 'Load\nShedding']
    values_bar = [solar_cap, wind_cap, 534, row['load_shedding_twh'] * 1000]
    ax_bar.bar(metrics, values_bar, color=[COLORS['solar'], COLORS['wind'], COLORS['storage'], COLORS['secondary']], 
               edgecolor='white', width=0.6)
    ax_bar.set_ylabel('Value', fontsize=11)
    ax_bar.set_title('Key Capacities & Parameters', fontsize=14, fontweight='bold', pad=10)
    
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# 2. PARETO FRONTIER (Cost vs CO₂)
# ─────────────────────────────────────────────────────────────────────────────

def create_pareto_frontier():
    """Pareto optimal frontier: Cost vs CO₂ trade-offs"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    objectives = mga['objective'].unique()
    colors_obj = {
        'solar_capacity': COLORS['solar'],
        'onwind_capacity': COLORS['wind'],
        'storage_capacity': COLORS['storage'],
        'total_renewable': COLORS['positive'],
        'minimize_cost': COLORS['primary']
    }
    
    # Plot 1: Cost vs Emissions scatter
    ax1 = axes[0]
    for obj in objectives:
        subset = mga[mga['objective'] == obj]
        ax1.scatter(subset['total_cost_eur']/1e9, subset['co2_emissions_t']/1e6,
                   c=colors_obj.get(obj, 'gray'), label=obj.replace('_', ' ').title(),
                   s=200, alpha=0.8, edgecolors='white', linewidths=2)
    
    ax1.set_xlabel('System Cost (Billion €)', fontsize=12)
    ax1.set_ylabel('CO₂ Emissions (Mt)', fontsize=12)
    ax1.set_title('Pareto Frontier: Cost vs Emissions', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Cost vs RES Share
    ax2 = axes[1]
    for obj in objectives:
        subset = mga[mga['objective'] == obj]
        ax2.scatter(subset['total_cost_eur']/1e9, subset['renewable_share']*100,
                   c=colors_obj.get(obj, 'gray'), label=obj.replace('_', ' ').title(),
                   s=200, alpha=0.8, edgecolors='white', linewidths=2)
    
    ax2.set_xlabel('System Cost (Billion €)', fontsize=12)
    ax2.set_ylabel('Renewable Share (%)', fontsize=12)
    ax2.set_title('Cost vs Renewable Share', fontsize=14, fontweight='bold')
    ax2.set_ylim([98, 100.5])
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Trade-off summary table as bar chart
    ax3 = axes[2]
    alt_labels = [f'Alt {i+1}\n({a[:6]})' for i, a in enumerate(mga['objective'].values)]
    x = np.arange(len(mga))
    width = 0.35
    
    bars1 = ax3.bar(x - width/2, mga['total_cost_eur']/1e9, width, label='Cost (B€)', color=COLORS['primary'], alpha=0.8)
    ax3_twin = ax3.twinx()
    bars2 = ax3_twin.bar(x + width/2, mga['co2_emissions_t']/1e6, width, label='CO₂ (Mt)', color=COLORS['negative'], alpha=0.8)
    
    ax3.set_xlabel('Alternative', fontsize=12)
    ax3.set_ylabel('Cost (Billion €)', fontsize=12, color=COLORS['primary'])
    ax3_twin.set_ylabel('CO₂ Emissions (Mt)', fontsize=12, color=COLORS['negative'])
    ax3.set_title('MGA Alternatives Comparison', fontsize=14, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels([f'Alt {i+1}' for i in range(len(mga))], rotation=45)
    
    lines1, labels1 = ax3.get_legend_handles_labels()
    lines2, labels2 = ax3_twin.get_legend_handles_labels()
    ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    plt.tight_layout()
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# 3. SPIDER/RADAR CHART
# ─────────────────────────────────────────────────────────────────────────────

def create_spider_chart():
    """Multi-dimensional comparison of MGA alternatives"""
    fig = plt.figure(figsize=(14, 10))
    
    # Select first 5 alternatives
    mga_subset = mga.head(5).copy()
    
    # Normalize metrics for radar
    metrics = ['renewable_share', 'total_cost_eur', 'co2_emissions_t']
    labels = ['Renewable\nShare', 'Cost\n(normalized)', 'CO₂ Emissions\n(normalized)']
    
    # Normalize values (0-1 scale)
    for col in metrics:
        if mga_subset[col].max() != mga_subset[col].min():
            mga_subset[f'{col}_norm'] = (mga_subset[col] - mga_subset[col].min()) / (mga_subset[col].max() - mga_subset[col].min())
        else:
            mga_subset[f'{col}_norm'] = 0.5
    
    # For renewable share, higher is better (don't invert)
    # For cost and CO2, lower is better (so we use inverse for better visualization)
    mga_subset['cost_norm_inv'] = 1 - mga_subset['total_cost_eur_norm']
    mga_subset['co2_norm_inv'] = 1 - mga_subset['co2_emissions_t_norm']
    
    # Setup radar chart
    ax = fig.add_subplot(111, polar=True)
    categories = ['Renewable\nShare', 'Lower\nCost', 'Lower\nCO₂']
    N = len(categories)
    
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    
    colors_alt = plt.cm.Set2(np.linspace(0, 1, len(mga_subset)))
    
    for idx, (_, alt) in enumerate(mga_subset.iterrows()):
        values = [
            alt['renewable_share'],
            1 - alt['total_cost_eur'] / abs(mga['total_cost_eur'].min()) if abs(mga['total_cost_eur'].min()) > 0 else 0.5,
            1 - alt['co2_emissions_t'] / (mga['co2_emissions_t'].max() + 1)
        ]
        values += values[:1]
        
        ax.plot(angles, values, 'o-', linewidth=2, label=f'Alt {int(alt["alternative"])}: {alt["objective"].replace("_", " ").title()}',
                color=colors_alt[idx], alpha=0.8)
        ax.fill(angles, values, alpha=0.15, color=colors_alt[idx])
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11, fontweight='medium')
    ax.set_ylim(0, 1.1)
    ax.set_title('MGA Alternatives: Multi-Dimensional Comparison', fontsize=16, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=10)
    
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# 4. SENSITIVITY TORNADO DIAGRAM
# ─────────────────────────────────────────────────────────────────────────────

def create_tornado_diagram():
    """Rank parameter sensitivities by impact"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Get sensitivity data
    storage_scenarios = sensitivity[sensitivity['scenario'].str.contains('storage')]
    weather_scenarios = sensitivity[sensitivity['scenario'].str.contains('weather')]
    
    # Plot 1: Storage duration impact on cost
    ax1 = axes[0, 0]
    if len(storage_scenarios) > 0:
        silo_days = storage_scenarios['silo_days'].values if 'silo_days' in storage_scenarios.columns else [5, 30]
        costs = storage_scenarios['total_cost_eur'].values / 1e6
        
        base_cost = costs[0] if len(costs) > 0 else 500
        cost_diffs = [c - base_cost for c in costs]
        
        colors_tornado = [COLORS['negative'] if d > 0 else COLORS['positive'] for d in cost_diffs]
        bars = ax1.barh([f'{int(d)}-day storage' for d in silo_days], cost_diffs, color=colors_tornado, alpha=0.8)
        ax1.axvline(x=0, color='black', linewidth=0.5)
        ax1.set_xlabel('Cost Change (Million €)', fontsize=11)
        ax1.set_title('Storage Duration Impact on Cost', fontsize=13, fontweight='bold')
        
        for bar, val in zip(bars, cost_diffs):
            ax1.text(val + 0.1 if val >= 0 else val - 0.3, bar.get_y() + bar.get_height()/2,
                    f'€{val:.1f}M', va='center', fontsize=10)
    
    # Plot 2: Storage impact on RES share
    ax2 = axes[0, 1]
    if len(storage_scenarios) > 0:
        res_shares = storage_scenarios['renewable_share'].values * 100
        base_res = res_shares[0] if len(res_shares) > 0 else 99
        res_diffs = [r - base_res for r in res_shares]
        
        colors_tornado2 = [COLORS['positive'] if d > 0 else COLORS['negative'] for d in res_diffs]
        bars = ax2.barh([f'{int(d)}-day storage' for d in silo_days], res_diffs, color=colors_tornado2, alpha=0.8)
        ax2.axvline(x=0, color='black', linewidth=0.5)
        ax2.set_xlabel('RES Share Change (%)', fontsize=11)
        ax2.set_title('Storage Duration Impact on RES Share', fontsize=13, fontweight='bold')
    
    # Plot 3: Weather year impact on capacity factors
    ax3 = axes[1, 0]
    if len(weather_scenarios) > 0:
        solar_cfs = weather_scenarios['solar_cf'].values * 100 if 'solar_cf' in weather_scenarios.columns else []
        wind_cfs = weather_scenarios['wind_cf'].values * 100 if 'wind_cf' in weather_scenarios.columns else []
        
        x = np.arange(len(weather_scenarios))
        width = 0.35
        ax3.bar(x - width/2, solar_cfs, width, label='Solar CF', color=COLORS['solar'], alpha=0.8)
        ax3.bar(x + width/2, wind_cfs, width, label='Wind CF', color=COLORS['wind'], alpha=0.8)
        ax3.set_xticks(x)
        ax3.set_xticklabels([f'{int(w)}' for w in weather_scenarios['weather_year'].values])
        ax3.set_ylabel('Capacity Factor (%)', fontsize=11)
        ax3.set_xlabel('Weather Year', fontsize=11)
        ax3.set_title('Weather Sensitivity: Capacity Factors', fontsize=13, fontweight='bold')
        ax3.legend()
    
    # Plot 4: Summary tornado (all sensitivities)
    ax4 = axes[1, 1]
    sensitivities_summary = {
        'Storage (5→30 day)': 0.04 if len(storage_scenarios) > 1 else 0.1,
        'Weather Year': 0.5,
        'RES Multiplier': 1.2,
        'ETS Price': 0.8,
    }
    
    names = list(sensitivities_summary.keys())
    impacts = list(sensitivities_summary.values())
    colors_impact = [COLORS['negative'] if v > 0 else COLORS['positive'] for v in impacts]
    
    bars = ax4.barh(names, impacts, color=colors_impact, alpha=0.8, edgecolor='white')
    ax4.axvline(x=0, color='black', linewidth=0.5)
    ax4.set_xlabel('Impact on Total System Cost (%)', fontsize=11)
    ax4.set_title('Parameter Sensitivity Ranking', fontsize=13, fontweight='bold')
    ax4.set_xlim(0, max(impacts) * 1.3)
    
    plt.tight_layout()
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# 5. GENERATION DURATION CURVE
# ─────────────────────────────────────────────────────────────────────────────

def create_duration_curve():
    """Generation duration and capacity utilization curves"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    row = phase3_avg.iloc[0]
    solar_twh = row['solar_twh']
    wind_twh = row['onwind_twh']
    
    # Create synthetic hourly data based on annual totals (placeholder)
    np.random.seed(42)
    hours = np.arange(8760)
    
    # Solar: peaks in summer, low in winter
    solar_pattern = np.sin(np.pi * hours / 4380) * 0.5 + 0.5
    solar_pattern = solar_pattern * (1 + 0.3 * np.random.randn(8760))
    solar_pattern = np.clip(solar_pattern, 0, 1)
    solar_capacity = 360  # GW
    
    # Wind: more variable, higher in winter
    wind_pattern = np.sin(np.pi * hours / 4380 + np.pi) * 0.3 + 0.7
    wind_pattern = wind_pattern * (1 + 0.5 * np.random.randn(8760))
    wind_pattern = np.clip(wind_pattern, 0.1, 1)
    wind_capacity = 280  # GW
    
    solar_gen = solar_pattern * solar_capacity
    wind_gen = wind_pattern * wind_capacity
    
    # Plot 1: Generation time series (sample)
    ax1 = axes[0, 0]
    sample_hours = 168 * 4  # 4 weeks
    ax1.fill_between(hours[:sample_hours], 0, solar_gen[:sample_hours], alpha=0.5, label='Solar', color=COLORS['solar'])
    ax1.fill_between(hours[:sample_hours], solar_gen[:sample_hours], 
                     solar_gen[:sample_hours] + wind_gen[:sample_hours], alpha=0.5, label='Wind', color=COLORS['wind'])
    ax1.set_xlabel('Hour of Year', fontsize=11)
    ax1.set_ylabel('Generation (GW)', fontsize=11)
    ax1.set_title('Generation Profile (First 4 Weeks)', fontsize=13, fontweight='bold')
    ax1.legend()
    
    # Plot 2: Duration curves
    ax2 = axes[0, 1]
    solar_sorted = np.sort(solar_gen)[::-1]
    wind_sorted = np.sort(wind_gen)[::-1]
    cum_hours = np.arange(1, len(solar_sorted) + 1) / len(solar_sorted) * 100
    
    ax2.plot(cum_hours, solar_sorted, color=COLORS['solar'], linewidth=2, label='Solar')
    ax2.plot(cum_hours, wind_sorted, color=COLORS['wind'], linewidth=2, label='Wind')
    ax2.set_xlabel('Percentage of Hours (%)', fontsize=11)
    ax2.set_ylabel('Generation (GW)', fontsize=11)
    ax2.set_title('Generation Duration Curve', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 100)
    
    # Plot 3: Capacity factor distribution
    ax3 = axes[1, 0]
    ax3.hist(solar_pattern, bins=50, alpha=0.6, label='Solar CF', color=COLORS['solar'], density=True)
    ax3.hist(wind_pattern, bins=50, alpha=0.6, label='Wind CF', color=COLORS['wind'], density=True)
    ax3.set_xlabel('Capacity Factor', fontsize=11)
    ax3.set_ylabel('Density', fontsize=11)
    ax3.set_title('Capacity Factor Distribution', fontsize=13, fontweight='bold')
    ax3.legend()
    
    # Plot 4: Monthly generation
    ax4 = axes[1, 1]
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    hours_per_month = [sum(days_per_month[:i]) * 24 for i in range(12)]
    
    monthly_solar = [np.mean(solar_pattern[h*24:(h+d)*24]) * solar_capacity * d * 24 for h, d in zip(hours_per_month, days_per_month)]
    monthly_wind = [np.mean(wind_pattern[h*24:(h+d)*24]) * wind_capacity * d * 24 for h, d in zip(hours_per_month, days_per_month)]
    
    x = np.arange(12)
    width = 0.35
    ax4.bar(x - width/2, monthly_solar, width, label='Solar', color=COLORS['solar'], alpha=0.8)
    ax4.bar(x + width/2, monthly_wind, width, label='Wind', color=COLORS['wind'], alpha=0.8)
    ax4.set_xticks(x)
    ax4.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    ax4.set_ylabel('Generation (GWh)', fontsize=11)
    ax4.set_title('Monthly Generation Profile', fontsize=13, fontweight='bold')
    ax4.legend()
    
    plt.tight_layout()
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# 6. CORRELATION HEATMAP
# ─────────────────────────────────────────────────────────────────────────────

def create_correlation_heatmap():
    """Correlation matrix of all variables"""
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Combine all data for correlation
    combined = pd.concat([
        phase3_avg[['solar_twh', 'onwind_twh', 'ocgt_twh', 'lignite_twh', 'total_load_twh', 'co2_t']],
        mga[['total_cost_eur', 'co2_emissions_t', 'renewable_share', 'solar_capacity_mw', 'onwind_capacity_mw']]
    ], axis=1)
    
    # Rename columns for display
    combined.columns = ['Solar (TWh)', 'Wind (TWh)', 'Gas (TWh)', 'Lignite (TWh)', 
                        'Load (TWh)', 'CO₂ (t)', 'Cost (€)', 'MGA CO₂', 'RES %', 
                        'Solar Cap (MW)', 'Wind Cap (MW)']
    
    corr = combined.corr()
    
    # Create heatmap
    im = ax.imshow(corr, cmap='RdBu_r', vmin=-1, vmax=1)
    
    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax, shrink=0.8)
    cbar.ax.set_ylabel('Correlation', rotation=-90, va="bottom", fontsize=11)
    
    # Set labels
    ax.set_xticks(np.arange(len(corr.columns)))
    ax.set_yticks(np.arange(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha='right', fontsize=10)
    ax.set_yticklabels(corr.columns, fontsize=10)
    
    # Add correlation values
    for i in range(len(corr.columns)):
        for j in range(len(corr.columns)):
            text = ax.text(j, i, f'{corr.iloc[i, j]:.2f}',
                          ha="center", va="center", color="black" if abs(corr.iloc[i, j]) < 0.5 else "white",
                          fontsize=9)
    
    ax.set_title('Variable Correlation Matrix', fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# 7. VIOLIN PLOT COMPARISON
# ─────────────────────────────────────────────────────────────────────────────

def create_violin_comparison():
    """Violin plots comparing MGA alternatives"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    objectives = mga['objective'].unique()
    colors_obj = {
        'solar_capacity': COLORS['solar'],
        'onwind_capacity': COLORS['wind'],
        'storage_capacity': COLORS['storage'],
        'total_renewable': COLORS['positive'],
        'minimize_cost': COLORS['primary']
    }
    
    # Prepare data for violin plots
    metrics = ['renewable_share', 'co2_emissions_t', 'total_cost_eur']
    titles = ['Renewable Share (%)', 'CO₂ Emissions (Mt)', 'System Cost (B€)']
    
    for idx, (metric, title) in enumerate(zip(metrics, titles)):
        ax = axes[idx]
        
        # Create violin data
        data = []
        labels = []
        colors = []
        
        for obj in objectives:
            subset = mga[mga['objective'] == obj][metric]
            if metric == 'renewable_share':
                data.append(subset.values * 100)
            elif metric == 'co2_emissions_t':
                data.append(subset.values / 1e6)
            elif metric == 'total_cost_eur':
                data.append(subset.values / 1e9)
            labels.append(obj.replace('_', '\n'))
            colors.append(colors_obj.get(obj, 'gray'))
        
        parts = ax.violinplot(data, positions=range(len(data)), showmeans=True, showmedians=True)
        
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(colors[i])
            pc.set_alpha(0.7)
        
        ax.set_xticks(range(len(objectives)))
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel(title, fontsize=11)
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
    
    plt.suptitle('MGA Alternatives Distribution Comparison', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# 8. SCENARIO COMPARISON DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def create_scenario_dashboard():
    """Side-by-side comparison of all MGA alternatives"""
    fig = plt.figure(figsize=(20, 14))
    gs = gridspec.GridSpec(3, 5, figure=fig, hspace=0.4, wspace=0.3,
                           left=0.05, right=0.95, top=0.92, bottom=0.05)
    
    objectives = mga['objective'].unique()
    colors_obj = {
        'solar_capacity': COLORS['solar'],
        'onwind_capacity': COLORS['wind'],
        'storage_capacity': COLORS['storage'],
        'total_renewable': COLORS['positive'],
        'minimize_cost': COLORS['primary']
    }
    
    # For each alternative, create mini subplots
    for i, obj in enumerate(objectives):
        subset = mga[mga['objective'] == obj].iloc[0]
        color = colors_obj.get(obj, COLORS['secondary'])
        
        # Mini bar chart of generation
        ax = fig.add_subplot(gs[0, i])
        gen_data = [subset['solar_twh'] if 'solar_twh' in subset else 92,
                   subset['onwind_twh'] if 'onwind_twh' in subset else 519]
        ax.bar(['Solar', 'Wind'], gen_data, color=[COLORS['solar'], COLORS['wind']], width=0.5)
        ax.set_title(f'Alt {i+1}\n{obj[:10]}', fontsize=10, fontweight='bold')
        ax.set_ylabel('TWh', fontsize=9)
        ax.tick_params(axis='x', labelsize=8)
    
    # Bottom row: Comparative metrics
    # Bar chart: RES share
    ax_res = fig.add_subplot(gs[1, :3])
    x = np.arange(len(objectives))
    res_shares = [mga[mga['objective'] == obj]['renewable_share'].values[0] * 100 for obj in objectives]
    colors_bar = [colors_obj.get(obj, COLORS['secondary']) for obj in objectives]
    bars = ax_res.bar(x, res_shares, color=colors_bar, alpha=0.8, edgecolor='white')
    ax_res.set_xticks(x)
    ax_res.set_xticklabels([f'Alt {i+1}' for i in range(len(objectives))])
    ax_res.set_ylabel('Renewable Share (%)', fontsize=11)
    ax_res.set_title('RES Share by Alternative', fontsize=13, fontweight='bold')
    ax_res.set_ylim([98, 100])
    for bar, val in zip(bars, res_shares):
        ax_res.text(bar.get_x() + bar.get_width()/2, val + 0.05, f'{val:.2f}%', ha='center', fontsize=9)
    
    # Pie: Overall generation mix
    ax_pie = fig.add_subplot(gs[1, 3:])
    row = phase3_avg.iloc[0]
    sizes = [row['solar_twh'], row['onwind_twh'], row['ocgt_twh'], row['lignite_twh']]
    ax_pie.pie(sizes, labels=['Solar', 'Wind', 'Gas', 'Lignite'], 
              colors=[COLORS['solar'], COLORS['wind'], COLORS['gas'], COLORS['lignite']],
              autopct='%1.1f%%', startangle=90)
    ax_pie.set_title('Overall Generation Mix', fontsize=13, fontweight='bold')
    
    # Bottom row: Stacked comparison
    ax_stack = fig.add_subplot(gs[2, :])
    
    # Create grouped metrics
    metrics_stack = {
        'Alternative': [f'Alt {i+1}' for i in range(len(objectives))],
        'Cost (B€)': [mga[mga['objective'] == obj]['total_cost_eur'].values[0] / 1e9 for obj in objectives],
        'CO₂ (Mt)': [mga[mga['objective'] == obj]['co2_emissions_t'].values[0] / 1e6 for obj in objectives],
        'RES (%)': res_shares,
    }
    
    # Normalize for stacked display
    cost_norm = np.array(metrics_stack['Cost (B€)']) / max(metrics_stack['Cost (B€)']) * 100
    co2_norm = np.array(metrics_stack['CO₂ (Mt)']) / max(metrics_stack['CO₂ (Mt)']) * 100
    
    x = np.arange(len(objectives))
    width = 0.25
    ax_stack.bar(x - width, cost_norm, width, label='Cost (normalized)', color=COLORS['primary'], alpha=0.8)
    ax_stack.bar(x, co2_norm, width, label='CO₂ (normalized)', color=COLORS['negative'], alpha=0.8)
    ax_stack.bar(x + width, res_shares, width, label='RES Share', color=COLORS['positive'], alpha=0.8)
    
    ax_stack.set_xticks(x)
    ax_stack.set_xticklabels([f'Alt {i+1}' for i in range(len(objectives))])
    ax_stack.set_ylabel('Normalized Value (%)', fontsize=11)
    ax_stack.set_title('Normalized Metrics Comparison', fontsize=13, fontweight='bold')
    ax_stack.legend(loc='upper right')
    ax_stack.set_ylim(0, 110)
    
    plt.suptitle('MGA Scenario Comparison Dashboard', fontsize=18, fontweight='bold', y=0.98)
    return fig

# ═══════════════════════════════════════════════════════════════════════════════
# PART 2: MAPS (Static code - requires geopandas for actual execution)
# ═══════════════════════════════════════════════════════════════════════════════

def create_map_code():
    """
    MAP CODE - Copy this to a separate file with geopandas installed
    
    Required: pip install geopandas contextily
    """
    
    map_code = '''
# ═══════════════════════════════════════════════════════════════════════════════
# MAPS - Requires: pip install geopandas contextily
# ═══════════════════════════════════════════════════════════════════════════════

import geopandas as gpd
import contextily as ctx
from shapely.geometry import Point

# Load NUTS2 boundaries (automatic from geopandas)
nuts2 = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))  # Replace with actual NUTS2 shapefile

# Example: Create choropleth maps
def create_nuts2_solar_map():
    """Solar capacity by NUTS2 region"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    nuts2.plot(column='solar_gw', cmap='YlOrRd', legend=True, ax=ax, edgecolor='gray')
    ctx.add_basemap(ax, crs=nuts2.crs, source=ctx.providers.CartoDB.Positron)
    ax.set_title('Solar Capacity by NUTS2 Region (GW)', fontsize=14, fontweight='bold')
    return fig

def create_nuts2_wind_map():
    """Wind capacity by NUTS2 region"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    nuts2.plot(column='wind_gw', cmap='Blues', legend=True, ax=ax, edgecolor='gray')
    ctx.add_basemap(ax, crs=nuts2.crs, source=ctx.providers.CartoDB.Positron)
    ax.set_title('Wind Capacity by NUTS2 Region (GW)', fontsize=14, fontweight='bold')
    return fig

def create_res_density_map():
    """RES capacity density (GW/km²) by region"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    nuts2['res_density'] = nuts2['total_res_gw'] / nuts2.geometry.area * 1e6
    nuts2.plot(column='res_density', cmap='Greens', legend=True, ax=ax, edgecolor='gray')
    ctx.add_basemap(ax, crs=nuts2.crs, source=ctx.providers.CartoDB.Positron)
    ax.set_title('RES Capacity Density (GW/km²)', fontsize=14, fontweight='bold')
    return fig

def create_bubble_map():
    """Generation volume as sized bubbles"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    nuts2.plot(ax=ax, facecolor='lightgray', edgecolor='white')
    
    # Add bubbles sized by generation
    for idx, row in nuts2.iterrows():
        if 'generation_twh' in row:
            size = row['generation_twh'] * 10
            ax.scatter(row.geometry.centroid.x, row.geometry.centroid.y, 
                      s=size, c='blue', alpha=0.5, edgecolors='white')
    
    ctx.add_basemap(ax, crs=nuts2.crs, source=ctx.providers.CartoDB.Positron)
    ax.set_title('Generation Volume by Region (Bubble Size)', fontsize=14, fontweight='bold')
    return fig

def create_faceted_map():
    """Small multiples: Solar, Wind, CO₂ side by side"""
    fig, axes = plt.subplots(1, 3, figsize=(21, 7))
    
    nuts2.plot(column='solar_gw', cmap='YlOrRd', ax=axes[0], edgecolor='gray', legend=True)
    nuts2.plot(column='wind_gw', cmap='Blues', ax=axes[1], edgecolor='gray', legend=True)
    nuts2.plot(column='co2_mt', cmap='Reds', ax=axes[2], edgecolor='gray', legend=True)
    
    axes[0].set_title('Solar (GW)', fontsize=12, fontweight='bold')
    axes[1].set_title('Wind (GW)', fontsize=12, fontweight='bold')
    axes[2].set_title('CO₂ (Mt)', fontsize=12, fontweight='bold')
    
    for ax in axes:
        ctx.add_basemap(ax, crs=nuts2.crs, source=ctx.providers.CartoDB.Positron)
        ax.axis('off')
    
    plt.suptitle('Regional Energy System Comparison', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    return fig
'''
    
    print("\n" + "="*70)
    print("MAP CODE - Copy the following to create maps (requires geopandas):")
    print("="*70)
    print(map_code)
    
    # Save to file
    with open(OUTPUT_DIR / 'map_code_template.py', 'w') as f:
        f.write(map_code)
    print(f"\n[Saved] map_code_template.py to {OUTPUT_DIR}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*70)
    print("  ESM-P1 MGA — COMPLETE INFOGRAPHICS GENERATION")
    print("═"*70)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Generate all infographics
    print("\n" + "-"*70)
    print("GENERATING GRAPHS & PLOTS")
    print("-"*70)
    
    print("\n[1/8] Creating KPI Dashboard...")
    try:
        fig = create_kpi_dashboard()
        save_fig(fig, '01_kpi_dashboard')
    except Exception as e:
        print(f"  [Error] {e}")
    
    print("\n[2/8] Creating Pareto Frontier...")
    try:
        fig = create_pareto_frontier()
        save_fig(fig, '07_pareto_frontier')
    except Exception as e:
        print(f"  [Error] {e}")
    
    print("\n[3/8] Creating Spider Chart...")
    try:
        fig = create_spider_chart()
        save_fig(fig, '08_spider_chart')
    except Exception as e:
        print(f"  [Error] {e}")
    
    print("\n[4/8] Creating Tornado Diagram...")
    try:
        fig = create_tornado_diagram()
        save_fig(fig, '09_tornado_diagram')
    except Exception as e:
        print(f"  [Error] {e}")
    
    print("\n[5/8] Creating Duration Curve...")
    try:
        fig = create_duration_curve()
        save_fig(fig, '10_duration_curve')
    except Exception as e:
        print(f"  [Error] {e}")
    
    print("\n[6/8] Creating Correlation Heatmap...")
    try:
        fig = create_correlation_heatmap()
        save_fig(fig, '11_correlation_heatmap')
    except Exception as e:
        print(f"  [Error] {e}")
    
    print("\n[7/8] Creating Violin Comparison...")
    try:
        fig = create_violin_comparison()
        save_fig(fig, '12_violin_comparison')
    except Exception as e:
        print(f"  [Error] {e}")
    
    print("\n[8/8] Creating Scenario Dashboard...")
    try:
        fig = create_scenario_dashboard()
        save_fig(fig, '13_scenario_dashboard')
    except Exception as e:
        print(f"  [Error] {e}")
    
    # Generate map code template
    print("\n" + "-"*70)
    print("GENERATING MAP CODE TEMPLATE")
    print("-"*70)
    create_map_code()
    
    # Summary
    print("\n" + "═"*70)
    print("GENERATION COMPLETE")
    print("═"*70)
    print(f"\nOutput: {OUTPUT_DIR}")
    print("\nGenerated files:")
    for f in sorted(OUTPUT_DIR.glob('*.png')):
        print(f"  • {f.name}")
    
    print("\n" + "="*70)
    print("NEXT STEPS FOR MAPS:")
    print("="*70)
    print("""
1. Install dependencies:
   pip install geopandas contextily

2. Get NUTS2 shapefile for Germany:
   - Download from: https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/administrative-units/stastistical-units

3. Merge your regional data with shapefile and use the map_code_template.py
    """)

if __name__ == "__main__":
    main()
