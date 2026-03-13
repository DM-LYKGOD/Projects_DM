# Carbon Budget and CDR Modeling

## Overview

Portfolio project on dynamic climate-economy modeling with carbon-budget constraints and carbon dioxide removal (CDR) capacity.
This folder combines the original notebook work into one GitHub-ready project with a canonical Python entry point and supporting research notebooks.

## Included Assets

- `src/carbon_budget_optimal_control.py`
  - Main executable script for the GEKKO-based optimal control model.
- `notebooks/climate_model_solver.ipynb`
  - Most complete notebook version with model run narrative.
- `notebooks/cdr_carbon_budget_prototype.ipynb`
  - Earlier prototype notebook.
- `notebooks/cdr_research_scenarios.ipynb`
  - Exploratory notebook with scenario comparisons and additional formulations.

## Dependencies

- Python
- `numpy`
- `matplotlib`
- `gekko`

## Outputs

Running the main script saves:

- `outputs/carbon_budget_optimal_control.png`

## Run

```bash
python src/carbon_budget_optimal_control.py --initial-pollution 400
```

Use `--local-solver` only if GEKKO is installed with a local solver setup.
