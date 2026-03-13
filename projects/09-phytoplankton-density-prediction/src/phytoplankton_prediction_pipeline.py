from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBClassifier, XGBRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error, accuracy_score
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILE_PATH = PROJECT_ROOT / "data" / "greifensee_phytoplankton_2019_2022.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EPS = 1e-9
TRAIN_RATIO = 0.8

ENV_PREDICTORS = [
    'mean_Temp_photic', 'mean_O2_photic', 'mean_CondF_photic', 'mean_depth_at_5PAR',
    'mean_air_temperature', 'mean_windspeed', 'max_windspeed', 'precipitation_tot',
    'mean_rel_humidity', 'mean_average_global_radiation',
    'nitrate', 'ammonium', 'TN', 'TP', 'phosphate'
]



def validate_train_test_split(X_train, X_test, y_train, y_test, dates_train, dates_test, species_name):
    """Validate train/test split has no data leakage. Matches original scripts exactly."""
    # Check 1: No index overlap
    train_indices = set(y_train.index)
    test_indices = set(y_test.index)
    if train_indices.intersection(test_indices):
        raise ValueError(f"DATA LEAKAGE: overlapping indices for {species_name}!")

    # Check 2: Temporal separation
    if dates_test.min() <= dates_train.max():
        raise ValueError(f"TEMPORAL LEAKAGE: Test dates overlap train dates for {species_name}!")

    # Check 3: Size consistency
    if len(y_train) + len(y_test) != len(X_train) + len(X_test):
        raise ValueError(f"DATA INCONSISTENCY for {species_name}: Mismatch in total data size!")

    # Check 4: No duplicate feature rows between train and test (exact match to original scripts)
    train_df = pd.DataFrame(X_train)
    test_df = pd.DataFrame(X_test)
    train_hashes = set(pd.util.hash_pandas_object(train_df, index=False))
    test_hashes = set(pd.util.hash_pandas_object(test_df, index=False))
    hash_overlap = train_hashes.intersection(test_hashes)
    if len(hash_overlap) > 0:
        raise ValueError(
            f"DATA LEAKAGE DETECTED for {species_name}: "
            f"{len(hash_overlap)} duplicate feature rows found between train and test sets!"
        )

    return {
        'train_size': len(y_train), 'test_size': len(y_test),
        'train_date_range': (dates_train.min(), dates_train.max()),
        'test_date_range': (dates_test.min(), dates_test.max()),
        'temporal_gap_days': (dates_test.min() - dates_train.max()).days
    }



def load_and_prepare_data(file_path):
    """Load CSV, detect species columns, interpolate, compute dt."""
    print("Loading data...")
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'], dayfirst=True)
    df = df.sort_values('date').reset_index(drop=True)

    all_columns = df.columns.tolist()
    start_idx = all_columns.index('date') + 1
    end_idx = all_columns.index(ENV_PREDICTORS[0])
    species_list = all_columns[start_idx:end_idx]
    print(f"Found {len(species_list)} species.")

    cols_to_interp = ENV_PREDICTORS + species_list
    df[cols_to_interp] = df[cols_to_interp].interpolate(method='linear', limit_direction='both')
    df['dt'] = df['date'].diff().dt.days.fillna(1)
    return df, species_list


def temporal_split(data, growth_col, feature_cols, train_ratio, species):
    """Perform a strict temporal train/test split."""
    split_idx = int(len(data) * train_ratio)
    X = data[feature_cols].values
    y = data[growth_col]
    dates = data['date']
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    dates_train, dates_test = dates.iloc[:split_idx], dates.iloc[split_idx:]
    validate_train_test_split(X_train, X_test, y_train, y_test, dates_train, dates_test, species)
    return X_train, X_test, y_train, y_test, dates_test


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

def create_enhanced_features_hybrid_xgb(df, species):
    """
    Feature engineering for Hybrid2 and XGBoost models.
    Uses the shared df - same logic as hybrid2_all_58_species.py and xgb_regression_all_58_species.py
    """
    df_out = df.copy()
    growth_col = f'{species}_growth'

    # Growth rate
    df_out[growth_col] = np.log((df_out[species].shift(-1) + EPS) / (df_out[species] + EPS)) / df_out['dt']

    for lag in [1, 2, 3, 7]:
        df_out[f'{growth_col}_lag{lag}'] = df_out[growth_col].shift(lag)

    for window in [7, 14]:
        df_out[f'{growth_col}_rolling_mean_{window}d'] = df_out[growth_col].rolling(window).mean()
        df_out[f'{growth_col}_rolling_std_{window}d'] = df_out[growth_col].rolling(window).std()

    df_out['month'] = df_out['date'].dt.month
    df_out['day_of_year'] = df_out['date'].dt.dayofyear
    df_out['month_sin'] = np.sin(2 * np.pi * df_out['month'] / 12)
    df_out['month_cos'] = np.cos(2 * np.pi * df_out['month'] / 12)

    df_out[f'{species}_density'] = df_out[species]
    df_out[f'{species}_density_lag1'] = df_out[species].shift(1)

    return df_out, growth_col


def create_clean_features_rf(df, species):
    """
    Feature engineering for RF Clean model.
    Isolates each species to prevent cross-species feature leakage.
    Matches rf_regression_all_58_species_clean.py exactly.
    """
    df_out = df[['date'] + ENV_PREDICTORS + [species]].copy()
    df_out['dt'] = df['dt']
    growth_col = f'{species}_growth'
    df_out[growth_col] = np.log((df_out[species].shift(-1) + EPS) / (df_out[species] + EPS)) / df_out['dt']

    for lag in [1, 2, 3, 7]:
        df_out[f'{species}_growth_lag{lag}'] = df_out[growth_col].shift(lag)

    for window in [7, 14]:
        df_out[f'{species}_growth_rolling_mean_{window}d'] = df_out[growth_col].rolling(window).mean()
        df_out[f'{species}_growth_rolling_std_{window}d'] = df_out[growth_col].rolling(window).std()

    df_out['month'] = df_out['date'].dt.month
    df_out['day_of_year'] = df_out['date'].dt.dayofyear
    df_out['month_sin'] = np.sin(2 * np.pi * df_out['month'] / 12)
    df_out['month_cos'] = np.cos(2 * np.pi * df_out['month'] / 12)

    df_out[f'{species}_density'] = df_out[species]
    df_out[f'{species}_density_lag1'] = df_out[species].shift(1)

    feature_cols = (
        ENV_PREDICTORS +
        [f'{species}_growth_lag{lag}' for lag in [1, 2, 3, 7]] +
        [f'{species}_growth_rolling_mean_{w}d' for w in [7, 14]] +
        [f'{species}_growth_rolling_std_{w}d' for w in [7, 14]] +
        ['month_sin', 'month_cos', 'day_of_year', 'month'] +
        [f'{species}_density', f'{species}_density_lag1']
    )
    return df_out, growth_col, feature_cols


# =============================================================================
# MODEL TRAINING
# =============================================================================

def create_growth_categories(growth_rate):
    """Create 3 growth categories - exact logic from hybrid2 script."""
    threshold = growth_rate.std() * 0.25
    categories = pd.cut(growth_rate,
                        bins=[-np.inf, -threshold, threshold, np.inf],
                        labels=['Decline', 'Stable', 'Growth'])
    return categories


def train_hybrid2(X_train, y_train, X_test, y_test, species_name, feature_names):
    """
    Train Hybrid 2: XGBoost classifier + per-category XGBoost regressors.
    Exact logic from hybrid2_all_58_species.py.
    """
    y_train_cat = create_growth_categories(y_train)
    y_test_cat = create_growth_categories(y_test)

    le = LabelEncoder()
    y_train_cat_num = le.fit_transform(y_train_cat.astype(str))
    y_test_cat_num = le.transform(y_test_cat.astype(str))

    classifier = XGBClassifier(n_estimators=100, random_state=0, eval_metric='logloss', n_jobs=-1)
    classifier.fit(X_train, y_train_cat_num)
    y_pred_cat = classifier.predict(X_test)
    cat_accuracy = accuracy_score(y_test_cat_num, y_pred_cat)
    feature_importance = classifier.feature_importances_

    final_pred = np.zeros(len(y_test))
    for cat_code in range(len(le.classes_)):
        train_mask = (y_train_cat_num == cat_code)
        test_mask = (y_pred_cat == cat_code)
        if train_mask.sum() > 10 and test_mask.sum() > 0:
            X_train_cat = X_train[train_mask]
            y_train_cat_vals = y_train.values[train_mask]
            reg = XGBRegressor(n_estimators=100, random_state=0, n_jobs=-1)
            reg.fit(X_train_cat, y_train_cat_vals)
            final_pred[test_mask] = reg.predict(X_test[test_mask])

    return {
        'species': species_name, 'r2': r2_score(y_test, final_pred),
        'mae': mean_absolute_error(y_test, final_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, final_pred)),
        'predictions': final_pred, 'y_test': y_test.values,
        'cat_accuracy': cat_accuracy,
        'feature_importance': dict(zip(feature_names, feature_importance))
    }


def train_xgb_regression(X_train, y_train, X_test, y_test, species_name, feature_names):
    """
    Pure XGBoost regression.
    Exact logic from xgb_regression_all_58_species.py.
    """
    regressor = XGBRegressor(n_estimators=100, random_state=0, n_jobs=-1, learning_rate=0.1, max_depth=6)
    regressor.fit(X_train, y_train)
    y_pred = regressor.predict(X_test)
    return {
        'species': species_name, 'r2': r2_score(y_test, y_pred),
        'mae': mean_absolute_error(y_test, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
        'predictions': y_pred, 'y_test': y_test.values,
        'feature_importance': dict(zip(feature_names, regressor.feature_importances_))
    }


def train_rf_regression(X_train, y_train, X_test, y_test, species_name, feature_names):
    """
    Random Forest regression (clean, no leakage).
    Exact hyperparameters from rf_regression_all_58_species_clean.py.
    """
    regressor = RandomForestRegressor(
        n_estimators=100, random_state=0, n_jobs=-1,
        max_depth=10, min_samples_split=5, min_samples_leaf=2
    )
    regressor.fit(X_train, y_train)
    y_pred = regressor.predict(X_test)
    return {
        'species': species_name, 'r2': r2_score(y_test, y_pred),
        'mae': mean_absolute_error(y_test, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
        'predictions': y_pred, 'y_test': y_test.values,
        'feature_importance': dict(zip(feature_names, regressor.feature_importances_))
    }


# =============================================================================
# RUN ALL THREE MODELS
# =============================================================================

def run_all_models(df, species_list):
    """Run Hybrid2, XGBoost, and RF across all species. Returns results dfs."""

    hybrid2_results, xgb_results, rf_results = [], [], []
    rf_feature_importance_list = []

    print("\n" + "="*70)
    print("TRAINING ALL THREE MODELS ACROSS ALL SPECIES")
    print("="*70)


    df_shared = df.copy()

    for i, species in enumerate(species_list):
        print(f"\n[{i+1}/{len(species_list)}] Processing: {species}")
        growth_col = f'{species}_growth'

        # Compute growth rate 
        df_shared[growth_col] = (
            np.log((df_shared[species].shift(-1) + EPS) / (df_shared[species] + EPS))
            / df_shared['dt']
        )

        # --- HYBRID 2 ---
        try:
            df_h = df_shared.copy()
            for lag in [1, 2, 3, 7]:
                df_h[f'{growth_col}_lag{lag}'] = df_h[growth_col].shift(lag)
            for window in [7, 14]:
                df_h[f'{growth_col}_rolling_mean_{window}d'] = df_h[growth_col].rolling(window).mean()
                df_h[f'{growth_col}_rolling_std_{window}d'] = df_h[growth_col].rolling(window).std()
            df_h['month'] = df_h['date'].dt.month
            df_h['day_of_year'] = df_h['date'].dt.dayofyear
            df_h['month_sin'] = np.sin(2 * np.pi * df_h['month'] / 12)
            df_h['month_cos'] = np.cos(2 * np.pi * df_h['month'] / 12)
            df_h[f'{species}_density'] = df_h[species]
            df_h[f'{species}_density_lag1'] = df_h[species].shift(1)

            mask = ((df_h[growth_col] >= df_h[growth_col].quantile(0.01)) &
                    (df_h[growth_col] <= df_h[growth_col].quantile(0.99)))
            data = df_h[mask].copy()
           
            feature_cols = ENV_PREDICTORS + [
                col for col in data.columns
                if ('lag' in col or 'rolling' in col or 'sin' in col or 'cos' in col or
                    'month' in col or 'dens' in col) and col != growth_col
            ]
            data = data.dropna(subset=feature_cols + [growth_col])
            if len(data) >= 100:
                X_train, X_test, y_train, y_test, dates_test = temporal_split(
                    data, growth_col, feature_cols, TRAIN_RATIO, species)
                res = train_hybrid2(X_train, y_train, X_test, y_test, species, feature_cols)
                hybrid2_results.append({'Species': species, 'R2': res['r2'],
                                        'MAE': res['mae'], 'RMSE': res['rmse']})
                print(f"  Hybrid2  R2={res['r2']:.4f}")
        except Exception as e:
            print(f"  Hybrid2  ERROR: {e}")

        # --- XGBoost ---
        try:
            df_x = df_shared.copy()
            for lag in [1, 2, 3, 7]:
                df_x[f'{growth_col}_lag{lag}'] = df_x[growth_col].shift(lag)
            for window in [7, 14]:
                df_x[f'{growth_col}_rolling_mean_{window}d'] = df_x[growth_col].rolling(window).mean()
                df_x[f'{growth_col}_rolling_std_{window}d'] = df_x[growth_col].rolling(window).std()
            df_x['month'] = df_x['date'].dt.month
            df_x['day_of_year'] = df_x['date'].dt.dayofyear
            df_x['month_sin'] = np.sin(2 * np.pi * df_x['month'] / 12)
            df_x['month_cos'] = np.cos(2 * np.pi * df_x['month'] / 12)
            df_x[f'{species}_density'] = df_x[species]
            df_x[f'{species}_density_lag1'] = df_x[species].shift(1)

            mask = ((df_x[growth_col] >= df_x[growth_col].quantile(0.01)) &
                    (df_x[growth_col] <= df_x[growth_col].quantile(0.99)))
            data = df_x[mask].copy()
            feature_cols = ENV_PREDICTORS + [
                col for col in data.columns
                if ('lag' in col or 'rolling' in col or 'sin' in col or 'cos' in col or
                    'month' in col or 'dens' in col) and col != growth_col
            ]
            data = data.dropna(subset=feature_cols + [growth_col])
            if len(data) >= 100:
                X_train, X_test, y_train, y_test, dates_test = temporal_split(
                    data, growth_col, feature_cols, TRAIN_RATIO, species)
                res = train_xgb_regression(X_train, y_train, X_test, y_test, species, feature_cols)
                xgb_results.append({'Species': species, 'R2': res['r2'],
                                    'MAE': res['mae'], 'RMSE': res['rmse']})
                print(f"  XGBoost  R2={res['r2']:.4f}")
        except Exception as e:
            print(f"  XGBoost  ERROR: {e}")

        # --- RF Clean (isolated per-species, no cross-species) ---
        try:
            df_sp, growth_col_rf, feature_cols = create_clean_features_rf(df, species)
            mask = ((df_sp[growth_col_rf] >= df_sp[growth_col_rf].quantile(0.01)) &
                    (df_sp[growth_col_rf] <= df_sp[growth_col_rf].quantile(0.99)))
            data = df_sp[mask].dropna(subset=feature_cols + [growth_col_rf])
            if len(data) >= 100:
                X_train, X_test, y_train, y_test, dates_test = temporal_split(
                    data, growth_col_rf, feature_cols, TRAIN_RATIO, species)
                res = train_rf_regression(X_train, y_train, X_test, y_test, species, feature_cols)
                rf_results.append({'Species': species, 'R2': res['r2'],
                                   'MAE': res['mae'], 'RMSE': res['rmse'],
                                   'mean_density': df[species].mean()})
                imp_row = {'Species': species}
                imp_row.update(res['feature_importance'])
                rf_feature_importance_list.append(imp_row)
                print(f"  RF       R2={res['r2']:.4f}")
        except Exception as e:
            print(f"  RF       ERROR: {e}")

    hybrid2_df = pd.DataFrame(hybrid2_results).sort_values('R2', ascending=False) if hybrid2_results else pd.DataFrame()
    xgb_df = pd.DataFrame(xgb_results).sort_values('R2', ascending=False) if xgb_results else pd.DataFrame()
    rf_df = pd.DataFrame(rf_results).sort_values('R2', ascending=False) if rf_results else pd.DataFrame()
    rf_importance_df = pd.DataFrame(rf_feature_importance_list) if rf_feature_importance_list else pd.DataFrame()

    return hybrid2_df, xgb_df, rf_df, rf_importance_df


# =============================================================================
# ABLATION STUDY (Figure 6)
# =============================================================================

def run_ablation_all_models(df, species_list, hybrid2_df, xgb_df, rf_df):
    """
    Runs all 3 models WITHOUT lag and rolling features (ablation).
    Returns merged dataframe with full and ablated R2 for each species x model.
    """
    ablation_results = []
    print("\nRunning ablation study (all 3 models without lag/rolling)...")

    for species in species_list:
        row = {'Species': species}
        try:
            # --- shared ablated feature set (env only + temporal + density) ---
            df_out = df[['date'] + ENV_PREDICTORS + [species]].copy()
            df_out['dt'] = df['dt']
            growth_col = f'{species}_growth'
            df_out[growth_col] = np.log((df_out[species].shift(-1) + EPS) / (df_out[species] + EPS)) / df_out['dt']
            df_out['month'] = df_out['date'].dt.month
            df_out['day_of_year'] = df_out['date'].dt.dayofyear
            df_out['month_sin'] = np.sin(2 * np.pi * df_out['month'] / 12)
            df_out['month_cos'] = np.cos(2 * np.pi * df_out['month'] / 12)
            df_out[f'{species}_density'] = df_out[species]
            df_out[f'{species}_density_lag1'] = df_out[species].shift(1)

            feature_cols_ablated = (
                ENV_PREDICTORS +
                ['month_sin', 'month_cos', 'day_of_year', 'month'] +
                [f'{species}_density', f'{species}_density_lag1']
            )
            mask = ((df_out[growth_col] >= df_out[growth_col].quantile(0.01)) &
                    (df_out[growth_col] <= df_out[growth_col].quantile(0.99)))
            data = df_out[mask].dropna(subset=feature_cols_ablated + [growth_col])
            if len(data) < 100:
                continue

            X_train, X_test, y_train, y_test, _ = temporal_split(data, growth_col, feature_cols_ablated, TRAIN_RATIO, species)

            # RF ablated
            rf_res = train_rf_regression(X_train, y_train, X_test, y_test, species, feature_cols_ablated)
            row['RF_ablated'] = rf_res['r2']

            # XGBoost ablated
            xgb_res = train_xgb_regression(X_train, y_train, X_test, y_test, species, feature_cols_ablated)
            row['XGBoost_ablated'] = xgb_res['r2']

            # Hybrid2 ablated
            hybrid_res = train_hybrid2(X_train, y_train, X_test, y_test, species, feature_cols_ablated)
            row['Hybrid2_ablated'] = hybrid_res['r2']

            ablation_results.append(row)
        except Exception:
            continue

    ablation_df = pd.DataFrame(ablation_results) if ablation_results else pd.DataFrame()
    return ablation_df


# =============================================================================
# FIGURE GENERATION
# =============================================================================

def fig_feature_importance_by_category(rf_importance_df):
    """
    Figure 4: Average feature importance across species by category.
    Exact logic from rf_regression_all_58_species_clean.py (mean-based).
    """
    feature_type_importance = {
        'Environmental': [], 'Growth Lag': [], 'Growth Rolling Mean': [],
        'Growth Rolling Std': [], 'Temporal': [], 'Species Density': []
    }
    for _, row in rf_importance_df.iterrows():
        species = row['Species']
        for col, val in row.items():
            if col == 'Species' or pd.isna(val):
                continue
            if col in ENV_PREDICTORS:
                feature_type_importance['Environmental'].append(val)
            elif 'rolling_mean' in col:
                feature_type_importance['Growth Rolling Mean'].append(val)
            elif 'rolling_std' in col:
                feature_type_importance['Growth Rolling Std'].append(val)
            elif 'lag' in col:
                feature_type_importance['Growth Lag'].append(val)
            elif col in ['month_sin', 'month_cos', 'day_of_year', 'month']:
                feature_type_importance['Temporal'].append(val)
            elif 'density' in col:
                feature_type_importance['Species Density'].append(val)

    type_means = {k: np.mean(v) for k, v in feature_type_importance.items() if v}
    sorted_types = sorted(type_means.items(), key=lambda x: x[1], reverse=True)
    types_sorted = [t[0] for t in sorted_types]
    means_sorted = [t[1] for t in sorted_types]

    color_map = {
        'Species Density': '#2ecc71', 'Growth Rolling Mean': '#3498db',
        'Growth Lag': '#e74c3c', 'Growth Rolling Std': '#f39c12',
        'Environmental': '#9b59b6', 'Temporal': '#1abc9c'
    }
    bar_colors = [color_map.get(c, '#95a5a6') for c in types_sorted]

    fig, ax = plt.subplots(figsize=(10, 6))
    y_pos = np.arange(len(types_sorted))
    ax.barh(y_pos, means_sorted, color=bar_colors, height=0.75, edgecolor='none')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(types_sorted, fontsize=12)
    ax.set_xlabel('Average Feature Importance', fontsize=13)
    ax.set_title('Feature Importance by Category (Average Across All Species)', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_color('black'); spine.set_linewidth(0.8); spine.set_visible(True)
    plt.tight_layout()
    outpath = OUTPUT_DIR / 'figure4_feature_importance_by_category.png'
    plt.savefig(outpath, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Saved: {outpath}")
    return feature_type_importance


def fig_env_feature_importance(feature_type_importance):
    """
    Figure 5: Relative importance of environmental drivers.
    Exact logic from rf_regression_all_58_species_clean.py.
    """
    env_entries = feature_type_importance.get('Environmental', [])
    if not env_entries:
        print("No environmental importance data - skipping Figure 5.")
        return

    # Rebuild per-feature means
    env_feature_vals = {}
    print("Warning: Figure 5 needs feature-level breakdown. Using mean of category.")


def fig_env_feature_importance_v2(rf_importance_df):
    """
    Figure 5 (correct): Average of each individual environmental feature.
    """
    env_feature_vals = {}
    for _, row in rf_importance_df.iterrows():
        for col in ENV_PREDICTORS:
            if col in row and not pd.isna(row[col]):
                if col not in env_feature_vals:
                    env_feature_vals[col] = []
                env_feature_vals[col].append(row[col])

    env_avg = {k: np.mean(v) for k, v in env_feature_vals.items()}
    env_sorted = sorted(env_avg.items(), key=lambda x: x[1], reverse=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    y_pos = range(len(env_sorted))
    ax.barh(y_pos, [e[1] for e in env_sorted], color='#3498db')
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels([e[0] for e in env_sorted], fontsize=11)
    ax.set_xlabel('Average Feature Importance', fontsize=13)
    ax.set_title('Relative Importance of Environmental Drivers\n(Average Across All Species, RF Model)', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    plt.tight_layout()
    outpath = OUTPUT_DIR / 'figure5_env_feature_importance.png'
    plt.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {outpath}")


def fig_density_predictability(rf_df):
    """
    Figure 1: Species density vs predictability scatter.
    X axis = mean species density (log scale), Y axis = R2.
    """
    if rf_df.empty or 'mean_density' not in rf_df.columns:
        print("No data for Figure 1 - skipping.")
        return

    fig, ax = plt.subplots(figsize=(10, 7))
    scatter = ax.scatter(
        rf_df['mean_density'], rf_df['R2'],
        c=rf_df['R2'], cmap='RdYlGn', s=80, alpha=0.85, edgecolors='grey', linewidth=0.5
    )
    plt.colorbar(scatter, ax=ax, label='R² Score')
    ax.set_xscale('log')
    ax.set_xlabel('Mean Species Density (log scale)', fontsize=13)
    ax.set_ylabel('R² Score', fontsize=13)
    ax.set_title('Figure 1. Species Density – Predictability Trade-off', fontsize=14, fontweight='bold')
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='R²=0')
    ax.axhline(y=0.5, color='green', linestyle='--', alpha=0.5, label='R²=0.5')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    outpath = OUTPUT_DIR / 'figure1_density_predictability.png'
    plt.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {outpath}")


def fig_r2_heatmap(hybrid2_df, xgb_df, rf_df):
    """
    Figure 2: Species-specific R² heatmap across all 3 models.
    Green = better, Red = worse. Sorted by mean R² descending.
    Annotated with rounded values.
    """
    merged = None
    for df_m, label in [(hybrid2_df, 'Hybrid 2'), (xgb_df, 'XGBoost'), (rf_df, 'Random Forest')]:
        if df_m.empty:
            continue
        tmp = df_m[['Species', 'R2']].rename(columns={'R2': label})
        if merged is None:
            merged = tmp
        else:
            merged = merged.merge(tmp, on='Species', how='outer')

    if merged is None or merged.empty:
        print("No data for Figure 2 - skipping.")
        return

    model_cols = [c for c in ['Hybrid 2', 'XGBoost', 'Random Forest'] if c in merged.columns]
    merged['mean_R2'] = merged[model_cols].mean(axis=1)
    merged = merged.sort_values('mean_R2', ascending=False).drop(columns='mean_R2')
    merged = merged.set_index('Species')
    heatmap_data = merged[model_cols]

    fig_height = max(12, len(heatmap_data) * 0.35)
    fig, ax = plt.subplots(figsize=(10, fig_height))

    sns.heatmap(
        heatmap_data,
        ax=ax,
        cmap='RdYlGn',
        center=0,
        vmin=-1.2, vmax=1.0,
        annot=True,
        fmt='.3f',
        annot_kws={'size': 8},
        linewidths=0.3,
        linecolor='white',
        cbar_kws={'label': 'R² Score', 'shrink': 0.6}
    )
    ax.set_title('R² Scores Across All Models and Species\n(Green = Better, Red = Worse)',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('Model Type', fontsize=11)
    ax.set_ylabel('Species', fontsize=11)
    ax.tick_params(axis='y', labelsize=8)
    plt.tight_layout()
    outpath = OUTPUT_DIR / 'figure2_r2_heatmap.png'
    plt.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {outpath}")


def fig_rf_r2_histogram(rf_df):
    """
    Figure 3: Histogram of R² scores for Random Forest regression only.
    Orange bars, yellow KDE, red zero line, green mean line.
    """
    if rf_df.empty:
        print("No RF data for Figure 3 - skipping.")
        return

    mean_r2 = rf_df['R2'].mean()
    fig, ax = plt.subplots(figsize=(10, 6))

    sns.histplot(rf_df['R2'], bins=20, kde=True, color='#f0a500',
                 line_kws={'color': '#f0a500', 'linewidth': 2}, ax=ax)

    ax.axvline(x=0, color='red', linestyle='--', linewidth=1.5, label='R²=0')
    ax.axvline(x=mean_r2, color='green', linestyle='--', linewidth=1.5,
               label=f'Mean: {mean_r2:.3f}')

    ax.set_xlabel('R² Score', fontsize=13)
    ax.set_ylabel('Count', fontsize=13)
    ax.set_title('Distribution of R² Scores - Random Forest Regression (All 58 Species)',
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(False)
    plt.tight_layout()
    outpath = OUTPUT_DIR / 'figure3_rf_r2_histogram.png'
    plt.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {outpath}")


def fig_ablation_heatmaps(hybrid2_df, xgb_df, rf_df, ablation_df):
    """
    Figure 6: Two side-by-side heatmaps.
    Left:  Top 20 species WITH lag & rolling (full model R² for all 3 models)
    Right: Same species WITHOUT lag & rolling (ablated R²)
    Sorted by RF full R² descending. Color: RdYlGn.
    """
    if ablation_df.empty:
        print("No ablation data for Figure 6 - skipping.")
        return

    # Build full-model merged table
    full_merged = None
    for df_m, label in [(hybrid2_df, 'Hybrid 2'), (xgb_df, 'XGBoost'), (rf_df, 'Random Forest')]:
        if df_m.empty:
            continue
        tmp = df_m[['Species', 'R2']].rename(columns={'R2': label})
        if full_merged is None:
            full_merged = tmp
        else:
            full_merged = full_merged.merge(tmp, on='Species', how='outer')

    if full_merged is None or full_merged.empty:
        print("No full-model data for Figure 6 - skipping.")
        return

    # Build ablated table
    ablation_renamed = ablation_df.rename(columns={
        'Hybrid2_ablated': 'Hybrid 2',
        'XGBoost_ablated': 'XGBoost',
        'RF_ablated': 'Random Forest'
    })

    # Merge full and ablated on Species
    both = full_merged.merge(ablation_renamed[['Species', 'Hybrid 2', 'XGBoost', 'Random Forest']],
                             on='Species', how='inner',
                             suffixes=('_full', '_ablated'))

    model_cols_full = ['Hybrid 2_full', 'XGBoost_full', 'Random Forest_full']
    model_cols_abl = ['Hybrid 2_ablated', 'XGBoost_ablated', 'Random Forest_ablated']

    # Sort by RF full R2 descending, take top 20
    both = both.sort_values('Random Forest_full', ascending=False).head(20)
    both = both.set_index('Species')

    full_data = both[model_cols_full].rename(columns={
        'Hybrid 2_full': 'Hybrid 2', 'XGBoost_full': 'XGBoost', 'Random Forest_full': 'Random Forest'
    })
    abl_data = both[model_cols_abl].rename(columns={
        'Hybrid 2_ablated': 'Hybrid 2', 'XGBoost_ablated': 'XGBoost', 'Random Forest_ablated': 'Random Forest'
    })

    fig_height = max(10, len(full_data) * 0.45)
    fig, axes = plt.subplots(1, 2, figsize=(18, fig_height))

    common_kws = dict(
        cmap='RdYlGn', center=0, vmin=-1.4, vmax=1.0,
        annot=True, fmt='.3f', annot_kws={'size': 8},
        linewidths=0.3, linecolor='white',
        cbar_kws={'label': 'R² Score', 'shrink': 0.6}
    )

    sns.heatmap(full_data, ax=axes[0], **common_kws)
    axes[0].set_title('WITH Lag & Rolling Features\n(Top 20 Species)', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Model', fontsize=11)
    axes[0].set_ylabel('Species', fontsize=11)
    axes[0].tick_params(axis='y', labelsize=9)

    sns.heatmap(abl_data, ax=axes[1], **common_kws)
    axes[1].set_title('WITHOUT Lag & Rolling Features\n(Same Species)', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Model', fontsize=11)
    axes[1].set_ylabel('Species', fontsize=11)
    axes[1].tick_params(axis='y', labelsize=9)

    plt.suptitle('Figure 6. Removing lag and rolling features causes a sharp drop in model performance',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    outpath = OUTPUT_DIR / 'figure6_ablation_lag_rolling.png'
    plt.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {outpath}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    # 1. Load data
    df, species_list = load_and_prepare_data(FILE_PATH)

    # 2. Train all models
    hybrid2_df, xgb_df, rf_df, rf_importance_df = run_all_models(df, species_list)

    # 3. Save raw results
    for df_res, name in [(hybrid2_df, 'hybrid2'), (xgb_df, 'xgb'), (rf_df, 'rf_clean')]:
        if not df_res.empty:
            df_res.to_csv(OUTPUT_DIR / f'{name}_all_species_results.csv', index=False)

    if not rf_importance_df.empty:
        rf_importance_df.to_csv(OUTPUT_DIR / 'rf_feature_importance_by_species.csv', index=False)

    # 4. Ablation for Figure 6
    ablation_df = run_ablation_all_models(df, species_list, hybrid2_df, xgb_df, rf_df)

    # Figure 1: Density-predictability scatter
    fig_density_predictability(rf_df)

    # Figure 2: R² heatmap across all species x 3 models
    fig_r2_heatmap(hybrid2_df, xgb_df, rf_df)

    # Figure 3: RF R² histogram (orange bars)
    fig_rf_r2_histogram(rf_df)

    # Figure 4: Feature importance by category (RF)
    if not rf_importance_df.empty:
        feature_type_importance = fig_feature_importance_by_category(rf_importance_df)
        # Figure 5: Individual environmental feature importance (RF)
        fig_env_feature_importance_v2(rf_importance_df)

    # Figure 6: Two side-by-side heatmaps (with vs without lag/rolling)
    fig_ablation_heatmaps(hybrid2_df, xgb_df, rf_df, ablation_df)

    print("\n" + "="*70)
    print("ALL FIGURES GENERATED SUCCESSFULLY")
    print("="*70)
    print(f"Output directory: {OUTPUT_DIR}")
    print("Files created:")
    for path in sorted(OUTPUT_DIR.iterdir()):
        if path.name.startswith('figure'):
            print(f"  {path.name}")
    print("="*70)


if __name__ == "__main__":
    main()
