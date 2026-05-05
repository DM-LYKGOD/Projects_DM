# Debapratim Mukherjee Project Portfolio

This repository is organized as a technical portfolio spanning energy economics, energy modeling, environmental modeling, applied mathematics, geospatial analysis, machine learning, and econometrics.

## Repository Structure

```text
projects/
  01-lake-eutrophication-model/
  02-autocatalytic-reaction-cstr/
  03-population-equilibrium-growth-rate/
  04-sediment-oxygen-dynamics/
  05-river-flow-distance-analysis/
  06-temperature-species-predation-model/
  07-energy-bill-information-extraction/
  08-renewable-energy-econometrics/
  09-phytoplankton-density-prediction/
  10-carbon-budget-cdr-modeling/
  11-cement-emissions-analysis/
  12-ESM-P1-MGA/
  13-hisim-practice-task/
```

## Portfolio Highlights

- PyPSA-based German energy-system optimisation with MGA (Modelling to Generate Alternatives) for cement-sector flexibility and 2045 decarbonisation targets.
- ETHOS.HiSim fork for household infrastructure and building energy simulation (heat pumps, batteries, EVs, thermal storage).
- Environmental and ecosystem simulations written in R with a focus on ODE-based system behavior.
- Applied machine learning workflows in Python for OCR-assisted extraction, ecological forecasting (Random Forest, XGBoost, hybrid ML), and multivariate time-series prediction.
- Econometric analysis connecting renewable energy adoption with macroeconomic output.
- Carbon-budget and CDR (carbon dioxide removal) modelling using GEKKO optimal control.
- GIS-oriented workflows for river network shortest-path analysis and spatial data processing.
- Research-oriented code packaged as self-contained project folders with local documentation.

## Project Index

| # | Project | Category | Focus Area | Stack | Entry Point |
|---|---------|----------|------------|-------|-------------|
| 01 | [Lake Eutrophication Model](projects/01-lake-eutrophication-model/README.md) | Environmental Modeling | Lake nutrient and food-web dynamics | R, deSolve, ggplot2 | `src/lake_eutrophication_model.R` |
| 02 | [Autocatalytic Reaction CSTR](projects/02-autocatalytic-reaction-cstr/README.md) | Applied Math | Flow-through stirred tank kinetics | R | `src/autocatalytic_reaction_cstr.R` |
| 03 | [Population Equilibrium vs Growth Rate](projects/03-population-equilibrium-growth-rate/README.md) | Environmental Modeling | Periodicity and equilibrium response | R | `src/population_equilibrium_growth_rate.R` |
| 04 | [Sediment Oxygen Dynamics](projects/04-sediment-oxygen-dynamics/README.md) | Environmental Modeling | Oxygen transport and consumption in sediment | R, minpack.lm | `src/sediment_oxygen_dynamics.R` |
| 05 | [River Flow Distance Analysis](projects/05-river-flow-distance-analysis/README.md) | Environmental Modeling | Shortest-path over river networks with elevation adjustment | R, GIS, sf, terra | `src/river_flow_distance_analysis.R` |
| 06 | [Temperature and Species Predation Model](projects/06-temperature-species-predation-model/README.md) | Environmental Modeling | Temperature effects in a limiting similarity model | R | `src/temperature_species_predation_model.R` |
| 07 | [Energy Bill Information Extraction](projects/07-energy-bill-information-extraction/README.md) | Energy Data Extraction | OCR + LLM-based structured extraction from PDF bills | Python, pdfplumber, pytesseract, Groq | `src/energy_bill_extraction.py` |
| 08 | [Renewable Energy Econometrics](projects/08-renewable-energy-econometrics/README.md) | Energy Modeling | Regression of renewable capacity share vs GDP | Python, pandas, statsmodels | `src/renewable_energy_econometric_model.py` |
| 09 | [Phytoplankton Density Prediction](projects/09-phytoplankton-density-prediction/README.md) | Environmental Modeling | Master's thesis ML pipeline, 58 species, Greifensee | Python, scikit-learn, xgboost | `src/phytoplankton_prediction_pipeline.py` |
| 10 | [Carbon Budget and CDR Modeling](projects/10-carbon-budget-cdr-modeling/README.md) | Energy Modeling | Dynamic climate-economy optimisation under carbon budget | Python, gekko, matplotlib | `src/carbon_budget_optimal_control.py` |
| 11 | [Cement Emissions Analysis](projects/11-cement-emissions-analysis/README.md) | Environmental Modeling | Regional cement-sector PM2.5/NO2 regression and clustering | Python, pandas, scikit-learn, DBSCAN | `src/pollution_regression_analysis.py` |
| 12 | [ESM-P1-MGA](projects/12-ESM-P1-MGA/README.md) | Energy Modeling | Germany cement-energy system with MGA near-optimal alternatives | Python, pypsa, geopandas, ERA5 | `ESM_P1_MGA_Standalone.ipynb` |
| 13 | [HiSim Practice Task](projects/13-hisim-practice-task/README.md) | Energy Modeling | Fork of ETHOS.HiSim for household energy simulation practice | Python, hisim | `hisim/` |

## Featured Project: ESM-P1-MGA

The ESM-P1-MGA project (Project 12) is the primary research output -- a PyPSA-based co-optimisation model of the German electricity system and cement industry under 2045 decarbonisation targets. It uses Modelling to Generate Alternatives (MGA) to explore structurally different near-optimal pathways.

**Key results:** 99.1% renewable share, 15.8 Mt CO2 (94.7% reduction), 628 TWh load, 10 MGA near-optimal alternatives at 5% and 10% cost slack.

See the [project README](projects/12-ESM-P1-MGA/README.md) for full details including system architecture, data sources, and research infographics.

## Working Conventions

- Each project folder includes a local `README.md`.
- Source code is grouped under `src/` or `notebooks/`.
- Thesis assets are separated into `data/`, `outputs/`, and `reports/`.
- Secrets should be supplied through environment variables, never hardcoded into notebooks or scripts.
- READMEs summarize results and usage -- they are not raw execution logs.


## Author

Debapratim Mukherjee
Research focus: energy systems, industrial decarbonisation, econometrics, and machine learning
GitHub: https://github.com/DM-LYKGOD
