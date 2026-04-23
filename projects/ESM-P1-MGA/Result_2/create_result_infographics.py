"""
ESM-P1 MGA — RESULT INFOGRAPHICS GENERATOR
For: ESM-P1- MGA/Result_2/

KEY FINDINGS:
- Phase 3 (2045): 628.5 TWh total load, 99.7% renewable share
- Generation: 92.2 TWh solar (14.9%), 519.3 TWh wind (85.1%)
- CO2: 15.8 Mt total
- MGA: 10 alternatives showing cost-CO2 tradeoffs
- Storage sensitivity: Minimal impact (<€50k difference)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# SETUP
RESULTS_DIR = Path(__file__).parent
OUTPUT_DIR = RESULTS_DIR / 'infographics'
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
    'accent': '#6366f1',
    'background': '#f8fafc',
}

# LOAD DATA
print("Loading model results...")
phase3 = pd.read_csv(RESULTS_DIR / 'phase3_results_summary.csv')
mga = pd.read_csv(RESULTS_DIR / 'mga_alternatives.csv')
sensitivity = pd.read_csv(RESULTS_DIR / 'sensitivity_results.csv')

row = phase3.iloc[0]
SOLAR_TWH = row['solar_twh']
WIND_TWH = row['onwind_twh']
GAS_TWH = row['ocgt_twh']
LIGNITE_TWH = row['lignite_twh']
TOTAL_GEN = SOLAR_TWH + WIND_TWH + GAS_TWH + LIGNITE_TWH
TOTAL_LOAD = row['total_load_twh']
CO2_MT = row['co2_t'] / 1e6
RES_SHARE = (SOLAR_TWH + WIND_TWH) / TOTAL_GEN * 100
ETS_PRICE = row['ets_eur_tco2']
ALPHA = row['alpha_kwh_t']
SOLAR_GW, WIND_GW = 360, 280

print(f"  Key: {RES_SHARE:.1f}% renewable, {WIND_TWH:.0f} TWh wind")

# HELPER FUNCTIONS
def save_fig(fig, name):
    path = OUTPUT_DIR / f'{name}.png'
    fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"  [Saved] {path.name}")
    plt.close(fig)

def create_card(ax, value, label, sub='', color='#1e40af'):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.add_patch(FancyBboxPatch((0.05, 0.1), 0.9, 0.8, boxstyle="round,pad=0.02", 
                                facecolor='white', edgecolor='#e2e8f0', linewidth=2))
    ax.text(0.5, 0.72, value, fontsize=28, fontweight='bold', ha='center', va='center', color=color)
    ax.text(0.5, 0.38, label, fontsize=11, ha='center', va='center', color='#1e293b')
    if sub: ax.text(0.5, 0.15, sub, fontsize=9, ha='center', color='#64748b', style='italic')

# INFOGRAPHIC 1: EXECUTIVE DASHBOARD
def create_executive_dashboard():
    fig = plt.figure(figsize=(20, 14))
    fig.patch.set_facecolor(COLORS['background'])
    fig.suptitle('ESM-P1 MGA: Germany Energy System 2045 - Key Findings', fontsize=22, fontweight='bold', y=0.98)
    gs = gridspec.GridSpec(4, 4, figure=fig, hspace=0.45, wspace=0.35, left=0.05, right=0.95, top=0.90, bottom=0.05)
    
    cost_val = 271179404
    cards_r1 = [
        (f'{SOLAR_TWH:.1f} TWh', 'Solar Generation', f'{SOLAR_TWH/TOTAL_GEN*100:.1f}%', COLORS['solar']),
        (f'{WIND_TWH:.0f} TWh', 'Wind Generation', f'{WIND_TWH/TOTAL_GEN*100:.1f}%', COLORS['wind']),
        (f'{TOTAL_GEN:.0f} TWh', 'Total Generation', 'Annual', COLORS['primary']),
        (f'{RES_SHARE:.1f}%', 'Renewable Share', 'Near-100% clean', COLORS['positive']),
    ]
    for i, (val, label, sub, color) in enumerate(cards_r1):
        create_card(fig.add_subplot(gs[0, i]), val, label, sub, color)
    
    cards_r2 = [
        (f'€{cost_val/1e6:.0f}M', 'System Cost', 'Annual', COLORS['primary']),
        (f'{CO2_MT:.1f} Mt', 'CO2 Emissions', 'Process+energy', COLORS['negative']),
        (f'{TOTAL_LOAD:.0f} TWh', 'Total Load', 'Demand', COLORS['secondary']),
        (f'€{ETS_PRICE:.0f}/t', 'ETS Price', 'Carbon', COLORS['accent']),
    ]
    for i, (val, label, sub, color) in enumerate(cards_r2):
        create_card(fig.add_subplot(gs[1, i]), val, label, sub, color)
    
    cards_r3 = [
        (f'{SOLAR_GW} GW', 'Solar Cap', '', COLORS['solar']),
        (f'{WIND_GW} GW', 'Wind Cap', '', COLORS['wind']),
        (f'{SOLAR_GW+WIND_GW} GW', 'Total RES', '', COLORS['positive']),
        (f'{len(mga)}', 'MGA Alts', 'Near-optimal', COLORS['accent']),
    ]
    for i, (val, label, sub, color) in enumerate(cards_r3):
        create_card(fig.add_subplot(gs[2, i]), val, label, sub, color)
    
    ax_donut = fig.add_subplot(gs[3, :2])
    sizes = [SOLAR_TWH, WIND_TWH, GAS_TWH, LIGNITE_TWH]
    colors_pie = [COLORS['solar'], COLORS['wind'], COLORS['gas'], COLORS['lignite']]
    ax_donut.pie(sizes, labels=['Solar', 'Wind', 'Gas', 'Lignite'], colors=colors_pie, 
                autopct='%1.1f%%', startangle=90, pctdistance=0.75, wedgeprops=dict(width=0.5))
    ax_donut.text(0, 0, f'Total\n{TOTAL_GEN:.0f} TWh', fontsize=14, fontweight='bold', ha='center', va='center')
    ax_donut.set_title('Generation Mix', fontsize=13, fontweight='bold')
    
    ax_bar = fig.add_subplot(gs[3, 2:])
    techs = ['Solar', 'Wind', 'RES%', 'Cost']
    vals = [SOLAR_GW, WIND_GW, RES_SHARE, cost_val/1e6]
    bcs = [COLORS['solar'], COLORS['wind'], COLORS['positive'], COLORS['primary']]
    bars = ax_bar.bar(techs, vals, color=bcs, width=0.6)
    for bar, v in zip(bars, [f'{SOLAR_GW}G', f'{WIND_GW}G', f'{RES_SHARE:.1f}%', f'€{cost_val/1e6:.0f}M']):
        ax_bar.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, v, ha='center', fontsize=10, fontweight='bold')
    ax_bar.set_title('Key Parameters', fontsize=13, fontweight='bold')
    return fig

# INFOGRAPHIC 2: MGA TRADE-OFF ANALYSIS
def create_mga_tradeoff():
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('MGA Analysis: Near-Optimal System Alternatives', fontsize=18, fontweight='bold')
    
    obj_colors = {
        'solar_capacity': COLORS['solar'], 'onwind_capacity': COLORS['wind'],
        'storage_capacity': COLORS['storage'], 'total_renewable': COLORS['positive'],
        'minimize_cost': COLORS['primary']
    }
    
    # Cost vs CO2
    ax1 = axes[0, 0]
    for obj in mga['objective'].unique():
        subset = mga[mga['objective'] == obj]
        ax1.scatter(subset['total_cost_eur']/1e6, subset['co2_emissions_t']/1e6,
                   c=obj_colors.get(obj, 'gray'), label=obj.replace('_', ' ').title(), s=200, alpha=0.8)
    ax1.set_xlabel('Cost (M EUR)'); ax1.set_ylabel('CO2 (Mt)'); ax1.legend(fontsize=9); ax1.grid(alpha=0.3)
    ax1.set_title('Cost vs Emissions Trade-off', fontsize=13, fontweight='bold')
    
    # RES share by alt
    ax2 = axes[0, 1]
    ax2.bar(range(len(mga)), mga['renewable_share']*100, color=[obj_colors.get(o, 'gray') for o in mga['objective']])
    ax2.set_xticks(range(len(mga))); ax2.set_xticklabels([f'Alt {i+1}' for i in range(len(mga))], rotation=45)
    ax2.set_ylabel('Renewable Share (%)'); ax2.set_ylim([98, 100.2])
    ax2.set_title('RES Share by Alternative', fontsize=13, fontweight='bold')
    
    # Capacity by objective
    ax3 = axes[1, 0]
    objectives = mga['objective'].unique()
    x = np.arange(len(objectives)); w = 0.35
    solar_caps = [mga[mga['objective']==o]['solar_capacity_mw'].iloc[0]/1000 for o in objectives]
    wind_caps = [mga[mga['objective']==o]['onwind_capacity_mw'].iloc[0]/1000 for o in objectives]
    ax3.bar(x - w/2, solar_caps, w, label='Solar', color=COLORS['solar'])
    ax3.bar(x + w/2, wind_caps, w, label='Wind', color=COLORS['wind'])
    ax3.set_xticks(x); ax3.set_xticklabels([o.replace('_', '\n') for o in objectives], fontsize=9)
    ax3.set_ylabel('Capacity (GW)'); ax3.legend(); ax3.set_title('Optimal Capacity', fontsize=13, fontweight='bold')
    
    # Epsilon sensitivity
    ax4 = axes[1, 1]
    x_pos = np.arange(5)
    ax4.bar(x_pos - 0.2, mga[mga['epsilon']==0.05]['total_cost_eur']/1e6, 0.4, label='eps=5%', color=COLORS['primary'])
    ax4.bar(x_pos + 0.2, mga[mga['epsilon']==0.10]['total_cost_eur']/1e6, 0.4, label='eps=10%', color=COLORS['accent'])
    ax4.set_xticks(x_pos); ax4.set_xticklabels([f'Alt {i+1}' for i in range(5)])
    ax4.set_ylabel('Cost (M EUR)'); ax4.legend(); ax4.set_title('Slack Sensitivity', fontsize=13, fontweight='bold')
    
    plt.tight_layout(); return fig

# INFOGRAPHIC 3: DECARBONISATION PATHWAY
def create_decarbonisation_pathway():
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Germany Decarbonisation Pathway 2045', fontsize=18, fontweight='bold')
    
    # CO2 reduction
    ax1 = axes[0]
    years = ['2020\nBaseline', '2045\nModel']
    ax1.bar(years, [300, CO2_MT], color=[COLORS['secondary'], COLORS['positive']], width=0.5)
    ax1.text(0.5, 305, '300 Mt', ha='center', fontweight='bold'); ax1.text(1.5, CO2_MT+5, f'{CO2_MT:.1f} Mt', ha='center', fontweight='bold')
    ax1.set_ylabel('CO2 (Mt)'); ax1.set_title('Emissions Reduction', fontsize=14, fontweight='bold')
    ax1.annotate(f'-{(300-CO2_MT)/300*100:.0f}%', xy=(1, CO2_MT), xytext=(1.3, CO2_MT+40), fontsize=12, fontweight='bold', color=COLORS['positive'], arrowprops=dict(arrowstyle='->', color=COLORS['positive']))
    ax1.set_ylim(0, 350)
    
    # RES share growth
    ax2 = axes[1]
    ax2.bar(years, [50, RES_SHARE], color=[COLORS['secondary'], COLORS['positive']], width=0.5)
    ax2.text(0.5, 52, '50%', ha='center', fontweight='bold'); ax2.text(1.5, RES_SHARE+1, f'{RES_SHARE:.1f}%', ha='center', fontweight='bold')
    ax2.set_ylabel('Renewable Share (%)'); ax2.set_title('RES Transition', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, 110)
    
    # Generation mix
    ax3 = axes[2]
    sources = ['Solar', 'Wind', 'Gas', 'Lignite']
    vals = [SOLAR_TWH, WIND_TWH, GAS_TWH, LIGNITE_TWH]
    ax3.barh(sources, vals, color=[COLORS['solar'], COLORS['wind'], COLORS['gas'], COLORS['lignite']])
    for i, v in enumerate(vals): ax3.text(v+5, i, f'{v:.1f} TWh', va='center')
    ax3.set_xlabel('Generation (TWh)'); ax3.set_title('2045 Mix', fontsize=14, fontweight='bold')
    
    plt.tight_layout(); return fig

# INFOGRAPHIC 4: SENSITIVITY ANALYSIS
def create_sensitivity_analysis():
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Sensitivity Analysis: Key Parameter Impacts', fontsize=18, fontweight='bold')
    
    storage_s = sensitivity[sensitivity['scenario'].str.contains('storage', na=False)]
    
    # Storage cost
    ax1 = axes[0]
    if len(storage_s) > 0:
        costs = storage_s['total_cost_eur'].values / 1e6
        bars = ax1.bar([f'{int(d)}-day' for d in storage_s['silo_days'].values], costs, color=[COLORS['accent'], COLORS['primary']])
        for b, c in zip(bars, costs): ax1.text(b.get_x()+b.get_width()/2, c+1, f'€{c:.1f}M', ha='center')
        if len(costs) > 1: ax1.annotate(f'Delta: €{abs(costs[1]-costs[0])*1000:.0f}k', xy=(0.5, max(costs)), xytext=(0.5, max(costs)+10), fontsize=10, ha='center', color=COLORS['positive'])
    ax1.set_ylabel('Cost (M EUR)'); ax1.set_title('Storage Sensitivity', fontsize=14, fontweight='bold')
    
    # Weather CF
    ax2 = axes[1]
    weather = sensitivity[sensitivity['scenario'].str.contains('weather', na=False)]
    if len(weather) > 0:
        x = range(len(weather))
        ax2.bar([i-0.2 for i in x], weather['solar_cf'].values*100, 0.4, label='Solar CF', color=COLORS['solar'])
        ax2.bar([i+0.2 for i in x], weather['wind_cf'].values*100, 0.4, label='Wind CF', color=COLORS['wind'])
        ax2.set_xticks(x); ax2.set_xticklabels([f'{int(w)}' for w in weather['weather_year'].values])
        ax2.legend(); ax2.set_ylabel('Capacity Factor (%)')
    ax2.set_title('Weather Sensitivity', fontsize=14, fontweight='bold')
    
    # RES share by storage
    ax3 = axes[2]
    if len(storage_s) > 0:
        res_s = storage_s['renewable_share'].values * 100
        bars = ax3.bar([f'{int(d)}-day' for d in storage_s['silo_days'].values], res_s, color=[COLORS['accent'], COLORS['primary']])
        for b, r in zip(bars, res_s): ax3.text(b.get_x()+b.get_width()/2, r+0.1, f'{r:.2f}%', ha='center')
        ax3.set_ylim([99, 100])
    ax3.set_ylabel('RES Share (%)'); ax3.set_title('RES vs Storage', fontsize=14, fontweight='bold')
    
    plt.tight_layout(); return fig

# INFOGRAPHIC 5: SYSTEM ARCHITECTURE
def create_system_architecture():
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis('off')
    fig.suptitle('Germany Energy System Architecture 2045', fontsize=18, fontweight='bold')
    
    # Colors for components
    comp_colors = {
        'solar': COLORS['solar'], 'wind': COLORS['wind'], 'grid': COLORS['primary'],
        'industry': COLORS['accent'], 'storage': COLORS['storage'], 'gas': COLORS['gas'], 'lignite': COLORS['lignite']
    }
    
    def draw_box(ax, x, y, w, h, label, sublabel='', color='white', text_color='black'):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", facecolor=color, edgecolor='#334155', linewidth=2))
        ax.text(x + w/2, y + h*0.65, label, fontsize=12, fontweight='bold', ha='center', va='center', color=text_color)
        if sublabel: ax.text(x + w/2, y + h*0.3, sublabel, fontsize=10, ha='center', va='center', color=text_color)
    
    # Generation
    draw_box(ax, 0.5, 7, 2.5, 1.5, 'SOLAR', f'{SOLAR_GW} GW', comp_colors['solar'], 'white')
    draw_box(ax, 0.5, 5, 2.5, 1.5, 'WIND', f'{WIND_GW} GW', comp_colors['wind'], 'white')
    draw_box(ax, 0.5, 3, 2.5, 1.5, 'GAS', f'{GAS_TWH:.1f} TWh', comp_colors['gas'], 'white')
    draw_box(ax, 0.5, 1, 2.5, 1.5, 'LIGNITE', f'{LIGNITE_TWH:.1f} TWh', comp_colors['lignite'], 'white')
    
    # Grid and Industry
    draw_box(ax, 4, 4, 2.5, 3, 'GRID', f'{TOTAL_LOAD:.0f} TWh\n{RES_SHARE:.1f}% Clean', comp_colors['grid'], 'white')
    draw_box(ax, 7.5, 4, 2.5, 3, 'CEMENT\nINDUSTRY', f'{ALPHA:.0f} kWh/t\n28 Mt/yr', comp_colors['industry'], 'white')
    draw_box(ax, 4, 0.5, 2.5, 1.5, 'STORAGE', f'5-day silo\n534,000 t', comp_colors['storage'], 'white')
    
    # Arrows
    for start_y, color in [(8, comp_colors['solar']), (6, comp_colors['wind']), (4, comp_colors['gas'])]:
        ax.annotate('', xy=(4, 5.5), xytext=(3, start_y), arrowprops=dict(arrowstyle='->', color=color, lw=2))
    ax.annotate('', xy=(7.5, 5.5), xytext=(6.5, 5.5), arrowprops=dict(arrowstyle='->', color='#334155', lw=3))
    
    # Metrics box
    metrics = f"Key Metrics:\nTotal: {TOTAL_GEN:.0f} TWh\nRES: {RES_SHARE:.1f}%\nSolar: {SOLAR_TWH:.1f} TWh\nWind: {WIND_TWH:.0f} TWh\nCO2: {CO2_MT:.1f} Mt\nCost: €{271179404/1e6:.0f}M"
    ax.text(7.5, 1.5, metrics, fontsize=10, va='top', ha='left', bbox=dict(boxstyle='round', facecolor='#f1f5f9'), family='monospace')
    
    return fig

# INFOGRAPHIC 6: WIND VS SOLAR
def create_wind_solar_analysis():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Renewable Energy: Wind Dominates the 2045 System', fontsize=16, fontweight='bold')
    
    # Pie
    ax1 = axes[0]
    sizes = [SOLAR_TWH, WIND_TWH]
    labels = [f'Solar\n{SOLAR_TWH:.1f} TWh', f'Wind\n{WIND_TWH:.0f} TWh']
    ax1.pie(sizes, labels=labels, colors=[COLORS['solar'], COLORS['wind']], autopct='%1.1f%%', startangle=90, wedgeprops=dict(width=0.5))
    ax1.set_title('Renewable Generation Split', fontsize=14, fontweight='bold')
    
    # Bar comparison
    ax2 = axes[1]
    cats = ['Capacity (GW)', 'Generation (TWh)', 'RES Share (%)']
    solar_v = [SOLAR_GW, SOLAR_TWH, SOLAR_TWH/TOTAL_GEN*100]
    wind_v = [WIND_GW, WIND_TWH, WIND_TWH/TOTAL_GEN*100]
    
    x = np.arange(len(cats)); w = 0.35
    ax2.bar(x - w/2, solar_v, w, label='Solar', color=COLORS['solar'])
    ax2.bar(x + w/2, wind_v, w, label='Wind', color=COLORS['wind'])
    ax2.set_xticks(x); ax2.set_xticklabels(cats); ax2.legend()
    ax2.set_title('Solar vs Wind Comparison', fontsize=14, fontweight='bold')
    
    # Labels with smart offset
    for i in range(len(cats)):
        max_v = max(solar_v[i], wind_v[i])
        offset = max_v * 0.05 if max_v > 100 else max_v * 0.02 + 10
        ax2.text(i - w/2, solar_v[i] + offset, f'{solar_v[i]:.1f}', ha='center', fontsize=9)
        ax2.text(i + w/2, wind_v[i] + offset, f'{wind_v[i]:.1f}', ha='center', fontsize=9)
    
    plt.tight_layout(); return fig

# MAIN
def main():
    print("\n" + "="*70)
    print("ESM-P1 MGA — RESULT INFOGRAPHICS")
    print("="*70)
    print(f"Key: {RES_SHARE:.1f}% renewable, {WIND_TWH:.0f} TWh wind, {CO2_MT:.1f} Mt CO2")
    
    print("\n[1/6] Executive Dashboard..."); save_fig(create_executive_dashboard(), '01_executive_dashboard')
    print("\n[2/6] MGA Trade-off..."); save_fig(create_mga_tradeoff(), '02_mga_tradeoff_analysis')
    print("\n[3/6] Decarbonisation..."); save_fig(create_decarbonisation_pathway(), '03_decarbonisation_pathway')
    print("\n[4/6] Sensitivity..."); save_fig(create_sensitivity_analysis(), '04_sensitivity_analysis')
    print("\n[5/6] System Architecture..."); save_fig(create_system_architecture(), '05_system_architecture')
    print("\n[6/6] Wind vs Solar..."); save_fig(create_wind_solar_analysis(), '06_wind_solar_analysis')
    
    print("\n" + "="*70)
    print("COMPLETE!")
    print("="*70)
    print(f"\nOutput: {OUTPUT_DIR}")
    for f in sorted(OUTPUT_DIR.glob('*.png')): print(f"  • {f.name}")
    
    print("\nKEY INSIGHTS:")
    print("1. WIND DOMINANCE: Wind 85% of renewable (519 TWh) vs Solar 15% (92 TWh)")
    print("2. NEAR-100% RENEWABLE: 99.7% RES with 360 GW solar + 280 GW wind")
    print("3. LOW STORAGE SENSITIVITY: 5-day vs 30-day storage changes cost by <€50k")
    print("4. MGA TRADE-OFFS: All objectives yield similar system configurations")
    print("5. 95% DECARBONISATION: CO2 reduced from 300 Mt to 16 Mt")

if __name__ == "__main__": main()
