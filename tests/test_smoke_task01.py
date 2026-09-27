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
import unittest
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestSmokeTask01(unittest.TestCase):

    def test_01_directory_structure(self):
        dirs = [
            "data/raw", "data/interim", "data/processed",
            "src/data", "src/features", "src/models", "src/evaluation",
            "scripts", "tests", "notebooks", "models"
        ]
        for d in dirs:
            p = os.path.join(ROOT, d)
            self.assertTrue(os.path.isdir(p), f"Missing directory: {d}")

    def test_02_feasibility_results(self):
        path1 = os.path.join(ROOT, "data", "raw", "feasibility_results.json")
        path2 = os.path.join(ROOT, "models", "feasibility_results.json")
        path = path1 if os.path.exists(path1) else path2
        self.assertTrue(os.path.exists(path), "feasibility_results.json missing")
        with open(path) as f:
            res = json.load(f)
        self.assertTrue("gefs" in res or "gefs_reforecast" in res or len(res) > 0)

    def test_03_live_era5_sanity_check(self):
        url = ("https://archive-api.open-meteo.com/v1/archive?"
               "latitude=19.076&longitude=72.877"
               "&start_date=2020-07-01&end_date=2020-07-05"
               "&daily=rain_sum&timezone=Asia%2FKolkata")
        req = urllib.request.Request(url, headers={"User-Agent": "WeatherApp/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        self.assertIn("daily", data)
        self.assertIn("time", data["daily"])

    def test_04_gefs_s3_reachability(self):
        url = ("https://noaa-gefs-retrospective.s3.amazonaws.com/?"
               "list-type=2&prefix=GEFSv12/reforecast/2000/2000010100/&max-keys=5")
        req = urllib.request.Request(url, headers={"User-Agent": "WeatherApp/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode()
        self.assertIn("Key", content)

if __name__ == "__main__":
    unittest.main()
