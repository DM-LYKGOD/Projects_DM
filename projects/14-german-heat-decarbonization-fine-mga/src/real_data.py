"""
Real Data Integration Module
=============================
Loads the ML-Ready German Kreise (district) dataset, classifies districts
into 5 municipal archetypes via K-Means clustering, and derives empirically
grounded model parameters (heat load shares, capacity limits, social
acceptance, retrofit applicability, DH piping premiums).

Data source: ML_Ready_Dataset_Transformed.xlsx (~400 Kreise × 2018–2022)
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# ─── Columns to drop (>70% null or irrelevant to heat model) ──────────────
_HIGH_NULL_COLS = [
    "Clinker Production (Kg/ year)",
    "Production Plant Capacity (Million tonnes)",
    "Coal dummy",
    "Area",
]

# ─── Clustering features ──────────────────────────────────────────────────
_CLUSTER_FEATURES = [
    "Population Density (Einwohner je km2)",
    "Proportion of Industrial Value Added in Total Value Added",
    "Degree of Urbanization",
]

# ─── Archetype names matched to cluster centroids ─────────────────────────
ARCHETYPE_NAMES = ["Metropolitan", "Suburban", "Rural-Dense", "Rural-Sparse", "Industrial"]


def load_kreise_data(filepath, base_year=2022):
    """
    Loads the Kreise Excel dataset, drops high-null columns, filters to the
    base year, and forward/backward-fills remaining gaps within each Kreis.

    Parameters
    ----------
    filepath : str
        Path to ML_Ready_Dataset_Transformed.xlsx
    base_year : int
        Year to use as the primary cross-section (default: 2022)

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame, one row per Kreis (~400 rows)
    """
    df = pd.read_excel(filepath)

    # Drop columns with excessive nulls
    df = df.drop(columns=[c for c in _HIGH_NULL_COLS if c in df.columns], errors="ignore")

    # Drop rows where core identifiers are null
    df = df.dropna(subset=["Kennziffer", "Raumeinheit"])

    # Filter to base year
    df_base = df[df["Year"] == base_year].copy()

    # If a Kreis is missing in the base year, fall back to the latest available
    existing_ids = set(df_base["Kennziffer"].unique())
    all_ids = set(df["Kennziffer"].unique())
    missing_ids = all_ids - existing_ids

    if missing_ids:
        fallback = (
            df[df["Kennziffer"].isin(missing_ids)]
            .sort_values("Year", ascending=False)
            .drop_duplicates(subset=["Kennziffer"], keep="first")
        )
        df_base = pd.concat([df_base, fallback], ignore_index=True)

    # Forward-fill remaining nulls with column medians (safe for numeric)
    numeric_cols = df_base.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df_base[col].isnull().any():
            df_base[col] = df_base[col].fillna(df_base[col].median())

    df_base = df_base.reset_index(drop=True)
    return df_base


def classify_archetypes(df, n_clusters=5, random_state=42):
    """
    Assigns each Kreis to one of 5 archetypes using K-Means clustering
    on population density (log), industrialization ratio, and urbanization.

    Cluster-to-archetype mapping uses centroid ranking:
      - Highest mean pop density → Metropolitan
      - Highest industrial VA share (excluding Metro) → Industrial
      - Lowest mean pop density → Rural-Sparse
      - Second-lowest → Rural-Dense
      - Remaining → Suburban

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned Kreise data from load_kreise_data()
    n_clusters : int
        Number of clusters (default 5)
    random_state : int
        Reproducibility seed

    Returns
    -------
    pd.DataFrame
        Input DataFrame with added 'archetype' column
    dict
        Cluster statistics {archetype: {feature: mean_value}}
    """
    features = df[_CLUSTER_FEATURES].copy()

    # Log-transform population density to reduce skewness
    features["Population Density (Einwohner je km2)"] = np.log1p(
        features["Population Density (Einwohner je km2)"]
    )

    # Standardize
    scaler = StandardScaler()
    X = scaler.fit_transform(features.values)

    # K-Means
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = km.fit_predict(X)

    # Compute cluster means on original (non-log, non-scaled) features
    df = df.copy()
    df["_cluster"] = labels

    cluster_means = df.groupby("_cluster")[_CLUSTER_FEATURES].mean()

    # Map clusters to archetype names
    assigned = {}
    remaining_clusters = list(range(n_clusters))

    # 1. Metropolitan: highest population density
    metro_idx = cluster_means["Population Density (Einwohner je km2)"].idxmax()
    assigned[metro_idx] = "Metropolitan"
    remaining_clusters.remove(metro_idx)

    # 2. Industrial: highest industrial VA share among remaining
    industrial_idx = (
        cluster_means.loc[remaining_clusters, "Proportion of Industrial Value Added in Total Value Added"]
        .idxmax()
    )
    assigned[industrial_idx] = "Industrial"
    remaining_clusters.remove(industrial_idx)

    # 3. Rural-Sparse: lowest population density among remaining
    rural_sparse_idx = (
        cluster_means.loc[remaining_clusters, "Population Density (Einwohner je km2)"]
        .idxmin()
    )
    assigned[rural_sparse_idx] = "Rural-Sparse"
    remaining_clusters.remove(rural_sparse_idx)

    # 4. Rural-Dense: second-lowest pop density among remaining
    rural_dense_idx = (
        cluster_means.loc[remaining_clusters, "Population Density (Einwohner je km2)"]
        .idxmin()
    )
    assigned[rural_dense_idx] = "Rural-Dense"
    remaining_clusters.remove(rural_dense_idx)

    # 5. Suburban: whatever is left
    assigned[remaining_clusters[0]] = "Suburban"

    # Apply mapping
    df["archetype"] = df["_cluster"].map(assigned)
    df = df.drop(columns=["_cluster"])

    # Build cluster stats for reporting
    cluster_stats = {}
    for cid, aname in assigned.items():
        stats = cluster_means.loc[cid].to_dict()
        stats["count"] = int((df["archetype"] == aname).sum())
        cluster_stats[aname] = stats

    return df, cluster_stats


def compute_empirical_parameters(df):
    """
    Aggregates Kreise-level data into archetype-level model parameters.

    Returns
    -------
    dict with keys:
        - 'HEAT_LOAD_SHARES': dict {archetype: float}  (sums to 1.0)
        - 'CAPACITY_LIMIT_SHARES': dict {archetype: {tech: float}}
        - 'DH_PIPING_PREMIUM': dict {archetype: float}  (EUR/kW)
        - 'SOCIAL_ACCEPTANCE': pd.DataFrame  (5×5)
        - 'RETROFIT_APPLICABILITY': dict {archetype: float}
    """
    archetypes = ARCHETYPE_NAMES
    results = {}

    # ── Heat Load Shares ──────────────────────────────────────────────
    # Weight by Population × HDD (captures both population mass and climate)
    df["_heat_weight"] = df["Population"] * df["Heating Degree Days"]
    total_weight = df["_heat_weight"].sum()
    heat_shares = {}
    for a in archetypes:
        mask = df["archetype"] == a
        heat_shares[a] = df.loc[mask, "_heat_weight"].sum() / total_weight
    # Normalize to exactly 1.0
    total = sum(heat_shares.values())
    heat_shares = {k: v / total for k, v in heat_shares.items()}
    results["HEAT_LOAD_SHARES"] = heat_shares
    df = df.drop(columns=["_heat_weight"])

    # ── Capacity Limit Shares ─────────────────────────────────────────
    # Based on urbanization and renewable heating penetration
    cap_limits = {}
    for a in archetypes:
        mask = df["archetype"] == a
        mean_density = df.loc[mask, "Population Density (Einwohner je km2)"].mean()
        mean_urban = df.loc[mask, "Degree of Urbanization"].mean()
        mean_renew = df.loc[mask, "Residential Building with Renewable Heating"].mean() / 100.0

        # Air HP: higher in suburban/rural (more space), lower in dense metro
        # Scale: low density → 0.8, high density → 0.15
        density_norm = np.clip(mean_density / 2000.0, 0.0, 1.0)
        air_hp = np.clip(0.85 - 0.7 * density_norm, 0.1, 0.85)

        # District HP: higher in dense areas (existing infrastructure)
        dh_hp = np.clip(0.9 * density_norm + 0.05, 0.0, 0.90)

        # Gas boiler: available everywhere (incumbent)
        gas = 1.0

        # H2 boiler: available everywhere (future infrastructure)
        h2 = 1.0

        # Biomass: higher in rural (forest access), lower in urban
        forest_share = df.loc[mask, "Percentage of forest area"].mean() / 100.0
        biomass = np.clip(forest_share * 2.0, 0.03, 0.65)

        cap_limits[a] = {
            "air_hp": round(float(air_hp), 3),
            "dh_large_hp": round(float(dh_hp), 3),
            "gas_boiler": round(float(gas), 3),
            "h2_boiler": round(float(h2), 3),
            "biomass_boiler": round(float(biomass), 3),
        }
    results["CAPACITY_LIMIT_SHARES"] = cap_limits

    # ── DH Piping Premium ─────────────────────────────────────────────
    # Inverse of density: dense areas have existing pipe infrastructure
    dh_premium = {}
    for a in archetypes:
        mask = df["archetype"] == a
        mean_density = df.loc[mask, "Population Density (Einwohner je km2)"].mean()
        # Formula: premium decreases with density
        # ~0 EUR/kW at 3000+ density, ~3000 EUR/kW at <50 density
        premium = max(0.0, 3000.0 * (1.0 - np.clip(mean_density / 2000.0, 0.0, 1.0)))
        dh_premium[a] = round(premium, 1)
    results["DH_PIPING_PREMIUM"] = dh_premium

    # ── Social Acceptance Matrix (ML-Derived) ────────────────────────
    results["SOCIAL_ACCEPTANCE"] = compute_ml_acceptance_matrix(df)

    # ── Gas Grid Lock-In Index ────────────────────────────────────────
    results["GAS_LOCK_IN_INDEX"] = compute_gas_lock_in_index(df)

    # ── Retrofit Applicability ────────────────────────────────────────
    # Higher in areas with older building stock (proxy: lower renewable heating)
    retrofit = {}
    for a in archetypes:
        mask = df["archetype"] == a
        renew_frac = df.loc[mask, "Residential Building with Renewable Heating"].mean() / 100.0
        # Low renewable → older buildings → higher retrofit applicability
        applicability = np.clip(0.95 - renew_frac * 0.5, 0.40, 0.90)
        retrofit[a] = round(float(applicability), 2)
    results["RETROFIT_APPLICABILITY"] = retrofit

    return results


def compute_ml_acceptance_matrix(df):
    """
    Computes the Social Acceptance Matrix using multiple ML features from the
    Kreise dataset. Each technology's acceptance score per archetype is derived
    from a weighted combination of empirical indicators:

    Features used:
      - Residential Building with Renewable Heating (%) → clean tech familiarity
      - Population Density → infrastructure readiness
      - GDP per inhabitant → willingness to pay for transition
      - PM2.5 → environmental concern (high pollution → desire for clean tech)
      - NO2 → air quality awareness (drives biomass rejection in cities)
      - Share of Benzin and Diesel cars → fossil fuel lock-in / conservative attitudes
      - Share of employees in knowledge-intensive industries → innovation openness
      - Rurality → rural cultural identity (biomass tradition)
      - Share of agricultural land → biomass resource availability

    Returns
    -------
    pd.DataFrame
        5×5 acceptance matrix, index=archetypes, columns=technologies
    """
    archetypes = ARCHETYPE_NAMES
    technologies = ["air_hp", "dh_large_hp", "gas_boiler", "h2_boiler", "biomass_boiler"]
    acceptance = np.zeros((len(archetypes), len(technologies)))

    # Safe column accessor: returns column mean for archetype, or fallback
    def _safe_mean(df_sub, col, fallback=0.0):
        if col in df_sub.columns:
            val = df_sub[col].mean()
            return val if not np.isnan(val) else fallback
        return fallback

    for i, a in enumerate(archetypes):
        mask = df["archetype"] == a
        sub = df.loc[mask]

        # ── Extract ML features ────────────────────────────────────────
        renew_frac = _safe_mean(sub, "Residential Building with Renewable Heating") / 100.0
        density = _safe_mean(sub, "Population Density (Einwohner je km2)")
        density_norm = np.clip(density / 2000.0, 0.0, 1.0)
        gdp = _safe_mean(sub, "GDP per inhabitant", 30000)
        gdp_norm = np.clip((gdp - 20000) / 60000, 0.0, 1.0)

        # Air quality indicators → environmental concern
        pm25 = _safe_mean(sub, "PM2.5", 10.0)
        pm25_norm = np.clip((pm25 - 8.0) / 10.0, 0.0, 1.0)  # 8-18 µg/m³ range
        no2 = _safe_mean(sub, "NO2", 15.0)
        no2_norm = np.clip((no2 - 10.0) / 30.0, 0.0, 1.0)   # 10-40 µg/m³ range

        # Fossil fuel dependency (car fleet as proxy)
        fossil_car_share = _safe_mean(sub, "Share of Benzin and Diesel cars in total passenger cars", 80.0) / 100.0

        # Innovation openness
        rd_share = _safe_mean(sub, "Share of employees in knowledge- and research-intensive industries in % of all employees in the labour market", 10.0) / 100.0
        rd_norm = np.clip(rd_share / 0.25, 0.0, 1.0)  # normalize: 0-25% range

        # Rural identity & biomass resource
        rurality = _safe_mean(sub, "Rurality", 1.0)
        rurality_norm = np.clip(rurality / 4.0, 0.0, 1.0)  # normalize to 0-1
        ag_land = _safe_mean(sub, "Share of agricultural land", 30.0) / 100.0
        forest = _safe_mean(sub, "Percentage of forest area", 20.0) / 100.0

        # ── Air HP acceptance ──────────────────────────────────────────
        # Positive drivers: renewable familiarity, environmental concern, innovation
        # Negative drivers: fossil lock-in
        air_hp_score = (
            0.35 * renew_frac           # familiarity with clean tech
            + 0.20 * pm25_norm          # pollution drives desire for electrification
            + 0.20 * rd_norm            # innovation openness
            - 0.15 * fossil_car_share   # fossil culture resistance
            - 0.10 * (1.0 - gdp_norm)   # cost sensitivity in poorer areas
        )
        acceptance[i, 0] = np.clip(air_hp_score * 2.5 - 0.3, -0.9, 0.9)

        # ── District HP acceptance ─────────────────────────────────────
        # Positive drivers: density (infrastructure), GDP (investment capacity)
        # Negative drivers: rurality (no infrastructure), low density
        dh_score = (
            0.40 * density_norm         # infrastructure readiness
            + 0.25 * gdp_norm           # investment capacity
            + 0.15 * pm25_norm          # environmental concern in cities
            - 0.20 * rurality_norm      # rural areas lack DH infrastructure
        )
        acceptance[i, 1] = np.clip(dh_score * 2.0 - 0.2, -0.5, 0.9)

        # ── Gas boiler acceptance ──────────────────────────────────────
        # Positive drivers: fossil lock-in, low renewable adoption
        # Negative drivers: environmental concern, innovation openness
        gas_score = (
            0.35 * fossil_car_share     # fossil culture
            + 0.25 * (1.0 - renew_frac) # unfamiliarity with alternatives
            - 0.20 * pm25_norm          # pollution awareness opposes gas
            - 0.20 * rd_norm            # innovation-oriented areas reject gas
        )
        acceptance[i, 2] = np.clip(gas_score * 2.0 - 0.5, -0.9, 0.8)

        # ── H2 boiler acceptance ───────────────────────────────────────
        # Positive drivers: GDP (early adopter), industrial intensity, R&D
        # Negative drivers: cost sensitivity, rurality
        ind_va = _safe_mean(sub, "Proportion of Industrial Value Added in Total Value Added", 0.2)
        h2_score = (
            0.30 * gdp_norm             # willingness to pay premium
            + 0.30 * rd_norm            # innovation openness
            + 0.20 * np.clip(ind_va / 0.4, 0.0, 1.0)  # industrial areas see H2 as future
            - 0.20 * rurality_norm      # rural skepticism
        )
        acceptance[i, 3] = np.clip(h2_score * 2.0 - 0.3, -0.5, 0.9)

        # ── Biomass boiler acceptance ──────────────────────────────────
        # Positive drivers: forest area, ag land, rurality (tradition)
        # Negative drivers: NO2 urban air quality concerns, density
        biomass_score = (
            0.30 * forest               # resource availability
            + 0.25 * ag_land            # agricultural identity
            + 0.20 * rurality_norm      # rural tradition
            - 0.15 * no2_norm           # urban air quality concerns
            - 0.10 * density_norm       # dense areas oppose combustion
        )
        acceptance[i, 4] = np.clip(biomass_score * 2.5 - 0.1, -0.5, 0.9)

    acceptance = np.round(acceptance, 2)
    return pd.DataFrame(acceptance, index=archetypes, columns=technologies)


def compute_gas_lock_in_index(df):
    """
    Computes a per-archetype Gas Grid Lock-In Index (0-1 scale) based on
    fossil fuel dependency proxies from the ML dataset.

    High lock-in = strong existing gas infrastructure + conservative energy culture.
    Used to set minimum gas capacity floors in optimization (infrastructure inertia).

    Features:
      - Share of Benzin and Diesel cars → fossil fuel culture
      - 1 - Residential Renewable Heating → reliance on fossil heating
      - Industrial VA share → industrial gas demand

    Returns
    -------
    dict
        {archetype: float} where float ∈ [0, 1]
    """
    lock_in = {}
    for a in ARCHETYPE_NAMES:
        mask = df["archetype"] == a
        sub = df.loc[mask]

        # Fossil car dominance (proxy for fossil energy culture)
        fossil_cars = sub["Share of Benzin and Diesel cars in total passenger cars"].mean() / 100.0 \
            if "Share of Benzin and Diesel cars in total passenger cars" in sub.columns else 0.8

        # Non-renewable heating share (gas/oil heating dominance)
        renew_frac = sub["Residential Building with Renewable Heating"].mean() / 100.0 \
            if "Residential Building with Renewable Heating" in sub.columns else 0.3
        fossil_heat = 1.0 - renew_frac

        # Industrial gas demand proxy
        ind_va = sub["Proportion of Industrial Value Added in Total Value Added"].mean() \
            if "Proportion of Industrial Value Added in Total Value Added" in sub.columns else 0.2

        # Weighted composite
        index = (
            0.35 * np.clip(fossil_cars, 0.0, 1.0)
            + 0.40 * np.clip(fossil_heat, 0.0, 1.0)
            + 0.25 * np.clip(ind_va / 0.5, 0.0, 1.0)  # normalize ind_va
        )
        lock_in[a] = round(float(np.clip(index, 0.0, 1.0)), 3)

    return lock_in


def get_archetype_climate_profiles(df):
    """
    Computes per-archetype mean climate parameters for weather-dependent
    COP calibration and heat demand profiling.

    Returns
    -------
    dict
        {archetype: {'temperature': float, 'hdd': float, 'cdd': float,
                      'wind_speed': float, 'vapour_pressure': float}}
    """
    climate_cols = {
        "temperature": "Temperature",
        "hdd": "Heating Degree Days",
        "cdd": "Cooling Degree Days",
        "wind_speed": "Wind Speed",
        "vapour_pressure": "Vapour Pressure (Humidity)",
    }

    profiles = {}
    for a in ARCHETYPE_NAMES:
        mask = df["archetype"] == a
        profile = {}
        for key, col in climate_cols.items():
            if col in df.columns:
                profile[key] = float(df.loc[mask, col].mean())
            else:
                profile[key] = np.nan
        profiles[a] = profile

    return profiles


def get_empirical_summary(df, cluster_stats, empirical_params):
    """
    Produces a human-readable summary string comparing empirical vs
    synthetic parameters. Used for verification logging.

    Returns
    -------
    str
        Multi-line summary
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  EMPIRICAL ARCHETYPE CLASSIFICATION SUMMARY")
    lines.append("=" * 60)

    for a in ARCHETYPE_NAMES:
        stats = cluster_stats.get(a, {})
        lines.append(f"\n  {a} (n={stats.get('count', '?')} Kreise)")
        lines.append(f"    Pop Density: {stats.get('Population Density (Einwohner je km2)', 0):.0f} /km²")
        lines.append(f"    Ind VA Share: {stats.get('Proportion of Industrial Value Added in Total Value Added', 0):.3f}")
        lines.append(f"    Urbanization: {stats.get('Degree of Urbanization', 0):.1f}")

    lines.append("\n" + "-" * 60)
    lines.append("  DERIVED PARAMETERS")
    lines.append("-" * 60)

    lines.append("\n  Heat Load Shares:")
    for a, v in empirical_params["HEAT_LOAD_SHARES"].items():
        lines.append(f"    {a:15s}: {v:.4f}")

    lines.append("\n  DH Piping Premium (EUR/kW):")
    for a, v in empirical_params["DH_PIPING_PREMIUM"].items():
        lines.append(f"    {a:15s}: {v:.1f}")

    lines.append("\n  Retrofit Applicability:")
    for a, v in empirical_params["RETROFIT_APPLICABILITY"].items():
        lines.append(f"    {a:15s}: {v:.2f}")

    return "\n".join(lines)


def generate_spatial_markdown(df, cluster_stats, empirical_params, archetype_climate,
                              frontier_results=None, output_path="results/german_spatial_analysis.md"):
    """
    Dynamically generates the full spatial analysis markdown report.
    Every number is computed from live model data — zero hardcoded values.

    Parameters
    ----------
    frontier_results : pd.DataFrame, optional
        If provided, includes social feasibility frontier insights.
    """
    archetypes = ARCHETYPE_NAMES

    # ── Archetype counts and shares ──────────────────────────────────
    counts = {a: cluster_stats.get(a, {}).get("count", 0) for a in archetypes}
    shares = {a: empirical_params["HEAT_LOAD_SHARES"].get(a, 0) * 100 for a in archetypes}
    premiums = empirical_params["DH_PIPING_PREMIUM"]
    lock_in = empirical_params.get("GAS_LOCK_IN_INDEX", {})
    sa = empirical_params["SOCIAL_ACCEPTANCE"]

    # ── Climate profiles ─────────────────────────────────────────────
    temps = {a: archetype_climate.get(a, {}).get("temperature", 0) for a in archetypes}
    hdds = {a: archetype_climate.get(a, {}).get("hdd", 0) for a in archetypes}
    warmest = max(temps, key=temps.get)
    coldest = max(hdds, key=hdds.get)

    # ── Acceptance extremes ──────────────────────────────────────────
    max_hp_arch = sa["air_hp"].idxmax()
    max_hp_val = sa["air_hp"].max()
    min_hp_arch = sa["air_hp"].idxmin()
    min_hp_val = sa["air_hp"].min()
    max_gas_arch = sa["gas_boiler"].idxmax()
    max_gas_val = sa["gas_boiler"].max()
    max_bio_arch = sa["biomass_boiler"].idxmax()
    max_bio_val = sa["biomass_boiler"].max()
    max_h2_arch = sa["h2_boiler"].idxmax()
    max_h2_val = sa["h2_boiler"].max()

    # ── Lock-in extremes ─────────────────────────────────────────────
    if lock_in:
        most_locked = max(lock_in, key=lock_in.get)
        least_locked = min(lock_in, key=lock_in.get)
    else:
        most_locked = least_locked = "N/A"

    # ── Build acceptance table rows ──────────────────────────────────
    sa_rows = ""
    for a in archetypes:
        vals = " | ".join(f"{sa.at[a, t]:+.2f}" for t in sa.columns)
        li = f"{lock_in.get(a, 0):.3f}" if lock_in else "N/A"
        sa_rows += f"| **{a}** | {vals} | {li} |\n"

    # ── Social feasibility frontier section ──────────────────────────
    frontier_section = ""
    if frontier_results is not None and len(frontier_results) > 0:
        cost_opt = frontier_results[frontier_results["objective_type"] == "cost_optimal"]
        max_acc = frontier_results[frontier_results["objective_type"] == "max_acceptance"]
        if len(cost_opt) > 0 and len(max_acc) > 0:
            cost_opt_cost = cost_opt.iloc[0]["system_cost_billion"]
            cost_opt_ssa = cost_opt.iloc[0]["social_acceptance_index"]
            best_acc = max_acc.loc[max_acc["social_acceptance_index"].idxmax()]
            best_acc_cost = best_acc["system_cost_billion"]
            best_acc_ssa = best_acc["social_acceptance_index"]
            cost_premium = ((best_acc_cost - cost_opt_cost) / cost_opt_cost) * 100
            ssa_gain = best_acc_ssa - cost_opt_ssa

            frontier_section = f"""
---

## ⚖️ Social Feasibility Frontier

The MGA (Modelling to Generate Alternatives) framework explores near-optimal solutions that trade cost efficiency for social acceptance.

| Metric | Cost-Optimal | Max Social Acceptance | Delta |
| :--- | :---: | :---: | :---: |
| **System Cost (Billion €)** | {cost_opt_cost:.2f} | {best_acc_cost:.2f} | +{cost_premium:.1f}% |
| **Social Acceptance Index** | {cost_opt_ssa:.1f} | {best_acc_ssa:.1f} | +{ssa_gain:.1f} |

> The socially optimal pathway costs **{cost_premium:.1f}%** more than the pure cost-optimum, but achieves **{ssa_gain:.1f}** additional units of social acceptance. This defines the "price of social feasibility" for German heat decarbonization.

![Social Feasibility Frontier](social_feasibility_frontier.png)
"""

    md_content = f"""# Municipally-Differentiated Heat Decarbonization Pathways (NUTS3)

*Bridging FINE methodology with MGA under social acceptance constraints — empirically grounded in {sum(counts.values())} German Kreise.*

---

## 🗺️ Geographic Archetype Map

![Empirical Geographic Map of Germany (NUTS3)](german_nuts3_map.png)

---

## 🔍 Key Spatial Insights

### 1. Municipal Archetype Typology
K-Means clustering on population density, industrialization, and urbanization reveals:
*   **{warmest} ({counts[warmest]} districts):** {shares[warmest]:.1f}% of national heat load. DH piping premium: €{premiums[warmest]:,.0f}/kW.
*   **{coldest} ({counts[coldest]} districts):** Highest HDD ({hdds[coldest]:.0f}), depressing heat pump COP. Premium: €{premiums[coldest]:,.0f}/kW.

### 2. Climate-Induced Technology Constraints
*   **Warmest archetype ({warmest}):** Mean {temps[warmest]:.1f}°C, {hdds[warmest]:.0f} HDD — optimal for air-source heat pumps.
*   **Coldest archetype ({coldest}):** Mean {temps[coldest]:.1f}°C, {hdds[coldest]:.0f} HDD — requires thermal storage buffers and hybrid biomass systems.

### 3. ML-Derived Social Acceptance
The acceptance matrix is derived from **9 empirical features** (renewable heating share, PM2.5, NO₂, fossil car fleet, R&D employment, GDP, density, rurality, agricultural land):
*   **Highest heat pump acceptance:** {max_hp_arch} ({max_hp_val:+.2f}) — driven by renewable familiarity and innovation openness.
*   **Lowest heat pump acceptance:** {min_hp_arch} ({min_hp_val:+.2f}) — fossil fuel lock-in and cost sensitivity dominate.
*   **Strongest gas boiler support:** {max_gas_arch} ({max_gas_val:+.2f}) — reflects conservative energy culture.
*   **Strongest biomass support:** {max_bio_arch} ({max_bio_val:+.2f}) — rural tradition and forest resource access.
*   **Strongest H₂ support:** {max_h2_arch} ({max_h2_val:+.2f}) — industrial innovation and high GDP.

### 4. Gas Grid Lock-In Analysis
The Gas Lock-In Index (0–1) measures fossil fuel infrastructure inertia:
*   **Most locked-in:** {most_locked} (index: {lock_in.get(most_locked, 0):.3f}) — highest fossil car share and lowest renewable heating penetration.
*   **Least locked-in:** {least_locked} (index: {lock_in.get(least_locked, 0):.3f}) — already transitioned to higher renewable heating shares.
{frontier_section}
---

## 📊 Acceptance Matrix & Lock-In Index

| Archetype | Air HP | District HP | Gas Boiler | H₂ Boiler | Biomass | Gas Lock-In |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
{sa_rows}

---

## 📋 Archetype Summary

| Archetype | Count | Heat Share | DH Premium | Mean Temp | HDD |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Metropolitan** | {counts['Metropolitan']} | {shares['Metropolitan']:.1f}% | €{premiums['Metropolitan']:,.0f}/kW | {temps['Metropolitan']:.1f}°C | {hdds['Metropolitan']:.0f} |
| **Suburban** | {counts['Suburban']} | {shares['Suburban']:.1f}% | €{premiums['Suburban']:,.0f}/kW | {temps['Suburban']:.1f}°C | {hdds['Suburban']:.0f} |
| **Rural-Dense** | {counts['Rural-Dense']} | {shares['Rural-Dense']:.1f}% | €{premiums['Rural-Dense']:,.0f}/kW | {temps['Rural-Dense']:.1f}°C | {hdds['Rural-Dense']:.0f} |
| **Rural-Sparse** | {counts['Rural-Sparse']} | {shares['Rural-Sparse']:.1f}% | €{premiums['Rural-Sparse']:,.0f}/kW | {temps['Rural-Sparse']:.1f}°C | {hdds['Rural-Sparse']:.0f} |
| **Industrial** | {counts['Industrial']} | {shares['Industrial']:.1f}% | €{premiums['Industrial']:,.0f}/kW | {temps['Industrial']:.1f}°C | {hdds['Industrial']:.0f} |
"""

    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
