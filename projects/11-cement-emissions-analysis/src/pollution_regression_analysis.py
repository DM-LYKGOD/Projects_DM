import argparse
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "ml_ready_dataset_transformed.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

TARGETS = ["PM2.5", "NO2"]
EXCLUDE_COLUMNS = {"Kennziffer", "Raumeinheit", "Code"}


def load_dataset(path: Path) -> pd.DataFrame:
    dataset = pd.read_excel(path)
    if "Code" in dataset.columns:
        encoder = LabelEncoder()
        dataset["Code_encoded"] = encoder.fit_transform(dataset["Code"].astype(str))
    return dataset


def prepare_features(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictors = [
        column
        for column in dataset.columns
        if column not in EXCLUDE_COLUMNS.union(TARGETS) and pd.api.types.is_numeric_dtype(dataset[column])
    ]
    x = dataset[predictors].fillna(dataset[predictors].median(numeric_only=True))
    y = dataset[TARGETS].dropna()
    x = x.loc[y.index]
    return x, y


def train_model(x: pd.DataFrame, y: pd.DataFrame) -> tuple[RandomForestRegressor, dict[str, float], pd.DataFrame]:
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=300, random_state=42)
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    metrics = {
        "pm25_r2": r2_score(y_test.iloc[:, 0], predictions[:, 0]),
        "no2_r2": r2_score(y_test.iloc[:, 1], predictions[:, 1]),
        "pm25_rmse": mean_squared_error(y_test.iloc[:, 0], predictions[:, 0]) ** 0.5,
        "no2_rmse": mean_squared_error(y_test.iloc[:, 1], predictions[:, 1]) ** 0.5,
        "pm25_mae": mean_absolute_error(y_test.iloc[:, 0], predictions[:, 0]),
        "no2_mae": mean_absolute_error(y_test.iloc[:, 1], predictions[:, 1]),
    }
    feature_importance = (
        pd.DataFrame({"feature": x.columns, "importance": model.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    return model, metrics, feature_importance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a Random Forest model for cement-sector pollution analysis.")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = args.data_path.resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(data_path)
    x, y = prepare_features(dataset)
    _, metrics, feature_importance = train_model(x, y)

    metrics_path = OUTPUT_DIR / "pollution_regression_metrics.csv"
    importance_path = OUTPUT_DIR / "pollution_feature_importance.csv"
    pd.DataFrame([metrics]).to_csv(metrics_path, index=False)
    feature_importance.to_csv(importance_path, index=False)

    print("Model performance:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")
    print(f"Saved metrics to: {metrics_path}")
    print(f"Saved feature importance to: {importance_path}")


if __name__ == "__main__":
    main()
