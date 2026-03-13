# Cement Emissions Analysis

## Overview

Portfolio project on regional cement-industry and air-pollution analysis.
The original notebooks were consolidated into a cleaner GitHub-ready structure with one canonical data-transformation script, one regression-analysis script, and one clustering-analysis script.

## Included Assets

- `src/transform_control_variables.py`
  - Reshapes the original wide-format Excel workbook into a panel dataset.
- `src/pollution_regression_analysis.py`
  - Trains a Random Forest model for `PM2.5` and `NO2`.
- `src/cement_cluster_analysis.py`
  - Runs year-wise DBSCAN clustering and produces stability summaries.
- `notebooks/cement_industry_analysis.ipynb`
  - Original modeling notebook.
- `notebooks/cement_cluster_analysis.ipynb`
  - Original clustering notebook.

## Deduplication

- `Cement Industry (1).ipynb` was not copied into the repository because it is an exact duplicate of `Cement Industry.ipynb`.

## Required Data

Place these files in `data/` as needed:

- raw wide-format workbook used for transformation
- `ml_ready_dataset_transformed.xlsx` for regression and clustering runs

## Outputs

Scripts write CSV outputs to `outputs/`, including model metrics, feature importance, and cluster assignments.

## Run

```bash
python src/transform_control_variables.py path/to/ControlVariables_Final2.xlsx
python src/pollution_regression_analysis.py
python src/cement_cluster_analysis.py --feature-mode cement-air-quality
```
