# Municipally-Differentiated Heat Decarbonization Pathways (NUTS3)

*Bridging FINE methodology with MGA under social acceptance constraints — empirically grounded in 400 German Kreise.*

---

## 🗺️ Geographic Archetype Map

![Empirical Geographic Map of Germany (NUTS3)](german_nuts3_map.png)

---

## 🔍 Key Spatial Insights

### 1. Municipal Archetype Typology
K-Means clustering on population density, industrialization, and urbanization reveals:
*   **Metropolitan (81 districts):** 37.3% of national heat load. DH piping premium: €827/kW.
*   **Rural-Sparse (99 districts):** Highest HDD (2812), depressing heat pump COP. Premium: €2,832/kW.

### 2. Climate-Induced Technology Constraints
*   **Warmest archetype (Metropolitan):** Mean 12.0°C, 2435 HDD — optimal for air-source heat pumps.
*   **Coldest archetype (Rural-Sparse):** Mean 10.7°C, 2812 HDD — requires thermal storage buffers and hybrid biomass systems.

### 3. ML-Derived Social Acceptance
The acceptance matrix is derived from **9 empirical features** (renewable heating share, PM2.5, NO₂, fossil car fleet, R&D employment, GDP, density, rurality, agricultural land):
*   **Highest heat pump acceptance:** Industrial (+0.90) — driven by renewable familiarity and innovation openness.
*   **Lowest heat pump acceptance:** Suburban (+0.66) — fossil fuel lock-in and cost sensitivity dominate.
*   **Strongest gas boiler support:** Suburban (-0.74) — reflects conservative energy culture.
*   **Strongest biomass support:** Rural-Sparse (+0.90) — rural tradition and forest resource access.
*   **Strongest H₂ support:** Industrial (+0.45) — industrial innovation and high GDP.

### 4. Gas Grid Lock-In Analysis
The Gas Lock-In Index (0–1) measures fossil fuel infrastructure inertia:
*   **Most locked-in:** Industrial (index: 0.347) — highest fossil car share and lowest renewable heating penetration.
*   **Least locked-in:** Rural-Dense (index: 0.263) — already transitioned to higher renewable heating shares.

---

## ⚖️ Social Feasibility Frontier

The MGA (Modelling to Generate Alternatives) framework explores near-optimal solutions that trade cost efficiency for social acceptance.

| Metric | Cost-Optimal | Max Social Acceptance | Delta |
| :--- | :---: | :---: | :---: |
| **System Cost (Billion €)** | 21.77 | 21.22 | +-2.5% |
| **Social Acceptance Index** | 42.9 | 45.3 | +2.4 |

> The socially optimal pathway costs **-2.5%** more than the pure cost-optimum, but achieves **2.4** additional units of social acceptance. This defines the "price of social feasibility" for German heat decarbonization.

![Social Feasibility Frontier](social_feasibility_frontier.png)

---

## 📊 Acceptance Matrix & Lock-In Index

| Archetype | Air HP | District HP | Gas Boiler | H₂ Boiler | Biomass | Gas Lock-In |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Metropolitan** | +0.71 | +0.87 | -0.79 | +0.35 | -0.05 | 0.297 |
| **Suburban** | +0.66 | +0.81 | -0.74 | +0.36 | -0.01 | 0.280 |
| **Rural-Dense** | +0.66 | -0.14 | -0.79 | -0.12 | +0.84 | 0.263 |
| **Rural-Sparse** | +0.72 | -0.16 | -0.82 | -0.01 | +0.90 | 0.272 |
| **Industrial** | +0.90 | +0.08 | -0.90 | +0.45 | +0.78 | 0.347 |


---

## 📋 Archetype Summary

| Archetype | Count | Heat Share | DH Premium | Mean Temp | HDD |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Metropolitan** | 81 | 37.3% | €827/kW | 12.0°C | 2435 |
| **Suburban** | 45 | 6.8% | €1,393/kW | 10.9°C | 2719 |
| **Rural-Dense** | 125 | 29.7% | €2,724/kW | 10.9°C | 2708 |
| **Rural-Sparse** | 99 | 15.4% | €2,832/kW | 10.7°C | 2812 |
| **Industrial** | 50 | 10.8% | €2,458/kW | 10.9°C | 2753 |
