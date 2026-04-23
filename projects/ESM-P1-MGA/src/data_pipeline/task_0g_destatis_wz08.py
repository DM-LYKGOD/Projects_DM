"""
task_0g_destatis_wz08.py - Task 0G: Destatis WZ08 Industrial Production
========================================================================
Downloads the monthly production index for cement from Destatis via
dbnomics, computes seasonal weights, and plots the seasonality profile.
"""

import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    CEMENT_SEASONALITY_CSV,
    CEMENT_SEASONALITY_PNG,
    DESTATIS_END_YEAR,
    DESTATIS_START_YEAR,
    DESTATIS_WZ08_CSV,
    FIGURE_DPI,
)

DBNOMICS_DATASETS = [
    "DESTATIS/42153BM004",
    "DESTATIS/42153BM001",
    "DESTATIS/62311BJ001",
]

WZ08_FILTER_TERMS = ["23.5", "235", "Zement", "cement", "23.51"]
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _load_dbnomics_dataset(dataset_id: str) -> "pd.DataFrame | None":
    """Attempt to load a dataset via dbnomics.
    
    Handles API changes across dbnomics versions:
      - fetch_series(dataset_id)   — current API (v0.7+)
      - fetch_dataset(dataset_id)  — old API (removed)
    """
    try:
        import dbnomics
    except ImportError as exc:
        raise ImportError("[0G] dbnomics not installed. Run: pip install dbnomics") from exc

    print(f"[0G]   Trying dataset: {dataset_id} ...")

    # Try fetch_series first (current dbnomics API)
    for fn_name in ("fetch_series", "fetch_dataset"):
        fn = getattr(dbnomics, fn_name, None)
        if fn is None:
            continue
        try:
            df = fn(dataset_id)
            if df is not None and len(df) > 0:
                print(f"[0G]   Loaded via dbnomics.{fn_name}: {len(df)} rows x {len(df.columns)} cols")
                return df
        except Exception as exc:
            print(f"[0G]   {fn_name} failed: {exc}")

    # Last resort: search for cement/Zement series directly
    try:
        provider, dataset = dataset_id.split("/", 1)
        df = dbnomics.fetch_series(provider_code=provider, dataset_code=dataset)
        if df is not None and len(df) > 0:
            print(f"[0G]   Loaded via keyword args: {len(df)} rows")
            return df
    except Exception as exc:
        print(f"[0G]   Keyword fetch failed: {exc}")

    return None


def _filter_cement_series(df: pd.DataFrame) -> pd.DataFrame | None:
    """Filter the dbnomics dataframe to the cement series."""
    for term in WZ08_FILTER_TERMS:
        mask = (
            df.get("series_name", pd.Series(dtype=str)).str.contains(term, case=False, na=False)
            | df.get("series_code", pd.Series(dtype=str)).str.contains(term, case=False, na=False)
        )
        subset = df[mask]
        if len(subset) > 0:
            print(f"[0G]   Found {len(subset)} rows matching '{term}'")
            return subset

    print("[0G] WARNING: Could not isolate cement series by WZ08 code.")
    return None


def _pivot_to_timeseries(df: pd.DataFrame) -> pd.Series:
    """Convert a tidy dbnomics dataframe to a monthly time series."""
    ts_col = next((c for c in ["period", "original_period", "date"] if c in df.columns), None)
    val_col = next((c for c in ["value", "original_value"] if c in df.columns), None)

    if not ts_col or not val_col:
        raise ValueError(f"[0G] Cannot find time/value columns. Available: {list(df.columns)}")

    series = df[[ts_col, val_col]].copy()
    series[ts_col] = pd.to_datetime(series[ts_col])
    series = series.set_index(ts_col)[val_col].sort_index().dropna()

    start = pd.Timestamp(f"{DESTATIS_START_YEAR}-01-01")
    end = pd.Timestamp(f"{DESTATIS_END_YEAR}-12-31")
    series = series.loc[start:end]

    print(f"[0G] Time series: {len(series)} obs | {series.index[0].date()} -> {series.index[-1].date()}")
    return series


def compute_seasonality(series: pd.Series) -> pd.Series:
    """Compute monthly average index normalized to annual mean 1.0."""
    monthly_avg = series.groupby(series.index.month).mean()
    normalized = monthly_avg / monthly_avg.mean()
    normalized.index.name = "month"
    normalized.name = "seasonality_weight"

    print("\n  Cement production seasonality:")
    for month, weight in normalized.items():
        bar = "#" * int(weight * 20)
        print(f"    {MONTH_LABELS[month - 1]:>3}: {weight:.4f}  {bar}")

    return normalized


def plot_seasonality(seasonality: pd.Series, output_path: Path) -> None:
    """Save a bar chart of monthly seasonality weights."""
    fig, ax = plt.subplots(figsize=(10, 5))

    colors = plt.cm.RdYlGn(seasonality.values / seasonality.values.max())
    bars = ax.bar(
        range(1, 13),
        seasonality.values,
        color=colors,
        edgecolor="white",
        linewidth=0.5,
        width=0.7,
    )

    ax.axhline(1.0, color="#333333", linewidth=1.0, linestyle="--", label="Annual mean (= 1.0)")

    for bar, val in zip(bars, seasonality.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.005,
            f"{val:.3f}",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#333333",
        )

    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTH_LABELS, fontsize=10)
    ax.set_xlabel("Month", fontsize=12, labelpad=8)
    ax.set_ylabel("Seasonality Weight (normalized to annual mean = 1.0)", fontsize=11, labelpad=8)
    ax.set_title("German Cement Production - Monthly Seasonality Profile", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylim(0, seasonality.max() * 1.18)
    ax.yaxis.set_minor_locator(mticker.AutoMinorLocator())
    ax.grid(axis="y", linestyle="--", alpha=0.4, linewidth=0.5)
    ax.legend(fontsize=10)

    plt.tight_layout()
    fig.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"[0G] Seasonality chart saved -> {output_path}")


def run_task_0g() -> None:
    """Main entry point for Task 0G."""
    print("\n" + "=" * 60)
    print("  TASK 0G - Destatis WZ08 Cement Seasonality")
    print("=" * 60)

    if DESTATIS_WZ08_CSV.exists() and CEMENT_SEASONALITY_CSV.exists() and CEMENT_SEASONALITY_PNG.exists():
        print(f"[0G] Cached outputs found: {DESTATIS_WZ08_CSV.name}, {CEMENT_SEASONALITY_CSV.name}, {CEMENT_SEASONALITY_PNG.name}. Skipping download.")
        print("\n[0G] -------- TASK 0G COMPLETE (cached) --------\n")
        return

    raw_df = None
    for dataset_id in DBNOMICS_DATASETS:
        raw_df = _load_dbnomics_dataset(dataset_id)
        if raw_df is not None and len(raw_df) > 0:
            break

    if raw_df is None or len(raw_df) == 0:
        raise RuntimeError(
            "[0G] Destatis WZ08 data could not be retrieved. "
            "Synthetic fallback has been removed to avoid fabricated results."
        )

    filtered = _filter_cement_series(raw_df)
    if filtered is None or len(filtered) == 0:
        raise RuntimeError(
            "[0G] Cement series could not be isolated from Destatis WZ08 data. "
            "Synthetic fallback has been removed to avoid fabricated results."
        )

    series = _pivot_to_timeseries(filtered)
    seasonality = compute_seasonality(series)

    series.rename("production_index").to_csv(DESTATIS_WZ08_CSV, header=True)
    seasonality.to_csv(CEMENT_SEASONALITY_CSV, header=True)
    plot_seasonality(seasonality, CEMENT_SEASONALITY_PNG)

    print(f"[0G] Monthly production index saved -> {DESTATIS_WZ08_CSV}")
    print(f"[0G] Seasonality weights saved -> {CEMENT_SEASONALITY_CSV}")


if __name__ == "__main__":
    run_task_0g()
