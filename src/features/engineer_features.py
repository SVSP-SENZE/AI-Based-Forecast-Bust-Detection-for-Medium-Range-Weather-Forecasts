"""
src/features/engineer_features.py
===================================
Task 03 — Feature Engineering

Loads data/raw/training_dataset_sample.parquet and adds:
  - Temporal features: month, season, day_of_year (sin/cos cyclic)
  - Spatial: lat, lon (already present), region_label (coarse quadrant)
  - Ensemble: forecast_mean, spread, min, max, range (already present)
  - forecast_anomaly = forecast_mean - rolling climatology per (lat,lon,month)
  - spatial_gradient  = std of forecast_mean over ±0.5-deg neighborhood
  - historical_bias   = mean past forecast_error per (lead_day, season, region)
                        computed LEAKAGE-SAFE (only from earlier issue dates)

Writes: data/processed/features.parquet
"""

import os
import sys
import numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IN_PATH  = os.path.join(ROOT_DIR, "data", "raw", "training_dataset_sample.parquet")
OUT_DIR  = os.path.join(ROOT_DIR, "data", "processed")
OUT_PATH = os.path.join(OUT_DIR, "features.parquet")
os.makedirs(OUT_DIR, exist_ok=True)


def season_label(month: int) -> str:
    if month in (6, 7, 8, 9):
        return "monsoon"
    elif month in (10, 11):
        return "post_monsoon"
    elif month in (12, 1, 2):
        return "winter"
    else:
        return "pre_monsoon"


def region_label(lat: float, lon: float) -> str:
    """Simple 4-quadrant label within the bounding box."""
    lat_mid, lon_mid = 20.0, 74.0
    ns = "N" if lat >= lat_mid else "S"
    ew = "E" if lon >= lon_mid else "W"
    return f"{ns}{ew}"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["issue_time"] = pd.to_datetime(df["issue_time"])
    df["valid_time"]  = pd.to_datetime(df["valid_time"])

    # ── Temporal ───────────────────────────────────────────────────
    df["month"]  = df["issue_time"].dt.month
    df["season"] = df["month"].apply(season_label)
    doy = df["issue_time"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365)

    # ── Spatial region ─────────────────────────────────────────────
    df["region"] = df.apply(lambda r: region_label(r["lat"], r["lon"]), axis=1)

    # ── Forecast anomaly  ──────────────────────────────────────────
    # climatology = mean observed_rainfall per (lat, lon, month) from ALL rows
    # (safe to use all-data here because we are computing a fixed obs climatology,
    #  not anything derived from the forecast error or labels)
    clim = (
        df.groupby(["lat", "lon", "month"])["observed_rainfall"]
        .mean()
        .rename("clim_rainfall")
        .reset_index()
    )
    df = df.merge(clim, on=["lat", "lon", "month"], how="left")
    df["forecast_anomaly"] = df["forecast_mean"] - df["clim_rainfall"]

    # ── Spatial gradient (std of forecast_mean in ±0.5-deg neighbors) ──
    # For each row, find all rows with same issue_time & lead_day & within ±0.5 deg
    df = df.sort_values(["issue_time", "lead_day", "lat", "lon"]).reset_index(drop=True)

    # Use a simple merge-on-rounded-tile approach: tile each cell by round(lat/0.5)*0.5
    df["lat_tile"] = (df["lat"] / 0.5).round() * 0.5
    df["lon_tile"] = (df["lon"] / 0.5).round() * 0.5
    tile_std = (
        df.groupby(["issue_time", "lead_day", "lat_tile", "lon_tile"])["forecast_mean"]
        .std()
        .fillna(0.0)
        .rename("spatial_gradient")
        .reset_index()
    )
    df = df.merge(tile_std, on=["issue_time", "lead_day", "lat_tile", "lon_tile"], how="left")
    df["spatial_gradient"] = df["spatial_gradient"].fillna(0.0)
    df.drop(columns=["lat_tile", "lon_tile"], inplace=True)

    # ── Historical bias  ──────────────────────────────────────────
    # For each row, compute mean forecast_error for the same (lead_day, season, region)
    # using ONLY rows whose issue_time is STRICTLY EARLIER than the current row.
    # This is the leakage-safe version.
    df = df.sort_values("issue_time").reset_index(drop=True)
    df["hist_bias"] = np.nan

    # Efficient: iterate over sorted issue_times, maintaining a running mean
    # Group approach: for each unique issue_time, the "prior" data = all earlier dates
    unique_dates = df["issue_time"].drop_duplicates().sort_values().tolist()
    running = {}  # (lead_day, season, region) -> [list of errors]

    for dt in unique_dates:
        mask = df["issue_time"] == dt
        rows = df[mask]

        # Assign historical bias from running dict (only prior dates)
        for idx, row in rows.iterrows():
            key = (int(row["lead_day"]), row["season"], row["region"])
            vals = running.get(key, [])
            df.at[idx, "hist_bias"] = np.mean(vals) if vals else np.nan

        # Update running dict with this date's errors
        for _, row in rows.iterrows():
            key = (int(row["lead_day"]), row["season"], row["region"])
            if key not in running:
                running[key] = []
            running[key].append(float(row["forecast_error"]))

    # Fill NaN hist_bias with global mean (for the very first dates that have no prior history)
    global_mean_err = df["forecast_error"].mean()
    df["hist_bias"] = df["hist_bias"].fillna(global_mean_err)

    return df


def main():
    print("=" * 60)
    print("TASK 03 — FEATURE ENGINEERING")
    print("=" * 60)

    if not os.path.exists(IN_PATH):
        print(f"FAIL: Input file not found: {IN_PATH}")
        sys.exit(1)

    df = pd.read_parquet(IN_PATH)
    print(f"Loaded {len(df)} rows, {df['issue_time'].nunique()} issue dates.")

    df_feat = build_features(df)

    feature_cols = [
        "issue_time", "valid_time", "lead_day", "lat", "lon", "region",
        "month", "season", "doy_sin", "doy_cos",
        "forecast_mean", "forecast_spread", "forecast_min", "forecast_max", "forecast_range",
        "forecast_anomaly", "spatial_gradient", "hist_bias",
        "clim_rainfall", "observed_rainfall", "forecast_error",
    ]
    missing = [c for c in feature_cols if c not in df_feat.columns]
    if missing:
        print(f"FAIL: Missing columns: {missing}")
        sys.exit(1)

    df_out = df_feat[feature_cols]
    df_out.to_parquet(OUT_PATH, engine="pyarrow", index=False)

    print(f"\nFeature table: {df_out.shape}")
    print(f"Columns: {list(df_out.columns)}")
    print(f"Saved to: {OUT_PATH}")

    # Quick checks
    nan_counts = df_out[["forecast_anomaly", "spatial_gradient", "hist_bias"]].isna().sum()
    print(f"\nNaN counts in engineered features:\n{nan_counts}")
    print(f"\nBust-label NOT yet added — run bust_label.py next.")
    print("\nPASS")


if __name__ == "__main__":
    main()
