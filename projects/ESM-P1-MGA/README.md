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

## Running on Kaggle

1. Upload `ESM_P1_MGA_Standalone.ipynb` to a Kaggle notebook
2. Attach the dataset `debapratim07/esm-dataset` as input
3. Run all cells top-to-bottom (~6–8 hours on Kaggle free tier)
4. Paste `research_maps_kaggle.py` into a new cell to generate all spatial maps

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
