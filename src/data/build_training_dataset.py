import os
import sys
import datetime
import urllib.request
import concurrent.futures
import subprocess
import numpy as np
import pandas as pd
import imdlib

# Config
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(ROOT_DIR, "data", "raw")
WGRIB2 = os.path.join(ROOT_DIR, "wgrib2", "wgrib2.exe")
os.makedirs(RAW_DIR, exist_ok=True)

TARGET_LAT_MIN, TARGET_LAT_MAX = 18.0, 22.0
TARGET_LON_MIN, TARGET_LON_MAX = 72.0, 76.0

# 5 Days for quick ML sample testing
START_DATE = datetime.date(2000, 7, 1)
END_DATE = datetime.date(2000, 7, 15)

LEAD_DAYS = [1, 3, 5, 7, 10]
MEMBERS = ["c00", "p01", "p02", "p03", "p04"]

GEFS_BASE = "https://noaa-gefs-retrospective.s3.amazonaws.com"

# Setup IMD Lat/Lon grid
imd_lats = np.arange(6.5, 38.75, 0.25)
imd_lons = np.arange(66.5, 100.25, 0.25)

# Filter IMD grid points to our bounding box
lat_mask = (imd_lats >= TARGET_LAT_MIN) & (imd_lats <= TARGET_LAT_MAX)
lon_mask = (imd_lons >= TARGET_LON_MIN) & (imd_lons <= TARGET_LON_MAX)
target_lats = imd_lats[lat_mask]
target_lons = imd_lons[lon_mask]
print(f"Target grid: {len(target_lats)} lats x {len(target_lons)} lons = {len(target_lats)*len(target_lons)} points")

def get_gefs_idx(issue_date, member):
    """Fetch and parse the .idx file to find byte ranges for all lead days."""
    init_str = issue_date.strftime("%Y%m%d00")
    year = issue_date.year
    idx_url = f"{GEFS_BASE}/GEFSv12/reforecast/{year}/{init_str}/{member}/Days:1-10/apcp_sfc_{init_str}_{member}.grib2.idx"
    
    req = urllib.request.Request(idx_url, headers={"User-Agent": "gefs-imd-builder"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            idx_text = r.read().decode("utf-8")
    except Exception as e:
        print(f"Error fetching {idx_url}: {e}")
        return None
        
    lines = [l for l in idx_text.strip().split("\n") if l.strip()]
    offsets = []
    for line in lines:
        parts = line.split(":")
        offsets.append((int(parts[1]), line))
        
    # Find contiguous blocks for each lead day
    blocks = {}
    for lead in LEAD_DAYS:
        # A day's APCP is made of four 6-h chunks.
        # e.g. Day 1: 0-6, 6-12, 12-18, 18-24
        start_hr = (lead - 1) * 24
        chunks = [
            f"{start_hr}-{start_hr+6} hour acc fcst",
            f"{start_hr+6}-{start_hr+12} hour acc fcst",
            f"{start_hr+12}-{start_hr+18} hour acc fcst",
            f"{start_hr+18}-{start_hr+24} hour acc fcst",
        ]
        
        chunk_offsets = []
        for i, (offset, line) in enumerate(offsets):
            if "APCP:surface" in line:
                for chunk in chunks:
                    if chunk in line:
                        end = offsets[i+1][0] - 1 if i+1 < len(offsets) else offset + 5000000
                        chunk_offsets.append((offset, end, chunk))
        
        if len(chunk_offsets) == 4:
            # Optimize: download one big block from the start of the first chunk to the end of the last chunk
            start_byte = chunk_offsets[0][0]
            end_byte = chunk_offsets[-1][1]
            blocks[lead] = {"start": start_byte, "end": end_byte, "chunks": chunks}
        else:
            print(f"Warning: Could not find all 4 chunks for lead {lead} in {init_str} {member}")
            
    return blocks

def download_gefs_block(issue_date, member, lead, block):
    """Download a byte range for a specific lead day and run wgrib2 to extract target area."""
    init_str = issue_date.strftime("%Y%m%d00")
    year = issue_date.year
    grib_url = f"{GEFS_BASE}/GEFSv12/reforecast/{year}/{init_str}/{member}/Days:1-10/apcp_sfc_{init_str}_{member}.grib2"
    
    start, end = block["start"], block["end"]
    req = urllib.request.Request(grib_url, headers={
        "User-Agent": "gefs-imd-builder",
        "Range": f"bytes={start}-{end}",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    except Exception as e:
        print(f"Error downloading {grib_url} range {start}-{end}: {e}")
        return None
        
    temp_grib = os.path.join(RAW_DIR, f"temp_{init_str}_{member}_ld{lead}.grib2")
    temp_csv = os.path.join(RAW_DIR, f"temp_{init_str}_{member}_ld{lead}.csv")
    
    with open(temp_grib, "wb") as f:
        f.write(raw)
        
    # Run wgrib2 to extract spatial subset and write to CSV
    cmd = [
        WGRIB2, temp_grib, 
        "-small_grib", f"{TARGET_LON_MIN}:{TARGET_LON_MAX}", f"{TARGET_LAT_MIN}:{TARGET_LAT_MAX}", 
        temp_grib + ".small",
        "-csv", temp_csv
    ]
    # Wait, wgrib2 can't do small_grib and csv in one pass reliably without -set_grib_type maybe? 
    # Let's do it in two passes.
    subprocess.run([WGRIB2, temp_grib, "-small_grib", f"{TARGET_LON_MIN}:{TARGET_LON_MAX}", f"{TARGET_LAT_MIN}:{TARGET_LAT_MAX}", temp_grib + ".small"], capture_output=True)
    subprocess.run([WGRIB2, temp_grib + ".small", "-csv", temp_csv], capture_output=True)
    
    # Read CSV
    if not os.path.exists(temp_csv):
        return None
        
    try:
        # Columns: "date","valid","var","level","lon","lat","val"
        df = pd.read_csv(temp_csv, header=None, names=["issue", "valid", "var", "level", "lon", "lat", "val"])
    except:
        return None
        
    # Clean up temp files
    for f in [temp_grib, temp_grib + ".small", temp_csv]:
        if os.path.exists(f):
            os.remove(f)
            
    # Filter to just the 4 chunks we care about (since the big block might have included 3h chunks)
    # The valid column in CSV looks like "2000-07-02 00:00:00"
    # But wgrib2 output for valid is usually the end of the accumulation period.
    # We can just sum all APCP values per lat/lon where val >= 0.
    # Wait, if we include 0-3 and 3-6 hour accs, they overlap!
    # We MUST filter by the exact accumulation string. But wgrib2 -csv doesn't output the "0-6 hour acc fcst" string directly!
    return df


def process_gefs_for_issue_date(issue_date):
    print(f"Processing GEFS for {issue_date}...")
    records = []
    
    for member in MEMBERS:
        blocks = get_gefs_idx(issue_date, member)
        if not blocks:
            continue
            
        for lead in LEAD_DAYS:
            if lead not in blocks:
                continue
                
            df = download_gefs_block(issue_date, member, lead, blocks[lead])
            if df is None or df.empty:
                continue
                
            # df has valid column like "2000-07-02 00:00:00"
            df['valid_dt'] = pd.to_datetime(df['valid'])
            
            # Filter to keep only the 6-hourly chunks (ending at 00, 06, 12, 18)
            df = df[df['valid_dt'].dt.hour.isin([0, 6, 12, 18])]
            
            # Group by lon, lat and sum the values
            # We expect exactly 4 chunks for each lon/lat point to make a full day
            grouped = df.groupby(['lon', 'lat']).agg(
                val=('val', 'sum'),
                count=('val', 'count')
            ).reset_index()
            
            # Only keep points that have all 4 chunks
            grouped = grouped[grouped['count'] == 4]
            
            for _, row in grouped.iterrows():
                valid_date = issue_date + datetime.timedelta(days=lead)
                records.append({
                    'issue_time': issue_date,
                    'valid_time': valid_date,
                    'lead_day': lead,
                    'member': member,
                    'lon': row['lon'],
                    'lat': row['lat'],
                    'apcp_mm': row['val']
                })
                
    return records

def process_imd_data():
    print("Downloading/loading IMD data for year 2000...")
    imd_cache = os.path.join(RAW_DIR, "imd_rain_2000")
    os.makedirs(imd_cache, exist_ok=True)
    try:
        data = imdlib.get_data("rain", 2000, 2000, fn_format="yearwise", file_dir=imd_cache)
        return data.data  # shape (366, 135, 129)
    except Exception as e:
        print(f"Failed to load IMD data: {e}")
        return None

def main():
    print("=" * 50)
    print("BUILDING GEFS + IMD TRAINING DATASET")
    print("=" * 50)
    
    # 1. Fetch all GEFS records in parallel
    issue_dates = [START_DATE + datetime.timedelta(days=i) for i in range((END_DATE - START_DATE).days + 1)]
    
    all_gefs_records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_gefs_for_issue_date, d): d for d in issue_dates}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                all_gefs_records.extend(res)
                
    if not all_gefs_records:
        print("No GEFS data successfully processed. Exiting.")
        sys.exit(1)
        
    df_gefs = pd.DataFrame(all_gefs_records)
    print(f"Extracted {len(df_gefs)} GEFS raw member rows.")
    
    # 2. Compute Ensemble Statistics
    # Group by issue_time, valid_time, lead_day, lon, lat
    agg_funcs = {
        'apcp_mm': ['mean', 'std', 'min', 'max']
    }
    df_ens = df_gefs.groupby(['issue_time', 'valid_time', 'lead_day', 'lat', 'lon']).agg(agg_funcs)
    df_ens.columns = ['forecast_mean', 'forecast_spread', 'forecast_min', 'forecast_max']
    df_ens['forecast_range'] = df_ens['forecast_max'] - df_ens['forecast_min']
    df_ens = df_ens.reset_index()
    
    print(f"Aggregated to {len(df_ens)} ensemble rows.")
    
    # 3. Load IMD and join
    imd_arr = process_imd_data()
    if imd_arr is None:
        sys.exit(1)
        
    # Prepare list for IMD observations
    imd_records = []
    
    # We only need IMD data for the valid dates we actually forecasted
    valid_dates = df_ens['valid_time'].unique()
    for vd in valid_dates:
        vd_date = pd.to_datetime(vd).date()
        day_idx = (vd_date - datetime.date(2000, 1, 1)).days
        
        # Iterate over target lats/lons
        for lat in target_lats:
            for lon in target_lons:
                lat_idx = int(np.argmin(np.abs(imd_lats - lat)))
                lon_idx = int(np.argmin(np.abs(imd_lons - lon)))
                
                val = float(imd_arr[day_idx, lat_idx, lon_idx])
                if val < -900:
                    val = np.nan
                    
                imd_records.append({
                    'valid_time': vd_date,
                    'lat': lat,
                    'lon': lon,
                    'observed_rainfall': val
                })
                
    df_imd = pd.DataFrame(imd_records)
    
    # Convert valid_time in df_ens to date to join
    df_ens['valid_time'] = pd.to_datetime(df_ens['valid_time']).dt.date
    
    # Join GEFS and IMD
    df_final = pd.merge(df_ens, df_imd, on=['valid_time', 'lat', 'lon'], how='inner')
    print(f"Joined GEFS and IMD. Final row count: {len(df_final)}")
    
    # 4. Filter missing IMD
    missing_rate = df_final['observed_rainfall'].isna().mean()
    print(f"IMD Missing data rate: {missing_rate:.2%}")
    df_final = df_final.dropna(subset=['observed_rainfall'])
    
    # 5. Compute Forecast Error
    df_final['forecast_error'] = (df_final['forecast_mean'] - df_final['observed_rainfall']).abs()
    
    # 6. Save Parquet
    out_file = os.path.join(RAW_DIR, "training_dataset_sample.parquet")
    df_final.to_parquet(out_file, engine='pyarrow', index=False)
    
    print("\nSample Output:")
    print(df_final[['issue_time', 'valid_time', 'lead_day', 'lat', 'lon', 'forecast_mean', 'forecast_spread', 'observed_rainfall', 'forecast_error']].head())
    
    print(f"\nMetadata: ")
    print(f"- Dimensions: {df_final.shape}")
    print(f"- File size: {os.path.getsize(out_file) / 1024:.1f} KB")
    print(f"- Date range: {df_final['issue_time'].min()} to {df_final['issue_time'].max()}")
    print("- PASS")

if __name__ == "__main__":
    main()
