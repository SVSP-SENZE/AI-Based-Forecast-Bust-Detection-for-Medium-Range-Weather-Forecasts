# PROJECT_CONTEXT.md
<!-- Agents: read this FIRST before every task. Keep it compact. -->

## Goal
AI-based forecast bust detection for medium-range (Day 1-10) rainfall forecasts over India.
Binary classification: P(bust | forecast, metadata). Output: calibrated bust probability per
grid-point / city / lead-time combination.

## Branch
`forecast-bust-dev`

## Current Data Sources (MVP Core)

| Role | Source | Format | Coverage | Access |
|------|--------|--------|----------|--------|
| Forecast (PRIMARY) | NOAA GEFSv12 Reforecast (S3) | GRIB2 + .idx | 2000-2019, 5 members | Public S3, byte-range capable |
| Truth (PRIMARY) | IMD 0.25-deg gridded rainfall | Binary .grd via imdlib | 1901-present | imdlib / IMD FTP |
| Forecast (Secondary/Optional) | Open-Meteo Historical / Previous Runs | JSON (HTTP GET) | 2021-present / 2024-present | Free, no key |
| Truth (Secondary/Optional) | Open-Meteo ERA5 archive | JSON (HTTP GET) | 1940-present | Free, no key |

**Geography (MVP):** India sub-region, target cities/grid-cells TBD in Task 02.
**Variable:** `precipitation_sum` (mm/day) / `apcp_sfc`. **Lead times:** Day 1, 3, 5, 7, 10.

## Confirmed Access Mechanisms
```
# GEFSv12 S3 (byte-range download using .idx, decoded via wgrib2)
s3://noaa-gefs-retrospective/GEFSv12/reforecast/YYYY/YYYYMMDDHH/{c00,p01-p04}/Days:1-10/apcp_sfc_YYYYMMDDHH_c00.grib2
.idx: https://noaa-gefs-retrospective.s3.amazonaws.com/GEFSv12/reforecast/.../.idx

# IMD Truth
imdlib.get_data("rain", START_YEAR, END_YEAR, fn_format="yearwise", file_dir="...")
```

## Planning-Document Conflict Resolution
- Task prompt specified "NOAA GEFSv12 reforecast" as preferred.
- DATA_STRATEGY.md recommended Open-Meteo as primary.
- **Resolution:** **GEFSv12 Reforecast is PRIMARY**, and **IMD 0.25° is PRIMARY TRUTH**.
  Open-Meteo and ERA5 are demoted to optional/secondary.
  The historical training period is set to 2000–2019 to match GEFSv12.

## Completed Milestones
- [x] **Task 01** — Repository setup, directory structure, data feasibility test.
  - REAL GEFSv12 FORECAST -> REAL IMD OBSERVATION -> REAL ERROR confirmed.
  - Successfully byte-ranged GEFS and decoded via `wgrib2`.
  - Successfully downloaded and parsed IMD year 2000 via `imdlib`.

## Current Milestone
**Task 02** — Define India sub-region, pull a real multi-month training sample from 2000-2019,
save raw parquet files to `data/raw/`.

## Important Paths
```
scripts/gefs_imd_verification_july.py # GEFS+IMD real data verification
tests/test_smoke_task01.py      # smoke test
data/raw/                       # raw parquet will go here (Task 02)
data/interim/                   # aligned forecast+truth tables (Task 03)
data/processed/                 # feature tables + bust labels (Task 04)
src/data/                       # ingest scripts
src/features/                   # feature engineering
src/models/                     # train / calibrate
src/evaluation/                 # metrics + plots
models/                         # saved model artifacts (.pkl, .txt)
wgrib2/                         # wgrib2 binary for GRIB2 decoding
```

## Environment / Setup
```powershell
# Python 3.14.4  |  pip 26.0.1
pip install requests pandas numpy   
pip install imdlib                  
# wgrib2.exe is used for GRIB2 decoding (downloaded locally).
```

## Known Issues
1. Open-Meteo remains available as a secondary fallback if needed, but not primary.
2. GEFSv12 S3 path is `YYYYMMDDHH/` (10-digit, not `YYYYMMDD/HH/`).
3. GEFS `apcp_sfc` requires 4x 6-hourly messages to sum a 24-hr Day 1 forecast.
4. Windows console needs ASCII-only output.

## Strict Do-Not-Do Rules
- NO synthetic data, ever.
- NO frontend / FastAPI / RAG yet (deferred to Task 07+).
- NO large GRIB2 downloads (25 MB/file global; use byte-range .idx extraction).
- NO random train/test splits — always temporal (chronological) splits.
- NO new packages without checking if pandas/numpy/requests already suffice.
- NO reprocessing of already-saved parquet files unless the schema changed.
- Do NOT start Task 03 until Task 02 raw data is on disk and verified.

## Next Task (Task 02)
**Pull real training data.**
1. Select India sub-region: 5-10 representative cities/grid-points spanning monsoon gradients.
2. Pull a subset from 2000–2019 (e.g. one monsoon season like 2000) GEFSv12 forecast data (Day 1/3/5/7/10).
3. Pull IMD truth for the same date range and locations.
4. Save as `data/raw/forecasts_raw.parquet` and `data/raw/imd_truth_raw.parquet`.
5. Validate: no all-null columns, date coverage > 80%, row counts match expectation.
6. Update PROJECT_CONTEXT.md. Run smoke test. Report PASS/FAIL.
