# Debapratim Mukherjee Project Portfolio

This repository is organized as a technical portfolio spanning environmental modeling, applied mathematics, geospatial analysis, machine learning, and econometrics.

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
```

## Portfolio Highlights

- Environmental and ecosystem simulations written in R with a focus on ODE-based system behavior.
- Applied machine learning workflows in Python for OCR-assisted extraction and ecological forecasting.
- Econometric analysis connecting renewable energy adoption with macroeconomic output.
- Research-oriented code packaged as self-contained project folders with local documentation.

## Verified Execution

The following project entry points were executed in this workspace on March 13, 2026.

- `projects/01-lake-eutrophication-model/src/lake_eutrophication_model.R` ran successfully.
- `projects/02-autocatalytic-reaction-cstr/src/autocatalytic_reaction_cstr.R` ran successfully.
- `projects/03-population-equilibrium-growth-rate/src/population_equilibrium_growth_rate.R` ran successfully.
- `projects/04-sediment-oxygen-dynamics/src/sediment_oxygen_dynamics.R` ran successfully and produced fitted decay-rate output with `k = 231.4519 d^-1`.
- `projects/05-river-flow-distance-analysis/src/river_flow_distance_analysis.R` was executed after adding `coordinates.csv` and `rivers_rlp.gpkg`, but remains blocked by the missing DEM input `dtm_germany_rheinland_pfalz_20m.tif`.
- `projects/06-temperature-species-predation-model/src/temperature_species_predation_model.R` ran successfully.
- `projects/09-phytoplankton-density-prediction/src/phytoplankton_prediction_pipeline.py` ran successfully, regenerated six figures and model result tables for 58 species, and showed Random Forest as the strongest average performer with mean `R2 = 0.678`, ahead of XGBoost (`0.593`) and the Hybrid model (`0.467`).
- `projects/10-carbon-budget-cdr-modeling/src/carbon_budget_optimal_control.py` ran successfully after installing `gekko` and generated `outputs/carbon_budget_optimal_control.png`.
- `projects/11-cement-emissions-analysis/src/pollution_regression_analysis.py` and `projects/11-cement-emissions-analysis/src/cement_cluster_analysis.py` ran successfully on the checked-in transformed dataset, producing `PM2.5 R2 = 0.9757`, `NO2 R2 = 0.9836`, and a clustering stability summary of `383` stable regions versus `18` volatile regions.

Across the validated runs, engineered lag and rolling-window growth features accounted for the largest share of feature importance in the Random Forest results from the phytoplankton thesis pipeline.

## Project Index

| Project | Focus Area | Stack | Entry Point |
| --- | --- | --- | --- |
| [01 Lake Eutrophication Model](projects/01-lake-eutrophication-model/README.md) | Lake nutrient and food-web dynamics with supporting conceptual analyses | R, `deSolve`, `ggplot2` | `src/lake_eutrophication_model.R` |
| [02 Autocatalytic Reaction CSTR](projects/02-autocatalytic-reaction-cstr/README.md) | Flow-through stirred tank kinetics | R | `src/autocatalytic_reaction_cstr.R` |
| [03 Population Equilibrium vs Growth Rate](projects/03-population-equilibrium-growth-rate/README.md) | Periodicity and equilibrium response | R | `src/population_equilibrium_growth_rate.R` |
| [04 Sediment Oxygen Dynamics](projects/04-sediment-oxygen-dynamics/README.md) | Oxygen transport and consumption in sediment | R | `src/sediment_oxygen_dynamics.R` |
| [05 River Flow Distance Analysis](projects/05-river-flow-distance-analysis/README.md) | Along-river and perpendicular distance calculations | R, GIS workflows | `src/river_flow_distance_analysis.R` |
| [06 Temperature and Species Predation Model](projects/06-temperature-species-predation-model/README.md) | Temperature effects in a limiting similarity model | R | `src/temperature_species_predation_model.R` |
| [07 Energy Bill Information Extraction](projects/07-energy-bill-information-extraction/README.md) | OCR plus LLM-based document extraction | Python, OCR, LLM APIs | `src/energy_bill_extraction.py` |
| [08 Renewable Energy Econometrics](projects/08-renewable-energy-econometrics/README.md) | Regression analysis of renewable energy and GDP | Python, `pandas`, `statsmodels` | `src/renewable_energy_econometric_model.py` |
| [09 Phytoplankton Density Prediction](projects/09-phytoplankton-density-prediction/README.md) | Master's thesis ML pipeline for species prediction | Python, `scikit-learn`, `xgboost` | `src/phytoplankton_prediction_pipeline.py` |
| [10 Carbon Budget and CDR Modeling](projects/10-carbon-budget-cdr-modeling/README.md) | Dynamic climate-economy optimization under a carbon budget | Python, `gekko`, `matplotlib` | `src/carbon_budget_optimal_control.py` |
| [11 Cement Emissions Analysis](projects/11-cement-emissions-analysis/README.md) | Regional cement-sector pollution modeling and clustering | Python, `pandas`, `scikit-learn` | `src/pollution_regression_analysis.py` |

## Working Conventions

- Each project folder includes a local `README.md`.
- Source code is grouped under `src/` or `notebooks/`.
- Thesis assets are separated into `data/`, `outputs/`, and `reports/`.
- Secrets should be supplied through environment variables, never hardcoded into notebooks or scripts.
- READMEs summarize results and usage, but they should not be used as raw execution logs.


## Author

Debapratim Mukherjee
