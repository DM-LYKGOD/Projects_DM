# Autocatalytic Reaction CSTR

## Overview

Simulation of an autocatalytic reaction in a continuous stirred-tank reactor with a focus on flow-through reaction behavior.
The script solves the reactor mass-balance equations for species `A`, `B`, and `C` and plots the resulting concentration trajectories.

## Stack

- R
- `deSolve`
- `ggplot2`

## Inputs

- `dilution_rate`
- `reaction_rate`
- inlet concentrations `A_in` and `B_in`
- initial reactor state for `A`, `B`, and `C`

## Outputs

- time-series concentration plot for all three species

## Run

Execute `src/autocatalytic_reaction_cstr.R` with `Rscript` or from an R session.
