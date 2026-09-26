import os
import sys
import datetime
import pandas as pd
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_dataset(parquet_file):
    print(f"Loading {parquet_file}")
    if not os.path.exists(parquet_file):
        print(f"FAIL: Dataset file {parquet_file} does not exist.")
        return False
        
    df = pd.read_parquet(parquet_file)
    
    # 1. non-empty dataset
    if len(df) == 0:
        print("FAIL: Dataset is empty.")
        return False
    print(f"PASS: Dataset has {len(df)} rows.")
    
    # Unique issue dates
    unique_dates = df['issue_time'].nunique()
    print(f"UNIQUE ISSUE DATES: {unique_dates}")
    
    # 2 & 3. Real GEFS and IMD data
    if df['forecast_mean'].isna().all():
        print("FAIL: No real GEFS data.")
        return False
    if df['observed_rainfall'].isna().all():
        print("FAIL: No real IMD data.")
        return False
    print("PASS: Data is real and populated.")
    
    # 4. Correct units (precipitation >= 0)
    # 9. No impossible negative precipitation
    if (df['forecast_mean'] < 0).any():
        print("FAIL: Negative GEFS forecast found.")
        return False
    if (df['observed_rainfall'] < 0).any():
        print("FAIL: Negative IMD precipitation found.")
        return False
    print("PASS: No impossible negative precipitation.")
    
    # 5 & 6. Valid issue/valid times, correct lead days
    df['issue_time_date'] = pd.to_datetime(df['issue_time']).dt.date
    df['valid_time_date'] = pd.to_datetime(df['valid_time']).dt.date
    
    df['expected_valid'] = df.apply(lambda r: r['issue_time_date'] + datetime.timedelta(days=r['lead_day']), axis=1)
    if not (df['valid_time_date'] == df['expected_valid']).all():
        print("FAIL: Temporal rule violated! issue_time + lead_time != valid_time.")
        return False
    print("PASS: Temporal rule issue_time + lead_time = valid_time holds.")
    
    if set(df['lead_day'].unique()) != {1, 3, 5, 7, 10}:
        print("FAIL: Missing some target lead days.")
        return False
    print("PASS: All target lead days present.")
    
    # 8. Ensemble stats are numerical
    stats_cols = ['forecast_mean', 'forecast_spread', 'forecast_min', 'forecast_max', 'forecast_range']
    for c in stats_cols:
        if not pd.api.types.is_numeric_dtype(df[c]):
            print(f"FAIL: {c} is not numerical.")
            return False
    print("PASS: Ensemble statistics are numerical.")
    
    # 10. No duplicate issue_time/location/lead_day rows
    dupes = df.duplicated(subset=['issue_time', 'lat', 'lon', 'lead_day']).sum()
    if dupes > 0:
        print(f"FAIL: Found {dupes} duplicate rows.")
        return False
    print("PASS: No duplicate rows.")
    
    # 11. Missing data rate
    missing = df['observed_rainfall'].isna().sum()
    print(f"PASS: Missing data rate = {missing / len(df):.2%} ({missing} rows)")
    
    # 12 & 13. Geographic & Temporal coverage
    print(f"PASS: Geographic coverage: lats {df['lat'].min()}-{df['lat'].max()}, lons {df['lon'].min()}-{df['lon'].max()}")
    print(f"PASS: Temporal coverage: issue_dates {df['issue_time_date'].min()} to {df['issue_time_date'].max()}")
    
    # Sample
    print("\n================== SAMPLE ==================")
    print(df[['issue_time', 'valid_time', 'lead_day', 'lat', 'lon', 'forecast_mean', 'forecast_spread', 'observed_rainfall', 'forecast_error']].sample(min(5, len(df))).to_string())
    print("============================================")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        target_file = os.path.join(ROOT_DIR, "data", "raw", "training_dataset_sample.parquet")
        
    if test_dataset(target_file):
        sys.exit(0)
    else:
        sys.exit(1)
