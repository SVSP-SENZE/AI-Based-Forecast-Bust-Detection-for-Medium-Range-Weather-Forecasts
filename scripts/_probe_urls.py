"""Quick probe for correct Open-Meteo API URLs and GEFS S3 paths."""
import urllib.request, json, sys

def probe(label, url):
    print(f"\n[{label}]")
    print(f"  URL: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "test"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            d = json.loads(raw)
            print(f"  STATUS: HTTP {r.status}")
            print(f"  TOP KEYS: {list(d.keys())}")
            daily = d.get("daily", {})
            if daily:
                print(f"  DAILY KEYS: {list(daily.keys())}")
                t = daily.get("time", [])
                p = daily.get("precipitation_sum", daily.get("rain", []))
                print(f"  DATES (first 3): {t[:3]}")
                print(f"  PRECIP (first 3): {p[:3]}")
            return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

# Historical Forecast API (replaces Previous Runs for older dates)
probe("HistFcst-API", 
    "https://historical-forecast-api.open-meteo.com/v1/forecast"
    "?latitude=19.08&longitude=72.88&daily=precipitation_sum"
    "&start_date=2024-06-01&end_date=2024-06-05&timezone=auto")

# Previous Runs API (correct v1 path)
probe("PrevRuns-v1",
    "https://previous-runs-api.open-meteo.com/v1/forecast"
    "?latitude=19.08&longitude=72.88&daily=precipitation_sum"
    "&forecast_days=3&start_date=2024-06-01&end_date=2024-06-05&timezone=auto")

# GEFSv12: correct S3 prefix (no date subdirectory)
print("\n[GEFS-S3]")
import urllib.parse
# Try listing top-level of reforecast directory
url_s3 = (
    "https://noaa-gefs-retrospective.s3.amazonaws.com/"
    "?prefix=GEFSv12/reforecast/2000/20000101/&delimiter=/&max-keys=20"
)
print(f"  URL: {url_s3}")
try:
    req = urllib.request.Request(url_s3, headers={"User-Agent": "test"})
    with urllib.request.urlopen(req, timeout=20) as r:
        content = r.read().decode("utf-8")
        import re
        keys = re.findall(r"<Key>(.*?)</Key>", content)
        prefixes = re.findall(r"<Prefix>(.*?)</Prefix>", content)
        print(f"  STATUS: HTTP {r.status}")
        print(f"  KEYS: {keys[:5]}")
        print(f"  PREFIXES: {prefixes[:5]}")
except Exception as e:
    print(f"  FAIL: {e}")
