# ESM-P1-MGA: Germany Cement-Energy System Model
### Modelling to Generate Alternatives (MGA) — PhD Research Pipeline

> **Part 1 of a multi-phase PhD research pipeline** integrating the German cement industry into a national energy system model under 2045 decarbonisation targets.

---

## Overview

This project builds a PyPSA-based optimisation model of the German electricity system, co-optimised with the cement industry as a demand-side flexibility resource. Using **Modelling to Generate Alternatives (MGA)**, it explores the full landscape of near-optimal investment strategies — revealing that multiple structurally different but equally cost-efficient decarbonisation pathways exist.

**Key Research Questions:**
- Can the cement industry's silo storage act as a virtual battery to integrate renewable energy?
- What is the flexibility space of near-optimal German energy system configurations in 2045?
- How sensitive are results to weather year variability and industrial storage assumptions?

---

## Repository Structure

```
ESM-P1-MGA/
├── ESM_P1_MGA_Standalone.ipynb    ← Main Kaggle notebook (all pipeline phases)
├── research_maps_kaggle.py         ← NUTS-2 spatial maps & research infographics
├── requirements.txt                ← Python dependencies
├── README.md
│
├── data/
│   ├── energy/                     ← Grid & network data
│   │   ├── pypsa_de_2025.nc        ← PyPSA-DE network (4-node, 2025)
│   │   ├── baseline_solved_2025.nc ← Solved baseline network
│   │   ├── industrial_solved_2025.nc ← Solved industrial co-optimisation
│   │   ├── entsoe_generation_DE_2023.csv
│   │   ├── entsoe_load_DE_2023.csv
│   │   ├── opsd_powerplants_DE.csv
│   │   └── opsd_timeseries_DE.csv
│   │
│   ├── industrial/                 ← Cement industry data
│   │   ├── cement_parameters.json  ← Clinker ratio, energy intensity (α), silo config
│   │   ├── cement_nuts3_weights_2022.csv
│   │   ├── cement_seasonality.csv
│   │   ├── destatis_cement_production_annual.csv
│   │   ├── destatis_wz08_cement.csv
│   │   ├── eurostat_industrial_elec_DE.csv
│   │   ├── mga_alternatives.csv    ← MGA result (10 near-optimal alternatives)
│   │   ├── phase3_results_summary.csv
│   │   └── production_schedule_2025.csv ← Hourly cement flex schedule
│   │
│   ├── climate/                    ← ERA5 renewable resource data
│   │   ├── era5_pv_cf_DE_2023.csv  ← Solar capacity factors (hourly)
│   │   └── era5_wind_cf_DE_2023.csv ← Wind capacity factors (hourly)
│   │
│   ├── raw/                        ← Raw input datasets
│   │   ├── conventional_power_plants_DE.csv
│   │   ├── Realisierte_Erzeugung_*.csv
│   │   └── Realisierter_Stromverbrauch_*.csv
│   │
│   └── figures/                    ← All generated plots & maps
│
└── Result_2/                       ← Final model run outputs
    ├── mga_alternatives.csv
    ├── mga_eps005.csv              ← MGA at 5% cost slack
    ├── mga_eps010.csv              ← MGA at 10% cost slack
    ├── phase3_results_summary.csv
    ├── phase3_summary_avg.csv
    ├── sensitivity_results.csv
    ├── production_schedule_2025.csv
    └── infographics/               ← Publication-ready maps & charts
```

---

## Model Pipeline (inside the notebook)

| Phase | Description |
|-------|-------------|
| **Phase 0** | Build PyPSA-DE 4-node network from OPSD & ENTSO-E data |
| **Phase A** | Baseline electricity system optimisation (2025) |
| **Phase B** | Add cement industry with flexible demand scheduling |
| **Phase C** | Co-optimise grid + industry under 2045 RES/ETS targets |
| **Phase D** | MGA: generate 10 near-optimal alternatives at ε = 5%, 10% |
| **Phase E** | Post-processing, KPI extraction, result analysis |
| **Phase F** | Sensitivity: weather years × silo storage durations |

---

## Key Results (Phase C — Germany 2045)

| Metric | Value |
|--------|-------|
| Renewable Share | **99.1%** |
| Solar Generation | 21 TWh |
| Wind Generation | 133 TWh |
| Total System Load | 628 TWh |
| CO₂ Emissions | 15.8 Mt |
| ETS Carbon Price | €180 / tCO₂ |
| Cement α (energy intensity) | 480 kWh / t |
| MGA Alternatives | 10 (ε = 5% & 10%) |

---

## System Architecture

![ESM-P1-MGA System Architecture](Result_2/infographics/ESM-%20System%20Architecture.png)

The model connects three layers:

| Layer | Components |
|---|---|
| **Generation** | Solar PV (~21 TWh/yr) · Onshore Wind (~133 TWh/yr) · Gas OCGT (backup) |
| **Grid** | Germany Electricity Grid — PyPSA 4-node · 99.1% renewable share · 628 TWh load · ETS: €180/tCO₂ |
| **Industrial** | Industrial Bus (Cement Sector) → Kiln/Clinker (28 Mt/yr) + Silo Storage (5-day buffer) · α = 480 kWh/t |

The **silo storage** acts as a virtual battery: cement production is shifted to high-renewable hours, with the silo buffer absorbing the mismatch — decoupling industrial demand from the grid in near-real-time.

---

## Research Infographics

All infographics are in [`Result_2/infographics/`](Result_2/infographics/).

### MGA Flexibility Space
![MGA Flexibility Space](Result_2/infographics/MGA%20Flexibility%20Space.png)
*Near-optimal system alternatives at 5% and 10% cost slack — shows the structural diversity of the solution space.*

---

### Power Sector Decarbonisation
![Power Sector Decarbonisation](Result_2/infographics/Power%20Sector%20Decarbonisation.png)
*CO₂ reduction from 2020 baseline (~300 Mt) to the 2045 model result (~15.8 Mt) — a 94.7% reduction.*

---

### Annual Generation Mix
![Annual Generation Mix](Result_2/infographics/Annual%20Generation%20Mix.png)
*Technology share breakdown: Solar 21 TWh · Wind 133 TWh · Gas backup · 99.1% renewable share.*

---

### MGA Alternative Profiles
![MGA Alternative Profiles](Result_2/infographics/MGA%20Alternative%20Profiles.png)
*Radar chart comparing near-optimal alternatives across solar capacity, wind capacity, cost, CO₂, and renewable share axes.*

---

### MGA Cost–CO₂ Pareto Frontier
![MGA Cost-CO2 Pareto Frontier](Result_2/infographics/MGA%20Cost-Co2%20Pareto%20Frontier.png)
*Pareto frontier showing cost vs. CO₂ across all MGA alternatives at ε = 5% and 10%.*

---

### German Cement Industry — NUTS-3 Plant Locations
![German Cement Industry Plant Locations](Result_2/infographics/German%20Cement%20Industry-%20Plant%20Location%20and%20Production%20weight.png)
*Bubble map showing cement production weight by NUTS-3 district — the spatial distribution of industrial demand used as model input.*

---

## Running on Kaggle (Due to computational limitation)

1. Upload `ESM_P1_MGA_Standalone.ipynb` to a Kaggle notebook
2. Attach the dataset `debapratim07/esm-dataset` as input
3. Run all cells top-to-bottom (~6–8 hours on Kaggle free tier)

**Data paths expected on Kaggle:**
```
/kaggle/working/data/energy/     ← .nc networks
/kaggle/working/data/industrial/ ← CSVs
/kaggle/working/data/figures/    ← output maps
```

---

## Data Sources

| Dataset | Source |
|---------|--------|
| Power plant fleet | [OPSD](https://open-power-system-data.org/) |
| Electricity load & generation | [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) |
| Hourly timeseries | [OPSD Time Series](https://data.open-power-system-data.org/time_series/) |
| Climate / capacity factors | [ERA5 via CDS](https://cds.climate.copernicus.eu/) |
| Cement production statistics | [Destatis WZ08](https://www.destatis.de/) |
| Cement industry energy use | [Eurostat](https://ec.europa.eu/eurostat) |
| NUTS-2 shapefiles | [Eurostat GISCO](https://gisco-services.ec.europa.eu/) |

> **Note:** `time_series_60min_singleindex.csv` (130 MB) and ERA5 `.nc` files exceed GitHub's 100 MB limit and are not included. Download from the respective sources above.

---

## Dependencies

```
pypsa>=0.26
pandas
geopandas
matplotlib
seaborn
requests
shapely
numpy
highspy
netCDF4
xarray
```

Install via:
```bash
pip install -r requirements.txt
```

---

## Author

**Debapratim Mukherjee**
PhD Researcher — Industrial Energy Systems & Decarbonisation
