# Phytoplankton Density Prediction

## Overview

Master's thesis project focused on predicting phytoplankton density and growth for 58 species in Greifensee using Random Forest, XGBoost, and hybrid modeling strategies.

## Structure

```text
data/
  greifensee_phytoplankton_2019_2022.csv
outputs/
  figures/
reports/
  master_thesis_2025.pdf
src/
  phytoplankton_prediction_pipeline.py
requirements.txt
```

## Questions Addressed

- How predictable are species growth rates at different density levels?
- Which environmental and engineered features drive forecast quality?
- How do baseline and hybrid models compare across species?
- What is lost when lag and rolling-window features are removed?

## Validated Findings

The pipeline was executed successfully in this repository on March 13, 2026 against the committed Greifensee dataset.

- 58 species were processed across Hybrid 2, XGBoost, and Random Forest models.
- Mean out-of-sample `R2` by model was `0.678` for Random Forest, `0.593` for XGBoost, and `0.467` for Hybrid 2.
- Random Forest delivered `R2 > 0.90` for 21 species, compared with 16 for XGBoost and 13 for Hybrid 2.
- The best individual model-species result was `Hybrid 2` on `paradileptus` with `R2 = 0.980`.
- Other standout results included `XGBoost` on `aphanizomenon` (`R2 = 0.978`) and `Random Forest` on `strombidium` (`R2 = 0.969`).
- Model wins by species were: Random Forest `29`, XGBoost `19`, Hybrid 2 `10`.
- Aggregated Random Forest feature importance was dominated by engineered growth-history terms: lag and rolling-window growth features contributed about `0.633` on average, versus `0.241` for density terms, `0.113` for environmental variables, and `0.013` for seasonal terms.
- Among environmental predictors, the strongest average signals were conductivity in the photic zone, total phosphorus, temperature in the photic zone, depth at `5PAR`, and phosphate.

Generated artifacts from that run are available in `outputs/figures/`, including:

- `figure1_density_predictability.png`
- `figure2_r2_heatmap.png`
- `figure3_rf_r2_histogram.png`
- `figure4_feature_importance_by_category.png`
- `figure5_env_feature_importance.png`
- `figure6_ablation_lag_rolling.png`

## Setup

```bash
pip install -r requirements.txt
python src/phytoplankton_prediction_pipeline.py
```

The script reads from `data/` and writes generated figures to `outputs/figures/`.
