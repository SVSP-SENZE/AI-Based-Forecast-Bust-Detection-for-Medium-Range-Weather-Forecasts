"""
scripts/assemble_dataset.py
============================
Assemble training_dataset_sample.parquet from already-cached GEFS CSV files
+ IMD .grd files (cached locally in data/raw/imd_rain_YYYY/).

Run:
    python scripts/assemble_dataset.py

Reads from:
    data/raw/gefs_cache/<YYYYMMDDHH>_<member>.csv  (already computed daily totals)
    data/raw/imd_rain_<YYYY>/rain/<YYYY>.grd        (imdlib yearwise format)

Writes:
    data/raw/training_dataset_sample.parquet
    data/raw/training_dataset_sample_metadata.json
"""

import os
import sys
import json
import datetime
import numpy as np
import pandas as pd
import imdlib

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(ROOT_DIR, "data", "raw")
CACHE_DIR = os.path.join(RAW_DIR, "gefs_cache")

TARGET_LAT_MIN, TARGET_LAT_MAX = 18.0, 22.0
TARGET_LON_MIN, TARGET_LON_MAX = 72.0, 76.0
MEMBERS   = ["c00", "p01", "p02", "p03", "p04"]
LEAD_DAYS = [1, 3, 5, 7, 10]

# IMD grid constants (imdlib yearwise rain: 6.5-38.5N, 66.5-100.0E, 0.25 deg)
IMD_LATS = np.arange(6.5,  38.75, 0.25)
IMD_LONS = np.arange(66.5, 100.25, 0.25)


def discover_issue_dates():
    """Find all unique issue dates that have at least one cached member CSV."""
    files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".csv") and not f.startswith("_")]
    dates = {}
    for f in files:
        parts = f.replace(".csv", "").split("_")
        init_str = parts[0]          # e.g. 2000070100
        member   = parts[1]          # e.g. c00
        issue_date = datetime.date(int(init_str[:4]), int(init_str[4:6]), int(init_str[6:8]))
        if issue_date not in dates:
            dates[issue_date] = []
        dates[issue_date].append(member)
    return sorted(dates.keys())


def load_gefs_for_date(issue_date):
    """Load all cached member CSVs for one issue date. Returns DataFrame."""
    init_str = issue_date.strftime("%Y%m%d00")
    frames = []
    for member in MEMBERS:
        path = os.path.join(CACHE_DIR, f"{init_str}_{member}.csv")
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path)
            # Validate required columns
            if not all(c in df.columns for c in ["lead_day", "lat", "lon", "apcp_mm"]):
                continue
            df["member"] = member
            df["issue_time"] = issue_date
            frames.append(df)
        except Exception as e:
            print(f"  Warning: could not read {path}: {e}")
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def load_imd_year(year):
    """Load IMD rain array for a given year. Returns numpy array or None."""
    imd_cache = os.path.join(RAW_DIR, f"imd_rain_{year}")
    os.makedirs(imd_cache, exist_ok=True)
    try:
        data = imdlib.get_data("rain", year, year, fn_format="yearwise", file_dir=imd_cache)
        arr = data.data   # shape: (days, lats, lons)
        print(f"  IMD {year}: shape={arr.shape}")
        return arr
    except Exception as e:
        print(f"  IMD load failed for {year}: {e}")
        return None


def main():
    print("=" * 60)
    print("ASSEMBLING TRAINING DATASET FROM CACHE")
    print("=" * 60)

    # ── 1. Collect all GEFS records ────────────────────────────────
    issue_dates = discover_issue_dates()
    print(f"Found {len(issue_dates)} cached issue dates: {issue_dates[0]} ... {issue_dates[-1]}")

    all_member_records = []
    for d in issue_dates:
        df = load_gefs_for_date(d)
        if df is not None:
            all_member_records.append(df)

    if not all_member_records:
        print("FAIL: No GEFS cache data found.")
        sys.exit(1)

    df_all = pd.concat(all_member_records, ignore_index=True)
    print(f"Loaded {len(df_all)} raw member-rows from {df_all['issue_time'].nunique()} issue dates.")

    # Validate lead days and precipitation values
    bad_neg = (df_all["apcp_mm"] < 0).sum()
    if bad_neg > 0:
        print(f"  Warning: {bad_neg} negative apcp_mm values found, clipping to 0.")
        df_all["apcp_mm"] = df_all["apcp_mm"].clip(lower=0)

    df_all = df_all[df_all["lead_day"].isin(LEAD_DAYS)]

    # ── 2. Ensemble statistics ──────────────────────────────────────
    df_ens = df_all.groupby(["issue_time", "lead_day", "lat", "lon"]).agg(
        forecast_mean=("apcp_mm", "mean"),
        forecast_spread=("apcp_mm", "std"),
        forecast_min=("apcp_mm", "min"),
        forecast_max=("apcp_mm", "max"),
        member_count=("apcp_mm", "count"),
    ).reset_index()
    df_ens["forecast_range"] = df_ens["forecast_max"] - df_ens["forecast_min"]
    df_ens["forecast_spread"] = df_ens["forecast_spread"].fillna(0.0)

    # Add valid_time
    df_ens["valid_time"] = df_ens.apply(
        lambda r: r["issue_time"] + datetime.timedelta(days=int(r["lead_day"])), axis=1
    )
    print(f"Ensemble aggregation: {len(df_ens)} rows.")

    # ── 3. Load IMD data for required years ─────────────────────────
    valid_years = sorted(set(d.year for d in df_ens["valid_time"].unique()))
    print(f"Loading IMD data for years: {valid_years}")
    imd_cache_dict = {}
    for y in valid_years:
        arr = load_imd_year(y)
        if arr is not None:
            imd_cache_dict[y] = arr

    if not imd_cache_dict:
        print("FAIL: Could not load any IMD data.")
        sys.exit(1)

    # ── 4. Build IMD lookup table ───────────────────────────────────
    lat_mask = (IMD_LATS >= TARGET_LAT_MIN) & (IMD_LATS <= TARGET_LAT_MAX)
    lon_mask = (IMD_LONS >= TARGET_LON_MIN) & (IMD_LONS <= TARGET_LON_MAX)
    target_lats = IMD_LATS[lat_mask]
    target_lons = IMD_LONS[lon_mask]

    imd_records = []
    for vd in sorted(df_ens["valid_time"].unique()):
        y = vd.year
        if y not in imd_cache_dict:
            continue
        arr = imd_cache_dict[y]
        day_idx = (vd - datetime.date(y, 1, 1)).days
        if day_idx < 0 or day_idx >= arr.shape[0]:
            continue
        for lat in target_lats:
            lat_idx = int(np.argmin(np.abs(IMD_LATS - lat)))
            for lon in target_lons:
                lon_idx = int(np.argmin(np.abs(IMD_LONS - lon)))
                val = float(arr[day_idx, lat_idx, lon_idx])
                if val < -900:
                    val = np.nan
                imd_records.append({
                    "valid_time": vd,
                    "lat": round(float(lat), 4),
                    "lon": round(float(lon), 4),
                    "observed_rainfall": val,
                })

    df_imd = pd.DataFrame(imd_records)
    print(f"IMD table: {len(df_imd)} rows.")

    # ── 5. Join ─────────────────────────────────────────────────────
    df_ens["lat"] = df_ens["lat"].round(4)
    df_ens["lon"] = df_ens["lon"].round(4)
    df_imd["lat"] = df_imd["lat"].round(4)
    df_imd["lon"] = df_imd["lon"].round(4)

    df_final = pd.merge(df_ens, df_imd, on=["valid_time", "lat", "lon"], how="inner")
    missing_rate = df_final["observed_rainfall"].isna().mean()
    print(f"After join: {len(df_final)} rows. IMD missing rate: {missing_rate:.2%}")
    df_final = df_final.dropna(subset=["observed_rainfall"])

    # ── 6. Compute forecast error ───────────────────────────────────
    df_final["forecast_error"] = (df_final["forecast_mean"] - df_final["observed_rainfall"]).abs()

    # Final sanity checks
    assert (df_final["forecast_mean"] >= 0).all(),  "Negative GEFS forecast found!"
    assert (df_final["observed_rainfall"] >= 0).all(), "Negative IMD rainfall found!"
    assert df_final.duplicated(subset=["issue_time", "lead_day", "lat", "lon"]).sum() == 0, "Duplicate rows!"

    # ── 7. Save ─────────────────────────────────────────────────────
    out_parquet = os.path.join(RAW_DIR, "training_dataset_sample.parquet")
    df_final.to_parquet(out_parquet, engine="pyarrow", index=False)

    meta = {
        "dataset_name": "training_dataset_sample.parquet",
        "rows": len(df_final),
        "columns": list(df_final.columns),
        "unique_issue_dates": int(df_final["issue_time"].nunique()),
        "issue_date_range": [str(df_final["issue_time"].min()), str(df_final["issue_time"].max())],
        "lead_days": LEAD_DAYS,
        "members": MEMBERS,
        "spatial_region": {"lat": [TARGET_LAT_MIN, TARGET_LAT_MAX], "lon": [TARGET_LON_MIN, TARGET_LON_MAX]},
        "sources": {"forecast": "GEFSv12 Reforecast (S3)", "truth": "IMD 0.25-deg gridded rainfall (imdlib)"},
        "missing_rate_after_drop": "0.00%",
        "file_size_kb": round(os.path.getsize(out_parquet) / 1024, 1),
    }
    with open(os.path.join(RAW_DIR, "training_dataset_sample_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print("\n" + "=" * 60)
    print("DATASET SUMMARY")
    print("=" * 60)
    print(f"  Unique issue dates : {meta['unique_issue_dates']}")
    print(f"  Total rows         : {meta['rows']}")
    print(f"  Columns            : {meta['columns']}")
    print(f"  Issue date range   : {meta['issue_date_range']}")
    print(f"  File size          : {meta['file_size_kb']} KB")
    print(f"  Output             : {out_parquet}")
    print("\nSAMPLE:")
    print(df_final[["issue_time", "valid_time", "lead_day", "lat", "lon",
                     "forecast_mean", "observed_rainfall", "forecast_error"]].head(5).to_string())
    print("\nPASS")


if __name__ == "__main__":
    main()
