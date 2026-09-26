"""
scripts/gefs_imd_verification_july.py
==================================
Targeted scientific feasibility verification:

  REAL GEFSv12 HISTORICAL FORECAST
  -> REAL IMD HISTORICAL RAINFALL
  -> REAL FORECAST ERROR

Case: GEFSv12 reforecast 2000-07-01 00Z (c00 control member)
      Day 1 (24-hr) accumulated precipitation over Mumbai area
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

# Constants for July
ISSUE_DATETIME  = datetime.datetime(2000, 7, 1, 0)
VALID_DATE      = datetime.date(2000, 7, 2)
MEMBER          = "c00"
TARGET_LAT      = 19.0
TARGET_LON      = 72.8

GEFS_BASE = "https://noaa-gefs-retrospective.s3.amazonaws.com"
INIT_STR  = "2000070100"
GRIB_KEY  = (f"GEFSv12/reforecast/2000/{INIT_STR}/{MEMBER}/Days:1-10/"
             f"apcp_sfc_{INIT_STR}_{MEMBER}.grib2")

# We need the new byte offsets for July 1. 
# We fetch the .idx file and parse the offsets dynamically!
SEP = "-" * 62

def get_day1_msgs_from_idx():
    idx_url = f"{GEFS_BASE}/{GRIB_KEY}.idx"
    req = urllib.request.Request(idx_url, headers={"User-Agent": "test"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            idx_text = r.read().decode("utf-8")
    except Exception as e:
        print(f"Error fetching .idx: {e}")
        sys.exit(1)
        
    lines = [l for l in idx_text.strip().split("\n") if l.strip()]
    msgs = []
    # Find 0-6, 6-12, 12-18, 18-24 hour forecasts
    targets = ["0-6 hour acc fcst", "6-12 hour acc fcst", "12-18 hour acc fcst", "18-24 hour acc fcst"]
    labels = ["0-6h", "6-12h", "12-18h", "18-24h"]
    
    offsets = []
    for line in lines:
        parts = line.split(":")
        offset = int(parts[1])
        offsets.append((offset, line))
    
    # Sort just in case, though they should be sequential
    # But wait, index lines are just in order.
    for target, label in zip(targets, labels):
        for i, (offset, line) in enumerate(offsets):
            if "APCP:surface" in line and target in line:
                # Find the next offset to know the end
                end = offsets[i+1][0] - 1 if i+1 < len(offsets) else offset + 1000000
                msgs.append({"label": label, "start": offset, "end": end})
                break
    return msgs

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
    
    day1_msgs = get_day1_msgs_from_idx()
    if len(day1_msgs) != 4:
        print("Could not find all 4 Day 1 messages in .idx")
        return None, accum_values

    combined_grib = os.path.join(RAW_DIR, "day1_apcp_july.grib2")
    with open(combined_grib, "wb") as f_out:
        for msg in day1_msgs:
            label = msg["label"]
            start, end = msg["start"], msg["end"]
            print(f"  Fetching {label}: bytes {start}-{end}")
            raw = byte_range_get(grib_url, start, end)
            f_out.write(raw)
            
    print(f"  Decoding with wgrib2")
    cmd = [WGRIB2, combined_grib, "-lon", str(TARGET_LON), str(TARGET_LAT)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  [FAIL] wgrib2 failed: {result.stderr}")
        return None, accum_values
        
    lines = result.stdout.strip().split("\n")
    day1_total = 0.0
    
    for i, line in enumerate(lines):
        parts = line.split(":")
        if i < len(day1_msgs):
            label = day1_msgs[i]["label"]
        else:
            continue
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
        
        if val < -900:
            val = np.nan
            
        print(f"  IMD rainfall at ({imd_lats[lat_idx]:.2f}N, {imd_lons[lon_idx]:.2f}E)")
        print(f"  on {VALID_DATE} (Day {day_idx}) = {val:.3f} mm")
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
    
    out_path = os.path.join(RAW_DIR, "gefs_imd_verification_july.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Result saved to: {out_path}")
    print(f"\n  VERDICT: {verdict}")

    return 0 if verdict == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
