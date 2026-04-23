"""
NUTS2 Map with Clear 'No Regional Data' Indicator
Shows that ESM-P1 is a national aggregate model without NUTS2 granularity
"""
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import tempfile
import zipfile
import io
import requests
from pathlib import Path

print("Downloading NUTS-2 German Boundaries...")
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

print(f"Total NUTS2 regions in Germany: {len(nuts2)}")
print(f"NUTS2 codes: {nuts2['NUTS_ID'].tolist()}")

print("\nGenerating Map with 'No Data' Indicator...")
fig, ax = plt.subplots(1, 1, figsize=(14, 16))

# Plot all regions with gray hatching to indicate no data
nuts2.plot(ax=ax, color='#e5e7eb', edgecolor='#6b7280', linewidth=1.0, 
           hatch='///', alpha=0.8)

# Add NUTS_ID labels for reference
for _, row in nuts2.iterrows():
    pt = row.geometry.representative_point()
    ax.text(pt.x, pt.y, row['NUTS_ID'], fontsize=7, ha='center', va='center', 
            color='#374151', weight='bold',
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white', alpha=0.8, edgecolor='#9ca3af'))

# Add prominent "NO REGIONAL DATA" text overlay
ax.text(0.5, 0.5, 'NO REGIONAL DATA\nModel: National Aggregate', 
        transform=ax.transAxes, fontsize=24, fontweight='bold', 
        ha='center', va='center', color='#dc2626',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#dc2626', linewidth=3, alpha=0.95))

# Title
ax.set_title("NUTS-2 Regional Map: ESM-P1 MGA Model\n" +
             "Note: Model uses national-level aggregation (1 bus). No regional capacity distribution available.",
             fontsize=14, fontweight='bold', pad=20)

# Legend for hatched regions
legend_elements = [
    Patch(facecolor='#e5e7eb', edgecolor='#6b7280', hatch='///', 
          label=f'No Data Available ({len(nuts2)} regions)'),
]
ax.legend(handles=legend_elements, loc='lower left', fontsize=11, framealpha=0.95)

# Add note box explaining why
note_text = """
MODEL INFORMATION:
- ESM-P1 is a national aggregate model
- Represents Germany as 1 bus
- No NUTS2 regional granularity
- For regional analysis, use EEGSO 
  or official BMWK data
"""
ax.text(0.02, 0.02, note_text, transform=ax.transAxes, fontsize=9,
        va='bottom', ha='left', family='monospace',
        bbox=dict(boxstyle='round', facecolor='#fef3c7', edgecolor='#f59e0b', alpha=0.95))

ax.axis('off')

plt.tight_layout()
output_path = 'Result_2/infographics/06_nuts2_no_data_map.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
print(f"Saved: {output_path}")

# Also create a version showing what regions exist
fig2, ax2 = plt.subplots(1, 1, figsize=(14, 16))
nuts2.plot(ax=ax2, color='#dbeafe', edgecolor='#1e40af', linewidth=1.0, alpha=0.9)

# Label all regions
for _, row in nuts2.iterrows():
    pt = row.geometry.representative_point()
    ax2.text(pt.x, pt.y, row['NUTS_ID'], fontsize=8, ha='center', va='center', 
            color='#1e3a8a', weight='bold')

ax2.set_title("Germany NUTS-2 Regions\nAll 38 NUTS2 regions shown for reference", 
              fontsize=14, fontweight='bold')
ax2.axis('off')

output_path2 = 'Result_2/infographics/06_nuts2_reference_map.png'
plt.savefig(output_path2, dpi=300, bbox_inches='tight', facecolor='white')
print(f"Saved: {output_path2}")

print("\nDone! Created 2 map files:")
print(f"  1. {output_path} - Shows no data available")
print(f"  2. {output_path2} - Reference map of all NUTS2 regions")
