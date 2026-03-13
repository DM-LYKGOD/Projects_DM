# Workspace Documentation

## Scope

This workspace is a portfolio of separate analytical projects. The scripts were reviewed to determine whether they should be merged, kept separate, or rewritten into a cleaner form.

## Consolidation Decisions

| Project | Decision | Reason |
| --- | --- | --- |
| `01-lake-eutrophication-model` | Kept separate | Distinct ecological ODE model with scenario comparison. |
| `02-mathematical-formulations` | Kept separate | Standalone conceptual logistic-growth visualization. |
| `03-parameter-sensitivity-analysis` | Kept separate | Standalone parameter-sweep visualization. |
| `04-autocatalytic-reaction-cstr` | Rebuilt as one complete script | Original file was an incomplete derivative function rather than an executable workflow. |
| `05-population-equilibrium-growth-rate` | Kept separate | Distinct bifurcation and Lyapunov analysis. |
| `06-sediment-oxygen-dynamics` | Deduplicated into one script | Repeated flux and penetration-depth logic was merged into shared functions. |
| `07-river-flow-distance-analysis` | Deduplicated into one script | Planar and elevation-adjusted shortest-path workflows now share the same network helpers. |
| `08-temperature-species-predation-model` | Kept separate | Distinct temperature-dependent community simulation. |
| `09-energy-bill-information-extraction` | Converted to one script | Notebook prototype was replaced with a reusable command-line script. |
| `10-renewable-energy-econometrics` | Kept separate | Distinct regression analysis pipeline. |
| `11-phytoplankton-density-prediction` | Kept separate | Large thesis pipeline already consolidated by topic. |
| `12-carbon-budget-cdr-modeling` | Grouped into one project | Related climate-economy notebooks now live under one project with a canonical GEKKO script. |
| `13-cement-emissions-analysis` | Grouped into one project | The topic stays in one project, with duplicate notebooks removed and analysis split into separate scripts. |

## Script Inventory

### R projects

- `projects/01-lake-eutrophication-model/src/lake_eutrophication_model.R`
  - Purpose: simulate phytoplankton, zooplankton, fish, and phosphorus under multiple nutrient and fishing scenarios.
  - Inputs: parameter blocks defined in-script.
  - Outputs: faceted time-series plot.

- `projects/02-mathematical-formulations/src/mathematical_formulations.R`
  - Purpose: visualize the logistic growth rate curve for a single carrying-capacity setting.
  - Inputs: scalar parameters `r` and `K`.
  - Outputs: one conceptual growth-curve plot.

- `projects/03-parameter-sensitivity-analysis/src/parameter_sensitivity_analysis.R`
  - Purpose: show how the saturation expression changes as `ks` varies.
  - Inputs: food range and parameter grid.
  - Outputs: multi-line sensitivity plot.

- `projects/04-autocatalytic-reaction-cstr/src/autocatalytic_reaction_cstr.R`
  - Purpose: solve and plot an autocatalytic reaction in a continuous stirred-tank reactor.
  - Inputs: dilution rate, reaction rate, inlet concentrations, initial state.
  - Outputs: time-series plot for species `A`, `B`, and `C`.

- `projects/05-population-equilibrium-growth-rate/src/population_equilibrium_growth_rate.R`
  - Purpose: analyze periodicity and chaos in the logistic map.
  - Inputs: growth-rate range and iteration settings.
  - Outputs: bifurcation diagram, Lyapunov plot, and transient trajectory.

- `projects/06-sediment-oxygen-dynamics/src/sediment_oxygen_dynamics.R`
  - Purpose: model oxygen depth profiles, flux, penetration depth, and fit a decay rate to observations.
  - Inputs: diffusion constant, surface oxygen, candidate `k` values, observed depth-oxygen pairs.
  - Outputs: summary table, profile plot, flux-vs-depth plot, and fitted curve.

- `projects/07-river-flow-distance-analysis/src/river_flow_distance_analysis.R`
  - Purpose: compute river-network shortest paths with and without elevation-adjusted edge weights.
  - Inputs: `data/coordinates.csv`, `data/rivers_rlp.gpkg`, `data/dtm_germany_rheinland_pfalz_20m.tif`.
  - Outputs: distance-matrix CSV files and shortest-path PNG plots in `outputs/`.

- `projects/08-temperature-species-predation-model/src/temperature_species_predation_model.R`
  - Purpose: compare baseline and warming scenarios in a temperature-sensitive limiting-similarity model.
  - Inputs: species traits, growth rates, baseline and warming temperatures.
  - Outputs: population-dynamics plots for both temperature scenarios.

### Python projects

- `projects/09-energy-bill-information-extraction/src/energy_bill_extraction.py`
  - Purpose: extract bill text from PDF, run an LLM summary, and save both raw text and final extraction.
  - Inputs: input PDF path and `GROQ_API_KEY`.
  - Outputs: `artifacts/extracted_text.json` and `artifacts/energy_bill_summary.txt`.

- `projects/10-renewable-energy-econometrics/src/renewable_energy_econometric_model.py`
  - Purpose: fit a log-linear econometric model for GDP, capital, labour, and renewable share.
  - Inputs: `data/energy_transition_model_data.xlsx`.
  - Outputs: regression summary printed to stdout.

- `projects/11-phytoplankton-density-prediction/src/phytoplankton_prediction_pipeline.py`
  - Purpose: train and compare Random Forest, XGBoost, and Hybrid models across 58 phytoplankton species.
  - Inputs: `data/greifensee_phytoplankton_2019_2022.csv`.
  - Outputs: figures and model result tables in `outputs/figures/`.

- `projects/12-carbon-budget-cdr-modeling/src/carbon_budget_optimal_control.py`
  - Purpose: solve a carbon-budget constrained optimal control model with fossil, renewable, nuclear, and CDR dynamics.
  - Inputs: command-line parameters for initial pollution, carbon budget, and solver mode.
  - Outputs: optimization plot in `outputs/`.

- `projects/13-cement-emissions-analysis/src/transform_control_variables.py`
  - Purpose: convert the source workbook into a panel dataset suitable for machine learning.
  - Inputs: source Excel workbook.
  - Outputs: transformed Excel dataset.

- `projects/13-cement-emissions-analysis/src/pollution_regression_analysis.py`
  - Purpose: fit a Random Forest model for PM2.5 and NO2 prediction.
  - Inputs: transformed dataset.
  - Outputs: regression metrics and feature-importance CSVs in `outputs/`.

- `projects/13-cement-emissions-analysis/src/cement_cluster_analysis.py`
  - Purpose: cluster regions year-by-year and classify cluster stability.
  - Inputs: transformed dataset and clustering configuration.
  - Outputs: cluster assignments, characteristics, and stability CSVs in `outputs/`.

## Maintenance Guidance

- Keep scripts separate when they represent different scientific questions.
- Consolidate only repeated implementation within the same topic, not across unrelated projects.
- Prefer project-relative file paths over user-specific absolute paths.
- Avoid notebook-only delivery for production-style portfolio work; keep a script as the canonical executable.
