"""
Fixed NUTS2 Capacity Map - Handles missing data properly
Fixes white regions by using masked NaN values or distinct "no data" styling
"""
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import pypsa
from shapely.geometry import Point
import tempfile
import zipfile
import io
import requests
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib import cm
import numpy as np

print("Loading PyPSA Network...")
solved_nc = Path('data/energy/industrial_solved_2025.nc')
if not solved_nc.exists():
    solved_nc = Path('data/energy/pypsa_de_2025.nc')
n = pypsa.Network(solved_nc)

print("Downloading NUTS-2 German Boundaries...")
def load_nuts2_shapes():
    url = 'https://gisco-services.ec.europa.eu/distribution/v2/nuts/shp/NUTS_RG_20M_2021_4326.shp.zip'
    extract_dir = Path(tempfile.gettempdir()) / 'nuts_shp_dashboard'
    shp = extract_dir / 'NUTS_RG_20M_2021_4326.shp'
    if not shp.exists():
        extract_dir.mkdir(parents=True, exist_ok=True)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        zipfile.ZipFile(io.BytesIO(resp.content)).extractall(extract_dir)
    nuts = gpd.read_file(shp)
    nuts2 = nuts[(nuts['CNTR_CODE'] == 'DE') & (nuts['LEVL_CODE'] == 2)].copy()
    nuts2 = nuts2.to_crs(epsg=4326)
    return nuts2

nuts2 = load_nuts2_shapes()
print(f"Total NUTS2 regions in Germany: {len(nuts2)}")
print(f"NUTS2 codes: {nuts2['NUTS_ID'].tolist()}")

print("Mapping PyPSA buses to NUTS-2 regions...")
buses = n.buses.copy()
buses['geometry'] = [Point(xy) for xy in zip(buses.x, buses.y)]
buses_gdf = gpd.GeoDataFrame(buses, geometry='geometry', crs="EPSG:4326")

# Spatial join buses to NUTS-2
buses_with_nuts2 = gpd.sjoin(buses_gdf, nuts2, how='left', predicate='within')

print("Aggregating Optimized Renewable Capacity...")
gens = n.generators.copy()
gens['NUTS_ID'] = gens.bus.map(buses_with_nuts2['NUTS_ID'])

# Filter Renewables (Solar and Wind)
res_gens = gens[gens.carrier.isin(['solar', 'onwind', 'offwind'])]
print(f"Renewable generators found: {len(res_gens)}")

if 'p_nom_opt' not in res_gens.columns:
    res_gens['p_nom_opt'] = res_gens['p_nom']

# Aggregate by NUTS_ID
capacity_by_nuts2 = res_gens.groupby('NUTS_ID')['p_nom_opt'].sum() / 1000  # Convert to GW

# Merge back into the NUTS-2 GeoDataFrame
nuts2 = nuts2.merge(capacity_by_nuts2, on='NUTS_ID', how='left')

# Identify regions with data vs no data
nuts2['has_data'] = nuts2['p_nom_opt'].notna() & (nuts2['p_nom_opt'] > 0)
regions_with_data = nuts2['has_data'].sum()
regions_no_data = len(nuts2) - regions_with_data

print(f"Regions with renewable capacity: {regions_with_data}")
print(f"Regions without data: {regions_no_data}")

# Fill NaN with 0 for plotting (but track which are missing)
nuts2['p_nom_opt'] = nuts2['p_nom_opt'].fillna(0)

print("Generating NUTS-2 Choropleth Map...")
fig, ax = plt.subplots(1, 1, figsize=(12, 14))

# Custom Colormap - only for regions with data
cmap = LinearSegmentedColormap.from_list('res_map', ['#fef3c7', '#fcd34d', '#f59e0b', '#d97706', '#92400e'])

# Separate regions with and without data
nuts2_with_data = nuts2[nuts2['has_data']]
nuts2_no_data = nuts2[~nuts2['has_data']]

# Plot regions WITHOUT data first (light gray with hatching)
nuts2_no_data.plot(ax=ax, color='#e5e7eb', edgecolor='#9ca3af', linewidth=0.5, hatch='///')

# Plot regions WITH data using colormap
vmin, vmax = 0, nuts2_with_data['p_nom_opt'].max() * 1.1
norm = Normalize(vmin=vmin, vmax=vmax)
nuts2_with_data.plot(column='p_nom_opt', ax=ax, cmap=cmap, norm=norm,
                      edgecolor='black', linewidth=0.5)

# Add colorbar
sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, orientation='horizontal', fraction=0.046, pad=0.04, shrink=0.8)
cbar.set_label("Optimized Renewable Capacity [GW]", fontsize=12)

# Add NUTS_ID labels for regions with significant capacity
for _, row in nuts2_with_data[nuts2_with_data['p_nom_opt'] > nuts2_with_data['p_nom_opt'].quantile(0.25)].iterrows():
    pt = row.geometry.representative_point()
    ax.text(pt.x, pt.y, row['NUTS_ID'][-3:], fontsize=8, ha='center', va='center', 
            color='black', weight='bold', 
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

ax.set_title("NUTS-2 Optimal Renewable Energy Distribution (Germany 2045)\n" + 
             f"Gray regions: No generator data | {regions_with_data} regions with capacity", 
             fontsize=14, fontweight='bold')
ax.axis('off')

# Add legend for no-data regions
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor='#e5e7eb', edgecolor='#9ca3af', hatch='///', 
                         label=f'No data ({regions_no_data} regions)'),
                   Patch(facecolor='#f59e0b', edgecolor='black', 
                         label=f'Has data ({regions_with_data} regions)')]
ax.legend(handles=legend_elements, loc='lower left', fontsize=10)

plt.tight_layout()
plt.savefig('Result_2/infographics/06_nuts2_capacity_map_fixed.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Saved: Result_2/infographics/06_nuts2_capacity_map_fixed.png")

# Also print which NUTS2 codes have no data
no_data_codes = nuts2_no_data['NUTS_ID'].tolist()
print(f"\nRegions without data: {no_data_codes}")
