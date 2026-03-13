# River Flow Distance Analysis

## Overview

GIS-oriented R workflow for measuring shortest-path distances over a river network, first with planar edge lengths and then with elevation-adjusted edge weights.

## Stack

- R
- GIS workflows
- `sf`
- `sfnetworks`
- `terra`
- `ggplot2`

## Required Data

Place these files in `data/` before running the script:

- `coordinates.csv`
- `rivers_rlp.gpkg`
- `dtm_germany_rheinland_pfalz_20m.tif`

## Outputs

The script writes these artifacts to `outputs/`:

- planar distance matrix CSV
- terrain-adjusted distance matrix CSV
- planar shortest-path plot
- terrain-adjusted shortest-path plot

## Run

Execute `src/river_flow_distance_analysis.R` with `Rscript` or from an R session.
