"""Probe GEFS S3 deeper directory + Previous Runs API correct params."""
import urllib.request, json, re

def probe(label, url):
    print(f"\n[{label}]")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "test"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8")
            print(f"  STATUS: {r.status}")
            return raw
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        return ""

# GEFS: try without delimiter to see all keys
raw = probe("GEFS-S3-nodelemit",
    "https://noaa-gefs-retrospective.s3.amazonaws.com/"
    "?prefix=GEFSv12/reforecast/2000/20000101/00/Days%3A1-10/&max-keys=10")
if raw:
    keys = re.findall(r"<Key>(.*?)</Key>", raw)
    print(f"  KEYS: {keys[:5]}")
    print(f"  RAW (first 600): {raw[:600]}")

# Previous Runs: try the correct parameter (past_days instead of start_date)
raw2 = probe("PrevRuns-past_days",
    "https://previous-runs-api.open-meteo.com/v1/forecast"
    "?latitude=19.08&longitude=72.88&daily=precipitation_sum"
    "&forecast_days=3&past_days=7&timezone=auto")
if raw2:
    d = json.loads(raw2)
    print(f"  TOP KEYS: {list(d.keys())}")
    daily = d.get("daily", {})
    print(f"  DATES (first 3): {daily.get('time',[])[:3]}")
    print(f"  PRECIP (first 3): {daily.get('precipitation_sum',[])[:3]}")
