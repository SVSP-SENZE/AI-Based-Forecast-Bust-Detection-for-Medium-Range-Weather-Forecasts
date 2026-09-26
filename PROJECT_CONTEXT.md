# PROJECT_CONTEXT.md
<!-- Agents: read this FIRST before every task. Keep it compact. -->

## Goal
AI-based forecast bust detection for medium-range (Day 1-10) rainfall forecasts over India.
Binary classification: P(bust | forecast, metadata). Output: calibrated bust probability per
grid-point / city / lead-time combination.

## Branch
`forecast-bust-dev`

## Current Data Sources

| Role | Source | Format | Coverage | Access |
|------|--------|--------|----------|--------|
| Forecast (primary) | Open-Meteo Historical Forecast API | JSON (HTTP GET) | 2021-present, global | Free, no key |
| Forecast (lead-stratified) | Open-Meteo Previous Runs API | JSON (HTTP GET, `past_days=N`) | 2024-present | Free, no key |
| Truth (primary) | Open-Meteo ERA5 archive | JSON (HTTP GET) | 1940-present | Free, no key |
| Forecast (secondary / ensemble) | NOAA GEFSv12 Reforecast (S3) | GRIB2 + .idx | 2000-2019, 5 members | Public S3, byte-range capable |
| Truth (cross-check) | IMD 0.25-deg gridded rainfall | Binary .grd via imdlib | 1901-present | imdlib / IMD FTP; direct HTTP 404 |

**Geography (MVP):** India sub-region, target cities/grid-cells TBD in Task 02.
**Variable:** `precipitation_sum` (mm/day). **Lead times:** Day 1, 3, 5, 7, 10.

## Confirmed API Calls (Task 01 verified)
```
# Historical Forecast (forecast side)
GET https://historical-forecast-api.open-meteo.com/v1/forecast
  ?latitude=19.08&longitude=72.88&daily=precipitation_sum
  &start_date=2024-06-01&end_date=2024-06-05&timezone=Asia/Kolkata

# Previous Runs (lead-stratified)
GET https://previous-runs-api.open-meteo.com/v1/forecast
  ?latitude=...&longitude=...&daily=precipitation_sum
  &forecast_days=3&past_days=7&timezone=Asia/Kolkata

# ERA5 truth
GET https://archive-api.open-meteo.com/v1/archive
  ?latitude=...&longitude=...&daily=precipitation_sum
  &start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&timezone=Asia/Kolkata

# GEFSv12 S3 (no download yet; .idx byte-range confirmed)
s3://noaa-gefs-retrospective/GEFSv12/reforecast/YYYY/YYYYMMDDHH/{c00,p01-p04}/Days:1-10/apcp_sfc_YYYYMMDDHH_c00.grib2
.idx: https://noaa-gefs-retrospective.s3.amazonaws.com/GEFSv12/reforecast/.../.idx
```

## IMD Status
- Direct HTTP links return 404 (URL structure changed on IMD portal).
- `imdlib` package wraps IMD FTP correctly; install with `pip install imdlib` when needed.
- ERA5 is sufficient truth for MVP; IMD is a stretch cross-check only.

## Planning-Document Conflict Resolution
- Task prompt specified "NOAA GEFSv12 reforecast" as preferred.
- DATA_STRATEGY.md recommends Open-Meteo as primary.
- **Resolution:** Both are accessible. Open-Meteo is PRIMARY (JSON, zero GRIB toolchain),
  GEFSv12 is SECONDARY (20-year depth, true ensemble spread for future feature).
  This is documented and consistent with DATA_STRATEGY.md §3.

## Completed Milestones
- [x] **Task 01** — Repository setup, directory structure, data feasibility test.
  - All 21 smoke tests PASS.
  - REAL FORECAST -> REAL OBSERVATION -> REAL ERROR confirmed with live data.
  - `data/raw/feasibility_results.json` written.

## Current Milestone
**Task 02** — Define India sub-region, pull a real multi-month training sample,
save raw parquet files to `data/raw/`.

## Important Paths
```
scripts/feasibility_test.py     # verified data access, run to re-check
tests/test_smoke_task01.py      # 21-check smoke test
data/raw/feasibility_results.json   # feasibility test output
data/raw/                       # raw parquet will go here (Task 02)
data/interim/                   # aligned forecast+truth tables (Task 03)
data/processed/                 # feature tables + bust labels (Task 04)
src/data/                       # ingest scripts
src/features/                   # feature engineering
src/models/                     # train / calibrate
src/evaluation/                 # metrics + plots
models/                         # saved model artifacts (.pkl, .txt)
```

## Environment / Setup
```powershell
# Python 3.14.4  |  pip 26.0.1
pip install requests pandas numpy   # already installed
pip install imdlib                  # optional, for IMD cross-check
# cfgrib / eccodes: only if GEFS GRIB2 decoding is added (Task 02+)
```

## Known Issues
1. IMD direct HTTP (imdpune.gov.in) returns 404 — use imdlib FTP wrapper instead.
2. Previous Runs API rejects `start_date`/`end_date` params; use `past_days=N` instead.
3. GEFSv12 S3 path is `YYYYMMDDHH/` (10-digit, not `YYYYMMDD/HH/`).
4. Open-Meteo ERA5 archive has ~3-day lag (recent dates return None).
5. Windows console needs ASCII-only output (no Unicode arrows/symbols in scripts).

## Strict Do-Not-Do Rules
- NO synthetic data, ever.
- NO frontend / FastAPI / RAG yet (deferred to Task 07+).
- NO large GRIB2 downloads (25 MB/file global; use byte-range .idx extraction).
- NO random train/test splits — always temporal (chronological) splits.
- NO new packages without checking if pandas/numpy/requests already suffice.
- NO reprocessing of already-saved parquet files unless the schema changed.
- NO rerunning feasibility_test.py for every task — only if a source breaks.
- Do NOT start Task 03 until Task 02 raw data is on disk and verified.

## Next Task (Task 02)
**Pull real training data.**
1. Select India sub-region: 5-10 representative cities/grid-points spanning monsoon gradients.
2. Pull 2024-01-01 to 2026-06-30 forecast data (Open-Meteo Historical Forecast API, lead days 1/3/5/7/10).
3. Pull ERA5 truth for same date range and locations.
4. Save as `data/raw/forecasts_raw.parquet` and `data/raw/era5_truth_raw.parquet`.
5. Validate: no all-null columns, date coverage > 80%, row counts match expectation.
6. Update PROJECT_CONTEXT.md. Run smoke test. Report PASS/FAIL.
