# Lake Eutrophication Model

## Overview

R simulation of lake eutrophication dynamics across multiple nutrient and fishing scenarios.
The consolidated script now includes the main ecosystem simulation plus two supporting analyses that were previously split across separate folders:

- a logistic-growth reference curve for population dynamics
- a nutrient-uptake sensitivity plot for different half-saturation constants

## Stack

- R
- `deSolve`
- `ggplot2`

## Included Analyses

- scenario-based eutrophication simulation for phytoplankton, zooplankton, fish, and phosphorus
- logistic growth reference analysis
- nutrient uptake sensitivity analysis

## Run

Open `src/lake_eutrophication_model.R` in RStudio or run it with `Rscript`.
