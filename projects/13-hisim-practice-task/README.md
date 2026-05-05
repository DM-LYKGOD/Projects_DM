# HiSim Practice Task

ETHOS.HiSim fork for household infrastructure and building energy system simulation practice.

## Project Overview

This repository contains a customized fork of HiSim - a house infrastructure simulator developed by Forschungszentrum Julich. It is used for modeling and simulating residential energy systems including heat pumps, batteries, electric vehicles, and thermal storage.

## Purpose

- Practice working with the HiSim energy system simulation framework
- Learn component-based building energy modeling
- Experiment with household load profiles and smart management strategies

## Key Technologies

- Language: Python 3.10+
- Framework: ETHOS.HiSim (household infrastructure simulator)
- Dependencies: graphviz (optional, for system charts)
- License: MIT

## Repository Structure

HiSim_PracticeTask/
  hisim/                     Main package
    components/            Building energy system components
    modular_household/     Household simulation modules
    inputs/                Input data and profiles
    *.py                  Core simulation engine
  tests/                     Test suite
  system_setups/            Pre-configured system setups
  docs/                      Documentation

## Installation

pip install -e .

## Usage

from hisim import hisim_main

Run a household simulation:
  hisim_main.main()

## References

- Main HiSim Repository: https://github.com/FZJ-IEK3-VSA/HiSim
- Documentation: https://hisim.readthedocs.io
- Funded by: European Union Horizon 2020, Helmholtz Association, FFG (Austria), German Weather Service, NREL

## Author

Forked from FZJ-IEK3-VSA/HiSim
Modified for practice and learning purposes.
