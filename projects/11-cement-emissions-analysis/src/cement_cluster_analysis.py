import argparse
from pathlib import Path

import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "ml_ready_dataset_transformed.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_CLUSTER_FEATURES = ["Clinker Production (Kg/ year)", "PM2.5", "NO2"]


def load_and_prepare_data(path: Path, feature_mode: str) -> tuple[pd.DataFrame, list[str]]:
    dataset = pd.read_excel(path)
    dataset["Year"] = pd.to_numeric(dataset["Year"], errors="coerce").astype("Int64")
    dataset["Raumeinheit"] = dataset["Raumeinheit"].astype(str)

    if "Clinker Production (Kg/ year)" in dataset.columns:
        dataset["Clinker Production (Kg/ year)"] = pd.to_numeric(
            dataset["Clinker Production (Kg/ year)"], errors="coerce"
        ).fillna(0)

    if feature_mode == "cement-air-quality":
        features = [feature for feature in DEFAULT_CLUSTER_FEATURES if feature in dataset.columns]
    else:
        excluded = {"Year", "Raumeinheit", "Code"}
        features = [
            column
            for column in dataset.select_dtypes(include="number").columns
            if column not in excluded
        ]

    if not features:
        raise ValueError("No usable clustering features were found in the dataset.")

    prepared = dataset.copy()
    for feature in features:
        prepared[feature] = prepared.groupby("Raumeinheit")[feature].transform(lambda series: series.ffill().bfill())
        if prepared[feature].isna().any():
            prepared[feature] = prepared[feature].fillna(prepared[feature].mean())

    prepared = prepared.dropna(subset=["Year", "Raumeinheit"]).copy()
    return prepared, features


def cluster_regions_year_wise(
    dataset: pd.DataFrame,
    features: list[str],
    eps: float,
    min_samples: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    temporal_results = []
    for year in sorted(dataset["Year"].dropna().unique()):
        year_df = dataset[dataset["Year"] == year].copy()
        if len(year_df) < min_samples + 1:
            continue

        scaled = StandardScaler().fit_transform(year_df[features])
        model = DBSCAN(eps=eps, min_samples=min_samples)
        year_df["Cluster"] = model.fit_predict(scaled)
        temporal_results.append(year_df[["Raumeinheit", "Code", "Year", "Cluster"] + features])

    if not temporal_results:
        raise ValueError("No yearly cluster results were produced. Adjust eps/min_samples or inspect the data.")

    long_results = pd.concat(temporal_results, ignore_index=True)
    pivot = long_results.pivot_table(index="Raumeinheit", columns="Year", values="Cluster", aggfunc="first")
    pivot = pivot.sort_index()
    return long_results, pivot


def compute_cluster_status(pivot: pd.DataFrame) -> pd.DataFrame:
    def get_status(row: pd.Series) -> str:
        clusters = row.dropna().tolist()
        if not clusters:
            return "No Data"
        if len(clusters) == 1:
            return "Stable"
        return "Stable" if all(value == clusters[0] for value in clusters) else "Volatile"

    status_df = pivot.copy()
    status_df["Status"] = status_df.apply(get_status, axis=1)
    return status_df


def compute_cluster_characteristics(long_results: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    summary = (
        long_results.groupby(["Year", "Cluster"])[features]
        .agg(["mean", "median"])
        .reset_index()
    )
    summary.columns = [
        "_".join(str(part) for part in column if part)
        if isinstance(column, tuple)
        else str(column)
        for column in summary.columns
    ]
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DBSCAN-based cement-sector regional clustering.")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument(
        "--feature-mode",
        choices=["cement-air-quality", "all-numeric"],
        default="cement-air-quality",
    )
    parser.add_argument("--eps", type=float, default=0.8)
    parser.add_argument("--min-samples", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = args.data_path.resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset, features = load_and_prepare_data(data_path, feature_mode=args.feature_mode)
    long_results, pivot = cluster_regions_year_wise(
        dataset,
        features,
        eps=args.eps,
        min_samples=args.min_samples,
    )
    status_df = compute_cluster_status(pivot)
    characteristics = compute_cluster_characteristics(long_results, features)

    long_path = OUTPUT_DIR / "cement_cluster_assignments.csv"
    status_path = OUTPUT_DIR / "cement_cluster_status.csv"
    characteristics_path = OUTPUT_DIR / "cement_cluster_characteristics.csv"

    long_results.to_csv(long_path, index=False)
    status_df.reset_index().to_csv(status_path, index=False)
    characteristics.to_csv(characteristics_path, index=False)

    print(f"Saved assignments to: {long_path}")
    print(f"Saved stability summary to: {status_path}")
    print(f"Saved cluster characteristics to: {characteristics_path}")


if __name__ == "__main__":
    main()
