# Debapratim Mukherjee Project Portfolio

This repository is organized as a technical portfolio spanning environmental modeling, applied mathematics, geospatial analysis, machine learning, and econometrics.

## Repository Structure

```text
projects/
  01-lake-eutrophication-model/
  02-mathematical-formulations/
  03-parameter-sensitivity-analysis/
  04-autocatalytic-reaction-cstr/
  05-population-equilibrium-growth-rate/
  06-sediment-oxygen-dynamics/
  07-river-flow-distance-analysis/
  08-temperature-species-predation-model/
  09-energy-bill-information-extraction/
  10-renewable-energy-econometrics/
  11-phytoplankton-density-prediction/
  12-carbon-budget-cdr-modeling/
  13-cement-emissions-analysis/
```

## Portfolio Highlights

- Environmental and ecosystem simulations written in R with a focus on ODE-based system behavior.
- Applied machine learning workflows in Python for OCR-assisted extraction and ecological forecasting.
- Econometric analysis connecting renewable energy adoption with macroeconomic output.
- Research-oriented code packaged as self-contained project folders with local documentation.

## Verified Execution

- The flagship thesis pipeline in `projects/11-phytoplankton-density-prediction` was executed successfully on March 13, 2026 in this workspace.
- That run regenerated six figures and model result tables for 58 species.
- The strongest average performer in the run was Random Forest with mean `R2 = 0.678`, ahead of XGBoost (`0.593`) and the Hybrid model (`0.467`).
- Engineered lag and rolling-window growth features accounted for the largest share of feature importance in the Random Forest runs.

## Project Index

| Project | Focus Area | Stack | Entry Point |
| --- | --- | --- | --- |
| [01 Lake Eutrophication Model](projects/01-lake-eutrophication-model/README.md) | Lake nutrient and food-web dynamics with supporting conceptual analyses | R, `deSolve`, `ggplot2` | `src/lake_eutrophication_model.R` |
| [02 Mathematical Formulations](projects/02-mathematical-formulations/README.md) | Merged into Project 01 | R | `merged into Project 01` |
| [03 Parameter Sensitivity Analysis](projects/03-parameter-sensitivity-analysis/README.md) | Merged into Project 01 | R | `merged into Project 01` |
| [04 Autocatalytic Reaction CSTR](projects/04-autocatalytic-reaction-cstr/README.md) | Flow-through stirred tank kinetics | R | `src/autocatalytic_reaction_cstr.R` |
| [05 Population Equilibrium vs Growth Rate](projects/05-population-equilibrium-growth-rate/README.md) | Periodicity and equilibrium response | R | `src/population_equilibrium_growth_rate.R` |
| [06 Sediment Oxygen Dynamics](projects/06-sediment-oxygen-dynamics/README.md) | Oxygen transport and consumption in sediment | R | `src/sediment_oxygen_dynamics.R` |
| [07 River Flow Distance Analysis](projects/07-river-flow-distance-analysis/README.md) | Along-river and perpendicular distance calculations | R, GIS workflows | `src/river_flow_distance_analysis.R` |
| [08 Temperature and Species Predation Model](projects/08-temperature-species-predation-model/README.md) | Temperature effects in a limiting similarity model | R | `src/temperature_species_predation_model.R` |
| [09 Energy Bill Information Extraction](projects/09-energy-bill-information-extraction/README.md) | OCR plus LLM-based document extraction | Python, OCR, LLM APIs | `src/energy_bill_extraction.py` |
| [10 Renewable Energy Econometrics](projects/10-renewable-energy-econometrics/README.md) | Regression analysis of renewable energy and GDP | Python, `pandas`, `statsmodels` | `src/renewable_energy_econometric_model.py` |
| [11 Phytoplankton Density Prediction](projects/11-phytoplankton-density-prediction/README.md) | Master's thesis ML pipeline for species prediction | Python, `scikit-learn`, `xgboost` | `src/phytoplankton_prediction_pipeline.py` |
| [12 Carbon Budget and CDR Modeling](projects/12-carbon-budget-cdr-modeling/README.md) | Dynamic climate-economy optimization under a carbon budget | Python, `gekko`, `matplotlib` | `src/carbon_budget_optimal_control.py` |
| [13 Cement Emissions Analysis](projects/13-cement-emissions-analysis/README.md) | Regional cement-sector pollution modeling and clustering | Python, `pandas`, `scikit-learn` | `src/pollution_regression_analysis.py` |

## Working Conventions

- Each project folder includes a local `README.md`.
- Source code is grouped under `src/` or `notebooks/`.
- Thesis assets are separated into `data/`, `outputs/`, and `reports/`.
- Secrets should be supplied through environment variables, never hardcoded into notebooks or scripts.
- READMEs summarize results and usage, but they should not be used as raw execution logs.


## Author

Debapratim Mukherjee
