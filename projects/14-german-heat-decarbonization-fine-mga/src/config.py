"""
Configuration file containing techno-economic, spatial, and social parameters
for the Municipally-Differentiated German Heat Decarbonization model.
All costs are estimated in 2045 terms (matching the PhD timeline).
"""

import pandas as pd

# ==============================================================================
# GENERAL & TEMPORAL SETTINGS
# ==============================================================================
TOTAL_GERMAN_HEAT_DEMAND_TWH = 450.0  # TWh/year
CO2_PRICE_2045 = 180.0                # EUR/tCO2
DISCOUNT_RATE = 0.04                  # Social discount rate for FINE annualization

# ==============================================================================
# DATA SOURCING MODE
# ==============================================================================
# "synthetic" → use hand-tuned parameters below (original behaviour)
# "empirical" → derive parameters from real Kreise dataset via K-Means
DATA_MODE = "empirical"
KREISE_DATA_PATH = "ML_Ready_Dataset_Transformed.xlsx"
KREISE_BASE_YEAR = 2022

# ==============================================================================
# TECHNOLOGY SCOPE & TECHNO-ECONOMICS
# ==============================================================================
TECHNOLOGIES = ["air_hp", "dh_large_hp", "gas_boiler", "h2_boiler", "biomass_boiler"]

CAPEX = {
    "air_hp": 1300.0,
    "dh_large_hp": 900.0,
    "gas_boiler": 350.0,
    "h2_boiler": 500.0,
    "biomass_boiler": 950.0,
}

FOM = {
    "air_hp": 0.02,
    "dh_large_hp": 0.015,
    "gas_boiler": 0.015,
    "h2_boiler": 0.02,
    "biomass_boiler": 0.025,
}

LIFETIME = {
    "air_hp": 20,
    "dh_large_hp": 30,
    "gas_boiler": 20,
    "h2_boiler": 20,
    "biomass_boiler": 20,
}

WACC = 0.05

CARRIER_COSTS = {
    "electricity": 120.0,
    "gas": 85.0,
    "hydrogen": 160.0,
    "biomass": 45.0,
}

CO2_EMISSIONS = {
    "gas": 0.202,
    "electricity": 0.0,
    "hydrogen": 0.0,
    "biomass": 0.0,
}

EFFICIENCY = {
    "gas_boiler": 0.92,
    "h2_boiler": 0.88,
    "biomass_boiler": 0.82,
}

# ==============================================================================
# SPATIAL MUNICIPAL ARCHETYPES
# ==============================================================================
ARCHETYPES = ["Metropolitan", "Suburban", "Rural-Dense", "Rural-Sparse", "Industrial"]

HEAT_LOAD_SHARES = {
    "Metropolitan": 0.25,
    "Suburban": 0.35,
    "Rural-Dense": 0.2,
    "Rural-Sparse": 0.1,
    "Industrial": 0.15,
}

CAPACITY_LIMIT_SHARES = {
    "Metropolitan": {"air_hp": 0.15, "dh_large_hp": 0.85, "gas_boiler": 1.0, "h2_boiler": 1.0, "biomass_boiler": 0.05},
    "Suburban": {"air_hp": 0.8, "dh_large_hp": 0.35, "gas_boiler": 1.0, "h2_boiler": 1.0, "biomass_boiler": 0.15},
    "Rural-Dense": {"air_hp": 0.6, "dh_large_hp": 0.15, "gas_boiler": 1.0, "h2_boiler": 1.0, "biomass_boiler": 0.35},
    "Rural-Sparse": {"air_hp": 0.45, "dh_large_hp": 0.0, "gas_boiler": 1.0, "h2_boiler": 1.0, "biomass_boiler": 0.6},
    "Industrial": {"air_hp": 0.4, "dh_large_hp": 0.65, "gas_boiler": 1.0, "h2_boiler": 1.0, "biomass_boiler": 0.1},
}

# Archetype-Specific District Heating Piping CAPEX Premiums (EUR/kW thermal)
# High-density areas have low premiums, sparse areas have extremely high premiums.
DH_PIPING_PREMIUM = {
    "Metropolitan": 0.0,
    "Suburban": 400.0,
    "Rural-Dense": 1200.0,
    "Rural-Sparse": 3000.0,
    "Industrial": 300.0
}

# ==============================================================================
# SOCIAL ACCEPTANCE PARADIGM
# ==============================================================================
SOCIAL_ACCEPTANCE = pd.DataFrame(
    [
        [0.5, 0.8, 0.1, -0.4, 0.2],
        [0.9, 0.4, -0.2, -0.7, 0.7],
        [-0.7, -0.3, 0.4, 0.7, 0.3],
        [0.2, 0.3, 0.5, 0.7, 0.6],
        [-0.9, 0.1, 0.8, 0.9, 0.0],
    ],
    index=ARCHETYPES,
    columns=TECHNOLOGIES,
)

# ==============================================================================
# ECONOMIC MATH FUNCTIONS
# ==============================================================================

# CO2 Cap Sensitivity Sweep Range (MtCO2)
CO2_CAPS_SENSITIVITY = [0.5, 1.0, 2.0, 5.0, 10.0]

# ==============================================================================
# ENDOGENOUS SOCIAL ACCEPTANCE SETTINGS
# ==============================================================================
# Penalty applied per kW of installed capacity for socially rejected technologies
# (negative acceptance score). Makes the optimizer "see" social friction.
ACCEPTANCE_PENALTY_SCALE = 200.0   # EUR/kW base penalty for rejected tech
ACCEPTANCE_BONUS_SCALE = 100.0     # EUR/kW cost reduction for preferred tech

# MGA epsilon grid for social feasibility frontier (finer than legacy)
MGA_EPSILONS = [0.0, 0.05, 0.10, 0.15, 0.20]

# Social feasibility frontier sweep directions
SOCIAL_FEASIBILITY_MODES = {
    "cost_optimal": "Minimize cost (no acceptance)",
    "max_acceptance": "Maximize social acceptance index",
    "min_acceptance": "Minimize social acceptance index (worst-case)",
}

# Gas lock-in: minimum fraction of peak load that must remain gas-capable
# in archetypes with high fossil dependency (relaxed in MGA sweeps)
GAS_LOCK_IN_FLOOR = 0.10  # 10% minimum gas capacity share for locked-in archetypes

# ==============================================================================
# BUILDING RETROFIT SCENARIOS
# ==============================================================================
RETROFIT_SCENARIOS = {
    "no_retrofit":   {"demand_reduction": 0.00, "retrofit_cost_eur_per_kwh": 0.0},
    "moderate":      {"demand_reduction": 0.15, "retrofit_cost_eur_per_kwh": 45.0},
    "deep_retrofit": {"demand_reduction": 0.30, "retrofit_cost_eur_per_kwh": 90.0},
}

# Archetype-specific share of building stock eligible for retrofit (old buildings)
RETROFIT_APPLICABILITY = {
    "Metropolitan": 0.60,
    "Suburban": 0.75,
    "Rural-Dense": 0.80,
    "Rural-Sparse": 0.85,
    "Industrial": 0.50,
}

def get_annuity(capex, lifetime, wacc=0.05):
    if wacc == 0:
        return capex / lifetime
    else:
        return capex * wacc * (1 + wacc)**lifetime / ((1 + wacc)**lifetime - 1)