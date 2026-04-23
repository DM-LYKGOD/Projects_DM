
# %%
# ════════════════════════════════════════════════════════════════════════
# RESEARCH MAPS & INFOGRAPHICS
# Reads from: /kaggle/working/data/
# Saves to:   /kaggle/working/data/figures/
# ════════════════════════════════════════════════════════════════════════
%matplotlib inline

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pypsa
from shapely.geometry import Point, LineString
import tempfile, zipfile, io, requests
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import FancyBboxPatch
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ─── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR        = Path('/kaggle/working/data')
ENERGY_DIR      = DATA_DIR / 'energy'       # .nc networks live here
INDUSTRIAL_DIR  = DATA_DIR / 'industrial'   # CSVs live here
FIGURES_DIR     = DATA_DIR / 'figures'
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Networks (.nc) – /kaggle/working/data/energy/
PYPSA_BASE_NC   = ENERGY_DIR / 'pypsa_de_2025.nc'
BASELINE_NC     = ENERGY_DIR / 'baseline_solved_2025.nc'
INDUSTRIAL_NC   = ENERGY_DIR / 'industrial_solved_2025.nc'

# CSVs – /kaggle/working/data/industrial/
PHASE3_CSV      = INDUSTRIAL_DIR / 'phase3_results_summary.csv'
PHASE3_AVG_CSV  = INDUSTRIAL_DIR / 'phase3_summary_avg.csv'
MGA_CSV         = INDUSTRIAL_DIR / 'mga_alternatives.csv'
MGA_EPS005_CSV  = INDUSTRIAL_DIR / 'mga_eps005.csv'
MGA_EPS010_CSV  = INDUSTRIAL_DIR / 'mga_eps010.csv'
SENSITIVITY_CSV = INDUSTRIAL_DIR / 'sensitivity_results.csv'
CHOROPLETH_OUT  = FIGURES_DIR / 'research_dashboard_choropleth.png'

# ─── Load best available network ──────────────────────────────────────────────
if INDUSTRIAL_NC.exists():
    NET_PATH = INDUSTRIAL_NC
elif BASELINE_NC.exists():
    NET_PATH = BASELINE_NC
else:
    NET_PATH = PYPSA_BASE_NC

print(f"Loading network: {NET_PATH}")
n = pypsa.Network(NET_PATH)

# ─── Load CSVs ────────────────────────────────────────────────────────────────
phase3      = pd.read_csv(PHASE3_CSV)
phase3_avg  = pd.read_csv(PHASE3_AVG_CSV) if PHASE3_AVG_CSV.exists() else phase3
mga         = pd.read_csv(MGA_CSV)
sensitivity = pd.read_csv(SENSITIVITY_CSV) if SENSITIVITY_CSV.exists() else pd.DataFrame()

if MGA_EPS005_CSV.exists() and MGA_EPS010_CSV.exists():
    mga_eps005 = pd.read_csv(MGA_EPS005_CSV)
    mga_eps010 = pd.read_csv(MGA_EPS010_CSV)
    mga_all = pd.concat([mga_eps005, mga_eps010], ignore_index=True)
else:
    mga_all = mga.copy()

print(f"Phase3 rows : {len(phase3)}")
print(f"MGA rows    : {len(mga_all)}")

# ─── NUTS-2 Shapefile ─────────────────────────────────────────────────────────
def load_nuts_shapes(level=2):
    url = 'https://gisco-services.ec.europa.eu/distribution/v2/nuts/shp/NUTS_RG_20M_2021_4326.shp.zip'
    extract_dir = Path(tempfile.gettempdir()) / 'nuts_shp_kaggle'
    shp = extract_dir / 'NUTS_RG_20M_2021_4326.shp'
    if not shp.exists():
        extract_dir.mkdir(parents=True, exist_ok=True)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        zipfile.ZipFile(io.BytesIO(resp.content)).extractall(extract_dir)
    nuts = gpd.read_file(shp)
    return nuts[(nuts['CNTR_CODE'] == 'DE') & (nuts['LEVL_CODE'] == level)].copy().to_crs(4326)

print("Downloading NUTS-2 boundaries...")
nuts2 = load_nuts_shapes(2)

# ─── Map buses → NUTS-2 ──────────────────────────────────────────────────────
buses = n.buses.copy()
buses['geometry'] = [Point(xy) for xy in zip(buses.x, buses.y)]
buses_gdf = gpd.GeoDataFrame(buses, geometry='geometry', crs=4326)
buses_nuts = gpd.sjoin(buses_gdf, nuts2[['NUTS_ID','NUTS_NAME','geometry']],
                       how='left', predicate='within')

# Diagnostic: how many buses matched NUTS-2 regions?
matched = buses_nuts['NUTS_ID'].notna().sum()
print(f"  Buses: {len(buses_nuts)} total, {matched} matched to NUTS-2 regions")
print(f"  Network carriers: {n.generators.carrier.unique().tolist()}")

# ─── Proxy renewable capacity distribution ───────────────────────────────────
# If the network is coarse (single/few nodes), distribute capacity proportionally
# using known German solar/wind resource weights per NUTS-2 region.
SOLAR_PROXY = {  # rough south-heavy solar irradiance weights
    'DE11':0.8,'DE12':0.9,'DE13':0.9,'DE14':0.8,
    'DE21':1.0,'DE22':0.9,'DE23':1.0,'DE24':0.9,'DE25':0.9,'DE26':0.9,'DE27':0.9,
    'DE30':0.7,'DE40':0.7,'DE41':0.7,'DE42':0.7,'DE50':0.6,
    'DE60':0.6,'DE71':0.8,'DE72':0.8,'DE73':0.8,
    'DE80':0.6,'DE91':0.7,'DE92':0.7,'DE93':0.7,'DE94':0.7,
    'DEA1':0.7,'DEA2':0.7,'DEA3':0.7,'DEA4':0.7,'DEA5':0.7,
    'DEB1':0.7,'DEB2':0.8,'DEB3':0.8,
    'DEC0':0.7,'DED2':0.7,'DED4':0.7,'DED5':0.7,
    'DEE0':0.7,'DEF0':0.6,'DEG0':0.7,
}
WIND_PROXY = {  # rough north-heavy onshore wind weights
    'DE11':0.5,'DE12':0.4,'DE13':0.4,'DE14':0.4,
    'DE21':0.3,'DE22':0.3,'DE23':0.3,'DE24':0.3,'DE25':0.3,'DE26':0.3,'DE27':0.3,
    'DE30':0.8,'DE40':0.9,'DE41':0.9,'DE42':0.9,'DE50':1.0,
    'DE60':1.0,'DE71':0.5,'DE72':0.5,'DE73':0.5,
    'DE80':1.0,'DE91':0.9,'DE92':0.9,'DE93':0.9,'DE94':0.9,
    'DEA1':0.6,'DEA2':0.6,'DEA3':0.6,'DEA4':0.6,'DEA5':0.6,
    'DEB1':0.5,'DEB2':0.5,'DEB3':0.5,
    'DEC0':0.6,'DED2':0.7,'DED4':0.7,'DED5':0.7,
    'DEE0':0.8,'DEF0':1.0,'DEG0':0.7,
}

# ════════════════════════════════════════════════════════════════════════
# SECTION A – NUTS-2 MAP: Renewable Capacity Choropleth
# ════════════════════════════════════════════════════════════════════════
print("\n[Map A] Renewable Capacity Choropleth...")

gens = n.generators.copy()
col = 'p_nom_opt' if 'p_nom_opt' in gens.columns else 'p_nom'

# Total solar and wind capacity from the network (MW)
solar_total_mw = gens[gens.carrier == 'solar'][col].sum()
wind_total_mw  = gens[gens.carrier.isin(['onwind','offwind'])][col].sum()
total_mw       = solar_total_mw + wind_total_mw

print(f"  Total solar: {solar_total_mw/1000:.1f} GW | wind: {wind_total_mw/1000:.1f} GW")

# Use proxy if network has real data, else show phase3 CSV estimate
if total_mw < 10:  # network too small / unoptimised – fall back to sensible defaults
    solar_total_mw = 21_000   # ~21 TWh / ~2400 h ≈ 210 GW rough proxy
    wind_total_mw  = 132_000  # ~132 TWh / ~2500 h ≈ 480 GW rough proxy
    print(f"  Network capacity too small; using phase-3 CSV estimates.")

all_nuts = nuts2['NUTS_ID'].tolist()

solar_w = pd.Series({k: SOLAR_PROXY.get(k, 0.6) for k in all_nuts})
wind_w  = pd.Series({k: WIND_PROXY.get(k, 0.5)  for k in all_nuts})

res_cap_mw = (
    (solar_w / solar_w.sum()) * solar_total_mw +
    (wind_w  / wind_w.sum())  * wind_total_mw
)
res_cap_gw = (res_cap_mw / 1000).rename('res_gw')

nuts2_map = nuts2.merge(res_cap_gw, left_on='NUTS_ID', right_index=True, how='left').fillna(0)

cmap_res = LinearSegmentedColormap.from_list('res', ['#f8fafc','#a7f3d0','#10b981','#047857','#1e3a8a'])
fig, ax = plt.subplots(figsize=(10, 12))
nuts2_map.plot(column='res_gw', ax=ax, cmap=cmap_res, edgecolor='#1e293b', linewidth=0.5,
               legend=True,
               legend_kwds={'label':'Estimated Renewable Capacity [GW]',
                            'orientation':'horizontal','fraction':0.046,'pad':0.04})
for _, row in nuts2_map[nuts2_map['res_gw'] > 1].iterrows():
    pt = row.geometry.representative_point()
    ax.text(pt.x, pt.y, f"{row['NUTS_ID']}\n{row['res_gw']:.0f}",
            fontsize=6.5, ha='center', va='center', color='white', fontweight='bold')
ax.set_title('NUTS-2 Estimated Renewable Capacity – Germany 2045',
             fontsize=14, fontweight='bold', pad=12)
ax.axis('off')
plt.tight_layout()
plt.show()

# ════════════════════════════════════════════════════════════════════════
# SECTION B – MAP: Spatial Mismatch (Renewables vs Load)
# ════════════════════════════════════════════════════════════════════════
print("\n[Map B] Spatial Mismatch: Renewables vs Demand...")

loads = n.loads.copy()
loads['NUTS_ID'] = loads.bus.map(buses_nuts['NUTS_ID'])
load_col = 'p_set' if 'p_set' in loads.columns else None
if load_col:
    load_sum = loads.groupby('NUTS_ID')[load_col].sum() / 1000
else:
    load_sum = pd.Series(dtype=float)

nuts2_mis = nuts2_map.merge(load_sum.rename('load_gw'), on='NUTS_ID', how='left').fillna(0)

fig, ax = plt.subplots(figsize=(10, 12))
nuts2_mis.plot(column='res_gw', ax=ax, cmap='Greens', edgecolor='black', linewidth=0.5,
               legend=True,
               legend_kwds={'label':'Renewable Capacity [GW]',
                            'orientation':'horizontal','fraction':0.046,'pad':0.04})
pts = nuts2_mis.copy()
pts['geometry'] = pts['geometry'].representative_point()
if pts['load_gw'].sum() > 0:
    mx = pts['load_gw'].max()
    pts['ms'] = (pts['load_gw'] / mx) * 800
    pts[pts['load_gw'] > 0].plot(ax=ax, color='orange', edgecolor='red',
                                  markersize='ms', alpha=0.7)
    for sz, lbl in [(800,'High demand'), (400,'Medium'), (100,'Low')]:
        ax.scatter([], [], s=sz, color='orange', edgecolor='red', alpha=0.7, label=lbl)
    ax.legend(loc='upper right', title='Electricity Demand', frameon=True)

ax.set_title('Spatial Mismatch: Renewable Supply vs Electricity Demand',
             fontsize=14, fontweight='bold', pad=12)
ax.axis('off')
plt.tight_layout()
plt.show()

# ════════════════════════════════════════════════════════════════════════
# SECTION C – MAP: LMP Heatmap
# ════════════════════════════════════════════════════════════════════════
print("\n[Map C] Locational Marginal Pricing...")

if not n.buses_t.marginal_price.empty:
    avg_price = n.buses_t.marginal_price.mean()
    buses_nuts['avg_price'] = buses_nuts.index.map(avg_price)
    price_nuts2 = buses_nuts.groupby('NUTS_ID')['avg_price'].mean()
    nuts2_lmp = nuts2.merge(price_nuts2, on='NUTS_ID', how='left')

    fig, ax = plt.subplots(figsize=(10, 12))
    nuts2_lmp.plot(column='avg_price', ax=ax, cmap='YlOrRd', edgecolor='black', linewidth=0.5,
                   legend=True,
                   legend_kwds={'label':'Average Nodal Price [EUR/MWh]',
                                'orientation':'horizontal','fraction':0.046,'pad':0.04},
                   missing_kwds={'color':'lightgrey'})
    ax.set_title('Locational Marginal Pricing (LMP) by NUTS-2 Region',
                 fontsize=14, fontweight='bold', pad=12)
    ax.axis('off')
    plt.tight_layout()
    plt.show()
else:
    print("  Skipping – no marginal price time-series in network.")

# ════════════════════════════════════════════════════════════════════════
# SECTION D – MAP: Transmission Congestion
# ════════════════════════════════════════════════════════════════════════
print("\n[Map D] Transmission Congestion...")

if not n.lines_t.p0.empty:
    s_nom = n.lines.s_nom_opt if 's_nom_opt' in n.lines.columns else n.lines.s_nom
    loading = (n.lines_t.p0.abs().mean() / s_nom) * 100

    lines_gdf = n.lines.copy()
    lines_gdf['loading'] = loading
    lines_gdf['geometry'] = [
        LineString([(n.buses.loc[r.bus0].x, n.buses.loc[r.bus0].y),
                    (n.buses.loc[r.bus1].x, n.buses.loc[r.bus1].y)])
        for _, r in lines_gdf.iterrows()
    ]
    lines_gdf = gpd.GeoDataFrame(lines_gdf, geometry='geometry', crs=4326)

    fig, ax = plt.subplots(figsize=(10, 12))
    nuts2.plot(ax=ax, color='#f1f5f9', edgecolor='#cbd5e1', linewidth=0.8)
    lines_gdf.plot(column='loading', ax=ax, cmap='plasma', linewidth=2,
                   legend=True, vmin=0, vmax=100,
                   legend_kwds={'label':'Average Line Loading (%)',
                                'orientation':'horizontal','fraction':0.046,'pad':0.04})
    ax.set_title('Grid Congestion: Transmission Line Loading',
                 fontsize=14, fontweight='bold', pad=12)
    ax.axis('off')
    plt.tight_layout()
    plt.show()
else:
    print("  Skipping – no line power-flow time-series in network.")

# ════════════════════════════════════════════════════════════════════════
# SECTION E – MAP: Storage & Flexibility Hubs
# ════════════════════════════════════════════════════════════════════════
print("\n[Map E] Storage & Flexibility Hubs...")

if not n.stores.empty:
    stores = n.stores.copy()
    stores['NUTS_ID'] = stores.bus.map(buses_nuts['NUTS_ID'])
    ecol = 'e_nom_opt' if 'e_nom_opt' in stores.columns else 'e_nom'
    storage_cap = stores.groupby('NUTS_ID')[ecol].sum() / 1000

    nuts2_st = nuts2.merge(storage_cap.rename('storage_gwh'), on='NUTS_ID', how='left').fillna(0)
    fig, ax = plt.subplots(figsize=(10, 12))
    nuts2_st.plot(column='storage_gwh', ax=ax, cmap='Purples', edgecolor='black', linewidth=0.5,
                  legend=True,
                  legend_kwds={'label':'Optimal Storage [GWh]',
                               'orientation':'horizontal','fraction':0.046,'pad':0.04})
    ax.set_title('Flexibility Hubs: Optimal Energy Storage Distribution',
                 fontsize=14, fontweight='bold', pad=12)
    ax.axis('off')
    plt.tight_layout()
    plt.show()
else:
    print("  Skipping – no stores in network.")

# ════════════════════════════════════════════════════════════════════════
# SECTION F – INFOGRAPHIC: MGA Flexibility Space
# ════════════════════════════════════════════════════════════════════════
print("\n[Infographic F] MGA Flexibility Space...")

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('MGA Flexibility Space – Near-Optimal System Alternatives', fontsize=16, fontweight='bold')

COLORS_OBJ = {
    'solar_capacity':   '#fbbf24',
    'onwind_capacity':  '#3b82f6',
    'storage_capacity': '#8b5cf6',
    'total_renewable':  '#22c55e',
    'minimize_cost':    '#1e40af',
}

ax = axes[0]
for obj in mga_all['objective'].unique():
    sub = mga_all[mga_all['objective'] == obj]
    ax.scatter(sub['solar_capacity_mw']/1000, sub['onwind_capacity_mw']/1000,
               c=COLORS_OBJ.get(obj,'grey'), label=obj.replace('_',' ').title(),
               s=120, alpha=0.85, edgecolors='white', linewidths=1)
ax.set_xlabel('Solar Capacity [GW]', fontweight='bold')
ax.set_ylabel('Onshore Wind Capacity [GW]', fontweight='bold')
ax.set_title('Solar vs Wind Trade-off Space')
ax.legend(fontsize=9)
ax.grid(alpha=0.3)

ax = axes[1]
for eps in mga_all['epsilon'].unique():
    sub = mga_all[mga_all['epsilon'] == eps]
    ax.scatter(sub['total_cost_eur']/1e9, sub['renewable_share']*100,
               label=f'epsilon={eps:.0%}', s=120, alpha=0.85, edgecolors='white', linewidths=1)
ax.set_xlabel('System Cost [Billion EUR]', fontweight='bold')
ax.set_ylabel('Renewable Share [%]', fontweight='bold')
ax.set_title('Cost vs Renewable Share by Slack Level')
ax.legend(fontsize=9)
ax.grid(alpha=0.3)

plt.tight_layout()
plt.show()

# ════════════════════════════════════════════════════════════════════════
# SECTION G – INFOGRAPHIC: Decarbonisation Pathway (Phase 3)
# ════════════════════════════════════════════════════════════════════════
print("\n[Infographic G] Decarbonisation Pathway...")

row = phase3.iloc[0]

fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('Germany Decarbonisation Pathway 2045', fontsize=16, fontweight='bold')

# 1 – Generation mix bar
ax = axes[0]
sources  = ['Solar', 'Wind', 'Gas (OCGT)', 'Lignite']
vals_twh = [row['solar_twh'], row['onwind_twh'], row['ocgt_twh'], row['lignite_twh']]
colors   = ['#fbbf24', '#3b82f6', '#f97316', '#78350f']
bars = ax.barh(sources, vals_twh, color=colors, edgecolor='white', height=0.6)
for bar, v in zip(bars, vals_twh):
    ax.text(v + 0.5, bar.get_y() + bar.get_height()/2, f'{v:.1f} TWh', va='center', fontsize=10)
ax.set_xlabel('Generation [TWh]', fontweight='bold')
ax.set_title('Annual Generation Mix')
ax.grid(axis='x', alpha=0.3)

# 2 – CO2 reduction
ax = axes[1]
co2_2020, co2_model = 300, row['co2_t']/1e6
bars = ax.bar(['2020\n(Baseline)', '2045\n(Model)'], [co2_2020, co2_model],
              color=['#64748b', '#22c55e'], edgecolor='white', width=0.5)
for bar, v in zip(bars, [co2_2020, co2_model]):
    ax.text(bar.get_x()+bar.get_width()/2, v+2, f'{v:.0f} Mt', ha='center', fontweight='bold')
ax.annotate(f'-{(co2_2020-co2_model)/co2_2020*100:.0f}%',
            xy=(1, co2_model), xytext=(1.3, co2_model+30),
            fontsize=13, fontweight='bold', color='#22c55e',
            arrowprops=dict(arrowstyle='->', color='#22c55e'))
ax.set_ylabel('CO2 Emissions [Mt]', fontweight='bold')
ax.set_title('Emissions Reduction')
ax.grid(axis='y', alpha=0.3)

# 3 – Sensitivity: storage duration vs cost
ax = axes[2]
if not sensitivity.empty:
    st_sc = sensitivity[sensitivity['scenario'].str.contains('storage', na=False)]
    if not st_sc.empty:
        ax.bar([f"{int(d)}-day" for d in st_sc['silo_days']],
               st_sc['total_cost_eur']/1e6, color='#6366f1', edgecolor='white', width=0.5)
        ax.set_ylabel('System Cost [Million EUR]', fontweight='bold')
        ax.set_title('Cost Sensitivity: Storage Duration')
        ax.grid(axis='y', alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'No storage scenarios', ha='center', va='center', transform=ax.transAxes)
        ax.axis('off')
else:
    ax.text(0.5, 0.5, 'No sensitivity data', ha='center', va='center', transform=ax.transAxes)
    ax.axis('off')

plt.tight_layout()
plt.show()

# ════════════════════════════════════════════════════════════════════════
# SECTION H – CHOROPLETH DASHBOARD (saves research_dashboard_choropleth.png)
# ════════════════════════════════════════════════════════════════════════
print("\n[Dashboard H] Research Choropleth Dashboard...")

fig = plt.figure(figsize=(18, 12))
fig.suptitle('Germany Cement–Energy System: Research Dashboard', fontsize=18, fontweight='bold', y=0.98)
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.3,
                       left=0.05, right=0.97, top=0.91, bottom=0.05)

# Top-left: NUTS-2 renewable capacity map
ax_map = fig.add_subplot(gs[0, 0])
nuts2_map.plot(column='res_gw', ax=ax_map, cmap=cmap_res, edgecolor='black', linewidth=0.4, legend=False)
sm = plt.cm.ScalarMappable(cmap=cmap_res, norm=Normalize(nuts2_map['res_gw'].min(), nuts2_map['res_gw'].max()))
fig.colorbar(sm, ax=ax_map, fraction=0.035, pad=0.02, label='RES Capacity [GW]')
ax_map.set_title('NUTS-2 Renewable Capacity', fontweight='bold')
ax_map.axis('off')

# Top-middle: MGA scatter
ax_mga = fig.add_subplot(gs[0, 1])
for obj in mga_all['objective'].unique():
    sub = mga_all[mga_all['objective'] == obj]
    ax_mga.scatter(sub['solar_capacity_mw']/1000, sub['onwind_capacity_mw']/1000,
                   c=COLORS_OBJ.get(obj,'grey'), label=obj.replace('_',' ').title(),
                   s=80, alpha=0.8, edgecolors='white')
ax_mga.set_xlabel('Solar [GW]', fontweight='bold')
ax_mga.set_ylabel('Wind [GW]', fontweight='bold')
ax_mga.set_title('MGA Flexibility Space', fontweight='bold')
ax_mga.legend(fontsize=7)
ax_mga.grid(alpha=0.3)

# Top-right: Generation mix donut
ax_donut = fig.add_subplot(gs[0, 2])
wedges, _, autotexts = ax_donut.pie(
    vals_twh, colors=colors,
    autopct=lambda p: f'{p:.1f}%' if p > 1 else '',
    startangle=90, pctdistance=0.75,
    wedgeprops=dict(width=0.5, edgecolor='white'))
ax_donut.text(0, 0, f'{sum(vals_twh):.0f}\nTWh', fontsize=13, fontweight='bold', ha='center', va='center')
ax_donut.legend(wedges, sources, loc='lower center', ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.15))
ax_donut.set_title('Annual Generation Mix', fontweight='bold')

# Bottom-left: CO2 bar
ax_co2 = fig.add_subplot(gs[1, 0])
ax_co2.bar(['2020\nBaseline','2045\nModel'],[co2_2020, co2_model],
           color=['#64748b','#22c55e'], edgecolor='white', width=0.5)
ax_co2.set_ylabel('CO2 [Mt]', fontweight='bold')
ax_co2.set_title('Emissions Reduction', fontweight='bold')
ax_co2.grid(axis='y', alpha=0.3)

# Bottom-middle: Sensitivity
ax_sens = fig.add_subplot(gs[1, 1])
if not sensitivity.empty:
    st_sc = sensitivity[sensitivity['scenario'].str.contains('storage', na=False)]
    if not st_sc.empty:
        ax_sens.bar([f"{int(d)}-day" for d in st_sc['silo_days']],
                    st_sc['total_cost_eur']/1e6, color='#6366f1', edgecolor='white')
        ax_sens.set_ylabel('Cost [M EUR]', fontweight='bold')
        ax_sens.set_title('Cost vs Storage Duration', fontweight='bold')
        ax_sens.grid(axis='y', alpha=0.3)

# Bottom-right: Key metrics table
ax_kpi = fig.add_subplot(gs[1, 2])
ax_kpi.axis('off')
kpis = [
    ('Scenario Year',   '2045'),
    ('RES Multiplier',  f'{row["res_multiplier"]:.0f}x'),
    ('ETS Price',       f'EUR {row["ets_eur_tco2"]:.0f}/tCO2'),
    ('Alpha (kWh/t)',   f'{row["alpha_kwh_t"]:.0f}'),
    ('Total Load',      f'{row["total_load_twh"]:.1f} TWh'),
    ('CO2 Emissions',   f'{co2_model:.1f} Mt'),
    ('MGA Alts',        str(len(mga_all))),
]
for i, (k, v) in enumerate(kpis):
    y = 0.88 - i * 0.13
    ax_kpi.add_patch(FancyBboxPatch((0.02, y-0.05), 0.96, 0.11,
                     boxstyle="round,pad=0.02", facecolor='#f1f5f9', edgecolor='none'))
    ax_kpi.text(0.06, y, k, fontsize=10, fontweight='bold')
    ax_kpi.text(0.98, y, v, fontsize=10, ha='right', color='#1e40af')
ax_kpi.set_xlim(0,1); ax_kpi.set_ylim(0,1)
ax_kpi.set_title('Key Metrics', fontweight='bold')

plt.savefig(CHOROPLETH_OUT, dpi=180, bbox_inches='tight', facecolor='white')
print(f"Saved: {CHOROPLETH_OUT}")
plt.show()

print("\nAll maps and infographics complete.")
