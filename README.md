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
  12-ESM-P1-MGA/
```

## Portfolio Highlights

- Environmental and ecosystem simulations written in R with a focus on ODE-based system behavior.
- Applied machine learning workflows in Python for OCR-assisted extraction and ecological forecasting.
- Econometric analysis connecting renewable energy adoption with macroeconomic output.
- PyPSA-based German energy-system MGA workflow for cement-sector flexibility and decarbonisation.
- Research-oriented code packaged as self-contained project folders with local documentation.

## Project Index

| Project | Category | Focus Area | Stack | Entry Point |
| --- | --- | --- | --- | --- |
| [01 Lake Eutrophication Model](projects/01-lake-eutrophication-model/README.md) | Environmental Modeling | Lake nutrient and food-web dynamics with supporting conceptual analyses | R, `deSolve`, `ggplot2` | `src/lake_eutrophication_model.R` |
| [02 Autocatalytic Reaction CSTR](projects/02-autocatalytic-reaction-cstr/README.md) | Applied Mathematical Modeling | Flow-through stirred tank kinetics | R | `src/autocatalytic_reaction_cstr.R` |
| [03 Population Equilibrium vs Growth Rate](projects/03-population-equilibrium-growth-rate/README.md) | Environmental Modeling | Periodicity and equilibrium response | R | `src/population_equilibrium_growth_rate.R` |
| [04 Sediment Oxygen Dynamics](projects/04-sediment-oxygen-dynamics/README.md) | Environmental Modeling | Oxygen transport and consumption in sediment | R | `src/sediment_oxygen_dynamics.R` |
| [05 River Flow Distance Analysis](projects/05-river-flow-distance-analysis/README.md) | Environmental Modeling | Along-river and perpendicular distance calculations | R, GIS workflows | `src/river_flow_distance_analysis.R` |
| [06 Temperature and Species Predation Model](projects/06-temperature-species-predation-model/README.md) | Environmental Modeling | Temperature effects in a limiting similarity model | R | `src/temperature_species_predation_model.R` |
| [07 Energy Bill Information Extraction](projects/07-energy-bill-information-extraction/README.md) | Energy Data Extraction | OCR plus LLM-based document extraction | Python, OCR, LLM APIs | `src/energy_bill_extraction.py` |
| [08 Renewable Energy Econometrics](projects/08-renewable-energy-econometrics/README.md) | Energy Modeling | Regression analysis of renewable energy and GDP | Python, `pandas`, `statsmodels` | `src/renewable_energy_econometric_model.py` |
| [09 Phytoplankton Density Prediction](projects/09-phytoplankton-density-prediction/README.md) | Environmental Modeling | Master's thesis ML pipeline for species prediction | Python, `scikit-learn`, `xgboost` | `src/phytoplankton_prediction_pipeline.py` |
| [10 Carbon Budget and CDR Modeling](projects/10-carbon-budget-cdr-modeling/README.md) | Energy Modeling | Dynamic climate-economy optimization under a carbon budget | Python, `gekko`, `matplotlib` | `src/carbon_budget_optimal_control.py` |
| [11 Cement Emissions Analysis](projects/11-cement-emissions-analysis/README.md) | Environmental Modeling | Regional cement-sector pollution modeling and clustering | Python, `pandas`, `scikit-learn` | `src/pollution_regression_analysis.py` |
| [12 ESM-P1-MGA](projects/12-ESM-P1-MGA/README.md) | Energy Modeling | German cement-energy system modelling with MGA near-optimal alternatives | Python, `pypsa`, `pandas`, `geopandas` | `ESM_P1_MGA_Standalone.ipynb` |

## Working Conventions

- Each project folder includes a local `README.md`.
- Source code is grouped under `src/` or `notebooks/`.
- Thesis assets are separated into `data/`, `outputs/`, and `reports/`.
- Secrets should be supplied through environment variables, never hardcoded into notebooks or scripts.
- READMEs summarize results and usage, but they should not be used as raw execution logs.


## Author

Debapratim Mukherjee
