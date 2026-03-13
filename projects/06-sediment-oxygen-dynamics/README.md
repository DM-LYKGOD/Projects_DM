# Sediment Oxygen Dynamics

## Overview

Environmental modeling project focused on oxygen transport, diffusion, and consumption in sediment layers.
The consolidated script now handles profile simulation, flux and penetration-depth summaries, and parameter fitting against observed oxygen data.

## Stack

- R
- `minpack.lm` for nonlinear fitting

## Inputs

- diffusion coefficient
- surface oxygen concentration
- candidate decay rates `k`
- observed depth and oxygen measurements for the fitted profile

## Outputs

- oxygen depth profile plot for multiple decay-rate scenarios
- oxygen flux versus penetration-depth plot
- fitted decay-rate estimate and fitted-profile plot

## Run

Execute `src/sediment_oxygen_dynamics.R` with `Rscript` or from an R session.
