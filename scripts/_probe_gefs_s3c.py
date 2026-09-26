"""HEAD a GEFS GRIB2 file to get size, then probe Previous Runs API correctly."""
import urllib.request, json, re, datetime

# --- GEFS file size ---
key = "GEFSv12/reforecast/2000/2000010100/c00/Days:1-10/apcp_sfc_2000010100_c00.grib2"
url = f"https://noaa-gefs-retrospective.s3.amazonaws.com/{key}"
print(f"GEFS GRIB2 sample: {key}")
try:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "test"})
    with urllib.request.urlopen(req, timeout=15) as r:
        cl = r.headers.get("Content-Length", "?")
        ct = r.headers.get("Content-Type", "?")
        mb = int(cl) // 1024 // 1024 if cl != "?" else "?"
        print(f"  Size: {cl} bytes ({mb} MB)")
        print(f"  Content-Type: {ct}")
        print(f"  HTTP: {r.status}")
except Exception as e:
    print(f"  FAIL: {e}")

# --- GEFS .idx file (byte-range index for partial download) ---
idx_key = key + ".idx"
idx_url = f"https://noaa-gefs-retrospective.s3.amazonaws.com/{idx_key}"
print(f"\nGEFS .idx (byte-range index): {idx_key}")
try:
    req = urllib.request.Request(idx_url, headers={"User-Agent": "test"})
    with urllib.request.urlopen(req, timeout=15) as r:
        idx_content = r.read().decode("utf-8", errors="replace")
        print(f"  HTTP: {r.status}")
        # Show first 10 lines of index
        lines = idx_content.strip().split("\n")[:10]
        for ln in lines:
            print(f"  IDX: {ln}")
except Exception as e:
    print(f"  FAIL: {e}")

# --- Previous Runs API: correct model param ---
print("\n--- Previous Runs API ---")
# The Previous Runs API requires specifying model explicitly
for model in ["gfs", "ecmwf_ifs04", "ecmwf_ifs025", ""]:
    if model:
        url = (
            f"https://previous-runs-api.open-meteo.com/v1/forecast"
            f"?latitude=19.08&longitude=72.88&daily=precipitation_sum"
            f"&forecast_days=3&past_days=5&timezone=auto&models={model}"
        )
    else:
        url = (
            "https://previous-runs-api.open-meteo.com/v1/forecast"
            "?latitude=19.08&longitude=72.88&daily=precipitation_sum"
            "&forecast_days=3&past_days=5&timezone=auto"
        )
    label = model if model else "(no model param)"
    print(f"\n  model={label}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "test"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
            daily = d.get("daily", {})
            t = daily.get("time", [])
            p = daily.get("precipitation_sum", [])
            print(f"    HTTP: {r.status} | dates: {t[:3]} | precip: {p[:3]}")
    except Exception as e:
        print(f"    FAIL: {type(e).__name__}: {e}")
