"""
scripts/gefs_imd_verification.py
==================================
Targeted scientific feasibility verification:

  REAL GEFSv12 HISTORICAL FORECAST
  -> REAL IMD HISTORICAL RAINFALL
  -> REAL FORECAST ERROR

Case: GEFSv12 reforecast 2000-01-01 00Z (c00 control member)
      Day 1 (24-hr) accumulated precipitation over Mumbai area

Strategy:
  A. GEFS: byte-range download the four 6-hourly APCP messages (0-6h, 6-12h,
     12-18h, 18-24h) = Day 1 total. 
     Decode using pre-compiled wgrib2.exe (downloaded locally).
  B. IMD: use imdlib to download year 2000 daily gridded rainfall (.grd binary).
     Extract the value for 2000-01-02 (valid date = issue + 1 day) at the
     grid cell nearest to Mumbai (19.0N, 72.8E).
  C. Compute absolute error: |GEFS_Day1 - IMD|.
"""

import os
import sys
import subprocess
import datetime
import urllib.request
import numpy as np
import imdlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
WGRIB2 = os.path.join(ROOT, "wgrib2", "wgrib2.exe")
os.makedirs(RAW_DIR, exist_ok=True)

# Constants
ISSUE_DATETIME  = datetime.datetime(2000, 1, 1, 0)
VALID_DATE      = datetime.date(2000, 1, 2)
MEMBER          = "c00"
TARGET_LAT      = 19.0
TARGET_LON      = 72.8

GEFS_BASE = "https://noaa-gefs-retrospective.s3.amazonaws.com"
INIT_STR  = "2000010100"
GRIB_KEY  = (f"GEFSv12/reforecast/2000/{INIT_STR}/{MEMBER}/Days:1-10/"
             f"apcp_sfc_{INIT_STR}_{MEMBER}.grib2")

DAY1_MSGS = [
    {"label": "0-6h",   "start": 422515,   "end": 925322},
    {"label": "6-12h",  "start": 1330399,  "end": 1592088},
    {"label": "12-18h", "start": 2014842,  "end": 2290260},
    {"label": "18-24h", "start": 2721180,  "end": 2995906},
]
SEP = "-" * 62

def byte_range_get(url, byte_start, byte_end):
    req = urllib.request.Request(url, headers={
        "User-Agent": "gefs-imd-feasibility",
        "Range": f"bytes={byte_start}-{byte_end}",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def fetch_gefs_day1():
    print(f"\n{SEP}")
    print("A. GEFS Day 1 Precipitation (byte-range + wgrib2 decode)")
    print(SEP)

    grib_url = f"{GEFS_BASE}/{GRIB_KEY}"
    accum_values = {}
    
    # Download the 4 messages into a single grib file
    combined_grib = os.path.join(RAW_DIR, "day1_apcp.grib2")
    with open(combined_grib, "wb") as f_out:
        for msg in DAY1_MSGS:
            label = msg["label"]
            start, end = msg["start"], msg["end"]
            print(f"  Fetching {label}: bytes {start}-{end}")
            raw = byte_range_get(grib_url, start, end)
            f_out.write(raw)
            
    # Decode to CSV using wgrib2
    csv_file = os.path.join(RAW_DIR, "day1_apcp.csv")
    print(f"  Decoding with wgrib2 -> {csv_file}")
    
    # Extract point values near Mumbai (lon 72.8, lat 19.0)
    cmd = [WGRIB2, combined_grib, "-lon", str(TARGET_LON), str(TARGET_LAT)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  [FAIL] wgrib2 failed: {result.stderr}")
        return None, accum_values
        
    lines = result.stdout.strip().split("\n")
    day1_total = 0.0
    
    for i, line in enumerate(lines):
        # wgrib2 -lon output format:
        # 1:0:d=2000010100:APCP:surface:0-6 hour acc fcst:ENS=low-res ctl:lon=72.750000,lat=19.000000,val=0
        parts = line.split(":")
        label = DAY1_MSGS[i]["label"]
        val_str = parts[-1].split("val=")[-1]
        try:
            val = float(val_str)
            accum_values[label] = val
            day1_total += val
            print(f"  {label} -> {val:.3f} mm")
        except:
            print(f"  Could not parse val from: {line}")
            
    print(f"\n  Day 1 GEFS total = {day1_total:.3f} mm")
    return day1_total, accum_values


def fetch_imd_day1():
    print(f"\n{SEP}")
    print("B. IMD 0.25-degree Daily Gridded Rainfall (imdlib)")
    print(SEP)

    imd_lats = np.arange(6.5, 38.75, 0.25)
    imd_lons = np.arange(66.5, 100.25, 0.25)
    
    lat_idx = int(np.argmin(np.abs(imd_lats - TARGET_LAT)))
    lon_idx = int(np.argmin(np.abs(imd_lons - TARGET_LON)))
    
    imd_cache = os.path.join(RAW_DIR, "imd_rain_2000")
    os.makedirs(imd_cache, exist_ok=True)
    
    try:
        data = imdlib.get_data("rain", 2000, 2000, fn_format="yearwise", file_dir=imd_cache)
        arr = data.data
        day_idx = (VALID_DATE - datetime.date(2000, 1, 1)).days
        val = float(arr[day_idx, lat_idx, lon_idx])
        
        # Handle IMD missing value (-999.0)
        if val < -900:
            val = np.nan
            
        print(f"  IMD rainfall at ({imd_lats[lat_idx]:.2f}N, {imd_lons[lon_idx]:.2f}E)")
        print(f"  on {VALID_DATE} = {val:.3f} mm")
        return val
    except Exception as e:
        print(f"  [FAIL] imdlib: {e}")
        return None

def main():
    print("=" * 62)
    print("GEFS-IMD SCIENTIFIC FEASIBILITY VERIFICATION")
    print(f"Issue time:  {ISSUE_DATETIME.strftime('%Y-%m-%d %HZ')} (GEFSv12 c00)")
    print(f"Valid date:  {VALID_DATE}")
    print(f"Location:    ~Mumbai ({TARGET_LAT}N, {TARGET_LON}E)")
    print("=" * 62)

    gefs_val, gefs_breakdown = fetch_gefs_day1()
    imd_val = fetch_imd_day1()

    print(f"\n{SEP}")
    print("C. Forecast Error")
    print(SEP)
    
    print(f"  GEFS Day 1:    {gefs_val:.3f} mm" if gefs_val is not None else "  GEFS Day 1:    [FAIL]")
    print(f"  IMD observed:  {imd_val:.3f} mm" if imd_val is not None else "  IMD observed:  [FAIL]")

    if gefs_val is not None and imd_val is not None and not np.isnan(imd_val):
        error = abs(gefs_val - imd_val)
        print(f"  |Error|:       {error:.3f} mm")
        print(f"\n  REAL GEFSv12 FORECAST -> REAL IMD OBSERVATION -> REAL ERROR  [CONFIRMED]")
        verdict = "PASS"
    else:
        print(f"\n  Cannot compute error.")
        verdict = "FAIL"

    import json
    result = {
        "issue_datetime": ISSUE_DATETIME.isoformat(),
        "valid_date": VALID_DATE.isoformat(),
        "location": {"lat": TARGET_LAT, "lon": TARGET_LON},
        "member": MEMBER,
        "gefs_day1_precip_mm": gefs_val,
        "imd_observed_mm": imd_val,
        "abs_error_mm": abs(gefs_val - imd_val) if verdict == "PASS" else None,
        "verdict": verdict,
    }
    
    out_path = os.path.join(RAW_DIR, "gefs_imd_verification.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Result saved to: {out_path}")
    print(f"\n  VERDICT: {verdict}")

    return 0 if verdict == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
