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
- [x] **Task 01** — Repository setup, data feasibility test (GEFSv12 + IMD verified).
- [x] **Task 02** — Build real GEFSv12 + IMD training dataset.
  - Assembled 44 unique issue dates across 2000–2004 over Maharashtra (18–22°N, 72–76°E).
  - Produced `data/raw/training_dataset_sample.parquet` (35,200 rows, 13 cols, 0.00% missing data).
  - `tests/test_dataset_task02.py` passes all checks.
- [x] **Task 03** — Feature engineering & bust label generation.
  - `src/features/engineer_features.py`: added cyclic temporal features, spatial gradients, anomaly, and leakage-safe historical bias.
  - `src/features/bust_label.py`: 85th percentile stratified threshold per (lead_day, season) on training data only. Realized bust rate: 14.07%.
  - Output: `data/processed/features.parquet` (35,200 rows, 22 cols).
- [x] **Task 04** — Model training & full evaluation suite.
  - Chronological 70/15/15 split (train: 24,000 rows; val: 4,800 rows; test: 6,400 rows).
  - Climatological Baseline: ROC-AUC 0.4358, PR-AUC 0.1044, Brier 0.1034.
  - Logistic Regression: ROC-AUC 0.8597, PR-AUC 0.6744, Brier 0.1155.
  - Primary XGBoost Model: ROC-AUC 0.9316, PR-AUC 0.7907, Brier 0.0513 (clear, decisive win over baseline).
  - Evaluated by lead day (Day 1: 0.9830, Day 3: 0.8908, Day 5: 0.9741, Day 7: 0.9139, Day 10: 0.9232 ROC-AUC).
- [x] **Task 05** — Probability calibration & explainability.
  - Isotonic calibration on validation fold improved test Brier score from 0.0513 to 0.0480.
  - Saved `models/calibrator.pkl`.
  - `src/explain/shap_explain.py`: SHAP global feature importances & per-prediction driver extractor.
  - `src/explain/rules.py`: Plain-language rule-based explanation mapping & confidence band labels.
- [x] **Task 06** — Inference engine.
  - `src/models/inference.py`: Production-grade `BustPredictor` with `predict()` and `batch_predict_region()`.
- [x] **Task 07** — FastAPI application.
  - `src/api/main.py`: Fully functional REST API serving `/health`, `/metrics`, `/forecast-reliability`, `/region`, `/explanation`, `/replay`, `/rag-query`.
  - Comprehensive unit test `tests/test_pipeline_task03_to_07.py` passes 100%.

## Current Milestone
**Task 08** — Frontend Dashboard (React + Vite + Leaflet) & **Task 09** — Meteorological RAG.

## Next Tasks
1. **Task 08**: React Dashboard (Command Center map, Day 1-10 selector, Region Detail drill-down, Why-panel).
2. **Task 09**: Meteorological RAG (Curated corpus ingestion, FAISS index, cited explanation generation).
3. **Task 10**: Historical Replay Mode (Pre-cached offline demo cases showing forecast vs actual bust).
4. **Task 11**: Final End-to-End integration & acceptance report.
5. **Task 12**: Demo & PPT preparation.
