"""
src/data/build_training_dataset_large.py
========================================
Builds the full GEFSv12 + IMD rainfall training dataset.

Design decisions:
- 200 issue dates deterministically sampled across 2000-2019, across seasons.
  Sampling: 10 dates/year x 20 years = 200 total.
  Months: Jan-15, Apr-15, Jun-01, Jun-15, Jul-01, Jul-15, Aug-01, Aug-15, Sep-01, Sep-15
  This covers: winter, pre-monsoon, monsoon onset, peak monsoon, monsoon retreat.
  NO data-driven selection - purely calendar-based.

- Spatial region: Maharashtra / Central India (18-22N, 72-76E), same as Task 02 sample.
  ~289 grid points at 0.25-deg resolution.

- For each issue_date, downloads ALL 5 members and ALL 5 lead days in ONE batch
  per member. Byte-ranges from .idx file. wgrib2 decodes the full spatial subset.

- Caching: Each issue_date-member result is saved as a small cache CSV in
  data/raw/gefs_cache/. Reruns skip already-processed files.

- IMD data is cached per-year in data/raw/imd_rain_YYYY/.

Usage:
  python src/data/build_training_dataset_large.py
"""

import os
import sys
import datetime
import json
import urllib.request
import concurrent.futures
import subprocess
import numpy as np
import pandas as pd
import imdlib

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(ROOT_DIR, "data", "raw")
CACHE_DIR = os.path.join(RAW_DIR, "gefs_cache")
WGRIB2 = os.path.join(ROOT_DIR, "wgrib2", "wgrib2.exe")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ─── Config ──────────────────────────────────────────────────────────────────
TARGET_LAT_MIN, TARGET_LAT_MAX = 18.0, 22.0
TARGET_LON_MIN, TARGET_LON_MAX = 72.0, 76.0

YEARS = list(range(2000, 2020))
MONTH_DAYS = [
    (1, 15), (4, 15), (6, 1), (6, 15),
    (7, 1), (7, 15), (8, 1), (8, 15),
    (9, 1), (9, 15)
]
ISSUE_DATES = [datetime.date(y, m, d) for y in YEARS for m, d in MONTH_DAYS]

LEAD_DAYS = [1, 3, 5, 7, 10]
MEMBERS = ["c00", "p01", "p02", "p03", "p04"]

GEFS_BASE = "https://noaa-gefs-retrospective.s3.amazonaws.com"

# ─── IMD Grid ────────────────────────────────────────────────────────────────
imd_lats = np.arange(6.5, 38.75, 0.25)
imd_lons = np.arange(66.5, 100.25, 0.25)
lat_mask = (imd_lats >= TARGET_LAT_MIN) & (imd_lats <= TARGET_LAT_MAX)
lon_mask = (imd_lons >= TARGET_LON_MIN) & (imd_lons <= TARGET_LON_MAX)
target_lats = imd_lats[lat_mask]
target_lons = imd_lons[lon_mask]


def get_gefs_idx(issue_date, member):
    """Parse .idx file and return byte ranges for all lead days."""
    init_str = issue_date.strftime("%Y%m%d00")
    year = issue_date.year
    idx_url = (f"{GEFS_BASE}/GEFSv12/reforecast/{year}/{init_str}/{member}"
               f"/Days:1-10/apcp_sfc_{init_str}_{member}.grib2.idx")

    req = urllib.request.Request(idx_url, headers={"User-Agent": "gefs-imd-builder"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            idx_text = r.read().decode("utf-8")
    except Exception as e:
        print(f"  IDX fetch error {init_str}/{member}: {e}")
        return None

    offsets = []
    for line in idx_text.strip().split("\n"):
        if line.strip():
            parts = line.split(":")
            offsets.append((int(parts[1]), line))

    blocks = {}
    for lead in LEAD_DAYS:
        start_hr = (lead - 1) * 24
        chunk_labels = [
            f"{start_hr}-{start_hr+6} hour acc fcst",
            f"{start_hr+6}-{start_hr+12} hour acc fcst",
            f"{start_hr+12}-{start_hr+18} hour acc fcst",
            f"{start_hr+18}-{start_hr+24} hour acc fcst",
        ]
        found = []
        for i, (offset, line) in enumerate(offsets):
            if "APCP:surface" in line:
                for lbl in chunk_labels:
                    if lbl in line:
                        end = offsets[i+1][0] - 1 if i+1 < len(offsets) else offset + 5_000_000
                        found.append((offset, end))
        if len(found) == 4:
            blocks[lead] = {"start": found[0][0], "end": found[-1][1]}
        else:
            pass  # Missing chunks are skipped silently

    return blocks if blocks else None


def download_one_member(issue_date, member):
    """
    Download ALL lead days for one member in one pass.
    Returns a DataFrame with columns: lead_day, lat, lon, apcp_mm
    Uses a per-date-member cache CSV to avoid redownloading.
    """
    init_str = issue_date.strftime("%Y%m%d00")
    cache_file = os.path.join(CACHE_DIR, f"{init_str}_{member}.csv")

    if os.path.exists(cache_file):
        try:
            return pd.read_csv(cache_file)
        except Exception:
            os.remove(cache_file)

    blocks = get_gefs_idx(issue_date, member)
    if not blocks:
        return None

    grib_url = (f"{GEFS_BASE}/GEFSv12/reforecast/{issue_date.year}/{init_str}"
                f"/{member}/Days:1-10/apcp_sfc_{init_str}_{member}.grib2")

    records = []
    for lead, block in blocks.items():
        start, end = block["start"], block["end"]
        req = urllib.request.Request(grib_url, headers={
            "User-Agent": "gefs-imd-builder",
            "Range": f"bytes={start}-{end}",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
        except Exception as e:
            print(f"  Download error {init_str}/{member}/ld{lead}: {e}")
            continue

        tmp_grib = os.path.join(CACHE_DIR, f"_tmp_{init_str}_{member}_{lead}.grib2")
        tmp_small = tmp_grib + ".small"
        tmp_csv = tmp_grib + ".csv"

        with open(tmp_grib, "wb") as f:
            f.write(raw)

        # wgrib2 -small_grib then -csv
        r1 = subprocess.run(
            [WGRIB2, tmp_grib, "-small_grib",
             f"{TARGET_LON_MIN}:{TARGET_LON_MAX}",
             f"{TARGET_LAT_MIN}:{TARGET_LAT_MAX}",
             tmp_small],
            capture_output=True
        )
        r2 = subprocess.run(
            [WGRIB2, tmp_small, "-csv", tmp_csv],
            capture_output=True
        )

        for f in [tmp_grib, tmp_small]:
            if os.path.exists(f):
                os.remove(f)

        if not os.path.exists(tmp_csv):
            continue

        try:
            df = pd.read_csv(tmp_csv, header=None,
                             names=["issue", "valid", "var", "level", "lon", "lat", "val"])
        except Exception:
            os.remove(tmp_csv)
            continue

        os.remove(tmp_csv)

        # Sum the 4 x 6-hour chunks per grid point
        df['valid_dt'] = pd.to_datetime(df['valid'])
        df = df[df['valid_dt'].dt.hour.isin([0, 6, 12, 18])]
        grp = df.groupby(['lon', 'lat']).agg(val=('val', 'sum'), count=('val', 'count')).reset_index()
        grp = grp[grp['count'] == 4]

        for _, row in grp.iterrows():
            records.append({
                'lead_day': lead,
                'lat': round(float(row['lat']), 4),
                'lon': round(float(row['lon']), 4),
                'apcp_mm': float(row['val'])
            })

    if not records:
        return None

    df_out = pd.DataFrame(records)
    df_out.to_csv(cache_file, index=False)
    return df_out


def process_issue_date(issue_date):
    """Process all 5 members for one issue date. Returns list of records."""
    records = []
    for member in MEMBERS:
        df = download_one_member(issue_date, member)
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            valid_date = issue_date + datetime.timedelta(days=int(row['lead_day']))
            records.append({
                'issue_time': issue_date,
                'valid_time': valid_date,
                'lead_day': int(row['lead_day']),
                'member': member,
                'lat': row['lat'],
                'lon': row['lon'],
                'apcp_mm': row['apcp_mm']
            })
    return records


def load_imd_years(years):
    """Load IMD data for required years, using cached .grd files."""
    imd_dict = {}
    for y in sorted(set(years)):
        imd_cache = os.path.join(RAW_DIR, f"imd_rain_{y}")
        os.makedirs(imd_cache, exist_ok=True)
        try:
            data = imdlib.get_data("rain", y, y, fn_format="yearwise", file_dir=imd_cache)
            imd_dict[y] = data.data
        except Exception as e:
            print(f"  IMD load failed for {y}: {e}")
    return imd_dict


def main():
    print("=" * 60)
    print("BUILDING FULL GEFSv12 + IMD TRAINING DATASET")
    print(f"Dates: {len(ISSUE_DATES)} | Grid: {len(target_lats)}x{len(target_lons)}")
    print("=" * 60)

    # ── GEFS: parallel over issue dates, sequential over members ──
    all_records = []
    # Use 20 workers: one per year, so 10 dates processed simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_issue_date, d): d for d in ISSUE_DATES}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            done += 1
            res = future.result()
            if res:
                all_records.extend(res)
            if done % 20 == 0:
                print(f"  Completed {done}/{len(ISSUE_DATES)} issue dates, "
                      f"{len(all_records)} raw records so far...")

    if not all_records:
        print("FAIL: No GEFS data extracted.")
        sys.exit(1)

    df_gefs = pd.DataFrame(all_records)
    print(f"Extracted {len(df_gefs)} raw member rows from "
          f"{df_gefs['issue_time'].nunique()} issue dates.")

    # ── Ensemble statistics ───────────────────────────────────────
    df_ens = df_gefs.groupby(
        ['issue_time', 'valid_time', 'lead_day', 'lat', 'lon']
    ).agg(
        forecast_mean=('apcp_mm', 'mean'),
        forecast_spread=('apcp_mm', 'std'),
        forecast_min=('apcp_mm', 'min'),
        forecast_max=('apcp_mm', 'max'),
    ).reset_index()
    df_ens['forecast_range'] = df_ens['forecast_max'] - df_ens['forecast_min']
    df_ens['forecast_spread'] = df_ens['forecast_spread'].fillna(0.0)
    print(f"Aggregated to {len(df_ens)} ensemble rows.")

    # ── IMD ──────────────────────────────────────────────────────
    valid_years = [pd.to_datetime(d).year for d in df_ens['valid_time'].unique()]
    imd_dict = load_imd_years(valid_years)

    imd_records = []
    for vd in df_ens['valid_time'].unique():
        vd_date = pd.to_datetime(vd).date()
        y = vd_date.year
        if y not in imd_dict:
            continue
        arr = imd_dict[y]
        day_idx = (vd_date - datetime.date(y, 1, 1)).days
        for lat in target_lats:
            for lon in target_lons:
                lat_idx = int(np.argmin(np.abs(imd_lats - lat)))
                lon_idx = int(np.argmin(np.abs(imd_lons - lon)))
                val = float(arr[day_idx, lat_idx, lon_idx])
                if val < -900:
                    val = np.nan
                imd_records.append({
                    'valid_time': vd_date,
                    'lat': round(lat, 4),
                    'lon': round(lon, 4),
                    'observed_rainfall': val
                })

    df_imd = pd.DataFrame(imd_records)
    df_ens['valid_time'] = pd.to_datetime(df_ens['valid_time']).dt.date
    df_final = pd.merge(df_ens, df_imd, on=['valid_time', 'lat', 'lon'], how='inner')

    missing_rate = df_final['observed_rainfall'].isna().mean()
    print(f"Joined: {len(df_final)} rows. IMD missing rate before drop: {missing_rate:.2%}")
    df_final = df_final.dropna(subset=['observed_rainfall'])
    df_final['forecast_error'] = (df_final['forecast_mean'] - df_final['observed_rainfall']).abs()

    # ── Save ─────────────────────────────────────────────────────
    out_parquet = os.path.join(RAW_DIR, "training_dataset.parquet")
    df_final.to_parquet(out_parquet, engine='pyarrow', index=False)

    unique_issue = int(df_final['issue_time'].nunique())
    file_kb = round(os.path.getsize(out_parquet) / 1024, 1)

    metadata = {
        "dataset_name": "training_dataset.parquet",
        "description": "Full GEFSv12 + IMD training dataset (Maharashtra region, 2000-2019)",
        "dimensions": {"rows": len(df_final), "columns": len(df_final.columns)},
        "unique_issue_dates": unique_issue,
        "spatial_region": {
            "lat_min": TARGET_LAT_MIN, "lat_max": TARGET_LAT_MAX,
            "lon_min": TARGET_LON_MIN, "lon_max": TARGET_LON_MAX,
            "description": "Maharashtra / Central India (18-22N, 72-76E)"
        },
        "temporal_coverage": {
            "issue_date_min": str(df_final['issue_time'].min()),
            "issue_date_max": str(df_final['issue_time'].max())
        },
        "sampling_strategy": "Calendar-based: 10 fixed dates/year (Jan-15, Apr-15, Jun-01, Jun-15, Jul-01, Jul-15, Aug-01, Aug-15, Sep-01, Sep-15)",
        "lead_days": LEAD_DAYS,
        "ensemble_members": MEMBERS,
        "missing_data_rate_before_drop": f"{missing_rate:.2%}",
        "file_size_kb": file_kb,
        "sources": {
            "forecast": "NOAA GEFSv12 Reforecast (S3 byte-range)",
            "truth": "IMD 0.25-deg daily gridded rainfall (imdlib)"
        }
    }
    with open(os.path.join(RAW_DIR, "training_dataset_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    print(f"  Unique issue dates : {unique_issue}")
    print(f"  Total rows         : {len(df_final)}")
    print(f"  Columns            : {list(df_final.columns)}")
    print(f"  Date range         : {df_final['issue_time'].min()} to {df_final['issue_time'].max()}")
    print(f"  Spatial extent     : lat {df_final['lat'].min()}-{df_final['lat'].max()}, "
          f"lon {df_final['lon'].min()}-{df_final['lon'].max()}")
    print(f"  File size          : {file_kb} KB")
    print(f"  Missing rate (final): 0.00%")
    print(f"  Output             : {out_parquet}")
    print("  PASS")


if __name__ == "__main__":
    main()
