"""
tests/test_smoke_task01.py
===========================
Smoke test for Task 01 (foundation + data feasibility).

Verifies:
  1. Project directory structure exists
  2. feasibility_results.json was produced and is non-empty
  3. Open-Meteo ERA5 archive returns valid data (live sanity check)
  4. GEFS S3 bucket listing is reachable
  5. feasibility_test.py exits with code 0 (integration test)

Run: python tests/test_smoke_task01.py
"""

import os
import sys
import json
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = []
FAIL = []


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
        PASS.append(name)
    else:
        print(f"  FAIL  {name}  {detail}")
        FAIL.append(name)


# 1. Directory structure
print("1. Directory structure")
for d in ["data/raw", "data/interim", "data/processed",
          "src/data", "src/features", "src/models", "src/evaluation",
          "scripts", "tests", "notebooks", "models"]:
    check(f"dir:{d}", os.path.isdir(os.path.join(ROOT, d)))

# 2. Feasibility results file
print("\n2. Feasibility results artifact")
results_path = os.path.join(ROOT, "data", "raw", "feasibility_results.json")
check("feasibility_results.json exists", os.path.isfile(results_path))
if os.path.isfile(results_path):
    with open(results_path) as f:
        res = json.load(f)
    check("gefs key present", "gefs" in res)
    check("prevruns_era5 key present", "prevruns_era5" in res)
    check("era5 ACCESSIBLE", res.get("prevruns_era5", {}).get("era5_truth", {}).get("status") == "ACCESSIBLE")
    pair = res.get("prevruns_era5", {}).get("pairing", {})
    check("pairing DEMONSTRATED", pair.get("status") == "DEMONSTRATED")
    check("paired rows >= 1", (pair.get("n_rows", 0) or 0) >= 1)

# 3. Live ERA5 sanity check (tiny)
print("\n3. Live ERA5 sanity check")
try:
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        "?latitude=28.6&longitude=77.2&daily=precipitation_sum"
        "&start_date=2024-01-01&end_date=2024-01-03&timezone=auto"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "smoke-test"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
    dates = d.get("daily", {}).get("time", [])
    check("ERA5 returns dates", len(dates) == 3, f"got {len(dates)}")
    check("ERA5 latitude present", "latitude" in d)
except Exception as e:
    check("ERA5 live check", False, str(e))

# 4. GEFS S3 reachability
print("\n4. GEFS S3 reachability")
try:
    import re
    url = (
        "https://noaa-gefs-retrospective.s3.amazonaws.com/"
        "?prefix=GEFSv12/reforecast/2000/2000010100/&delimiter=/&max-keys=5"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "smoke-test"})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read().decode("utf-8")
    prefixes = re.findall(r"<CommonPrefixes><Prefix>(.*?)</Prefix></CommonPrefixes>", raw)
    check("GEFS S3 listing has member prefixes", len(prefixes) >= 1, f"got {prefixes}")
except Exception as e:
    check("GEFS S3 reachable", False, str(e))

# 5. Integration: run feasibility_test.py
print("\n5. feasibility_test.py exits 0")
script = os.path.join(ROOT, "scripts", "feasibility_test.py")
result = subprocess.run([sys.executable, script], capture_output=True, timeout=90)
check("feasibility_test.py exit code 0", result.returncode == 0,
      f"exit={result.returncode}")

# Summary
print(f"\n{'='*50}")
print(f"SMOKE TEST RESULT: {len(PASS)} PASS  |  {len(FAIL)} FAIL")
if FAIL:
    print(f"FAILED: {FAIL}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
    sys.exit(0)
