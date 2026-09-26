# BUILD_MAP_BIBLE.md — Implementation Bible

Legend: **[FACT]** · **[ASSUMPTION]** · **[RECOMMENDATION]** · **[OPTION]**

---

## 1. Architecture

```
┌─────────────────┐   ┌──────────────────┐   ┌────────────────────┐
│ Data Acquisition │→ │ Data Validation   │→ │ Forecast/Obs Align  │
│ (Open-Meteo:     │   │ (schema, range,   │   │ (join on grid cell │
│  Previous/Single │   │  gap checks)      │   │  + valid time)     │
│  Runs, ERA5)     │   └──────────────────┘   └──────────┬──────────┘
└─────────────────┘                                       ↓
                                              ┌────────────────────┐
                                              │ Preprocessing +     │
                                              │ Feature Engineering │
                                              │ (climatology,       │
                                              │  revision, spread)  │
                                              └──────────┬──────────┘
                                                          ↓
                                              ┌────────────────────┐
                                              │ Bust-Label          │
                                              │ Generation           │
                                              │ (stratified          │
                                              │  percentile)         │
                                              └──────────┬──────────┘
                                                          ↓
                                    ┌─────────────────────────────────┐
                                    │ Train/Validation/Test            │
                                    │ (time-ordered split, per fold    │
                                    │  historical-stat features)       │
                                    └───────────────┬──────────────────┘
                                                     ↓
                          ┌───────────────────────────────────────────┐
                          │ Model: Climatology baseline → Logistic →   │
                          │ LightGBM/XGBoost                            │
                          └───────────────┬──────────────────────────┘
                                           ↓
                          ┌────────────────────────┐
                          │ Calibration (isotonic)  │
                          └───────────┬─────────────┘
                                      ↓
                          ┌────────────────────────┐        ┌───────────────────┐
                          │ Explainability (SHAP +  │──────→│ RAG (retrieval +   │
                          │ rule-based summary)     │        │ cited generation)  │
                          └───────────┬─────────────┘        └─────────┬─────────┘
                                      ↓                                 ↓
                          ┌───────────────────────────────────────────────┐
                          │ API (FastAPI): reliability, bust-probability,  │
                          │ region, explanation, replay, rag-query, metrics│
                          └───────────────┬─────────────────────────────┘
                                          ↓
                          ┌───────────────────────────────────────────────┐
                          │ Dashboard (React+Vite+Tailwind+Leaflet/Plotly): │
                          │ Command Center → Region Detail → Why-panel →   │
                          │ Historical Analogues → RAG Assistant → Metrics │
                          └───────────────────────────────────────────────┘

Data stores: parquet files for raw/aligned/feature tables; a single
`model.pkl`/`model.txt` (LightGBM) + `calibrator.pkl`; FAISS index +
chunk-store (JSON/parquet) for RAG; no relational DB required (§Storage).
```

## 2. Repository Structure

```
forecast-bust-detector/
├── PROJECT_CONTEXT.md          # living summary agents read before each task
├── data/
│   ├── raw/                    # untouched pulls from Open-Meteo (parquet)
│   ├── aligned/                # forecast+truth joined tables
│   └── features/               # final model-ready feature tables
├── src/
│   ├── ingest/                 # Open-Meteo/ERA5 pull scripts
│   ├── features/               # feature engineering + bust-label code
│   ├── models/                 # train/eval/calibration scripts
│   ├── explain/                # SHAP + rule-based explanation code
│   ├── rag/                    # ingestion, embedding, retrieval, generation
│   └── api/                    # FastAPI app
├── frontend/                   # React + Vite dashboard
├── notebooks/                  # exploratory only, not load-bearing
├── models/                     # trained artifacts (model.txt, calibrator.pkl)
├── rag_store/                  # FAISS index + chunk metadata
├── tests/                      # smoke tests per pipeline stage
└── docs/                       # the six bible documents (this set)
```

## 3. Tech Stack

**[RECOMMENDATION]**
- **Frontend**: React + Vite + Tailwind; Leaflet for the map, Plotly for charts (reliability diagrams, lead-time degradation curves).
- **Backend**: Python + FastAPI (small, fast to stand up, natural fit for serving a scikit-learn/LightGBM model + SHAP + FAISS retrieval).
- **Data/ML**: Python, pandas, NumPy, xarray (only if any gridded NetCDF handling is needed beyond Open-Meteo's JSON), scikit-learn (logistic regression, isotonic calibration, metrics), LightGBM (primary model — chosen over XGBoost for faster CPU training on this data size; XGBoost is an acceptable drop-in **[OPTION]** if LightGBM install friction appears on the agent's environment).
- **Explainability**: `shap`.
- **RAG**: FAISS (vector store), `sentence-transformers` (`all-MiniLM-L6-v2`, local CPU embeddings), Claude (via API) for grounded generation with the RAG prompt in RAG_BIBLE.md.
- **Deployment**: local run for development; if a public link is wanted for judging, a free-tier static host for the frontend (e.g., Vercel/Netlify free tier) + a free-tier small API host (e.g., Render/Fly.io free tier) — **[ASSUMPTION]** verify current free-tier limits at deployment time since these change; local-only + screen-recorded demo video is an acceptable and lower-risk fallback (see §Failure Modes).
- **Storage**: parquet files + local FAISS index — **no PostgreSQL / production DB**, since nothing here needs multi-writer concurrency, transactions, or relational joins beyond what pandas/parquet already does well; introducing Postgres would be pure unnecessary overhead for a 3-day build.

## 4. Agent Allocation

**[RECOMMENDATION]**
- **Antigravity (primary)**: all data ingestion, feature engineering, model training/evaluation, API, and dashboard implementation tasks — i.e., the bulk of Tasks 01–18 below. It should work one task at a time per PART 19's required workflow.
- **Claude (secondary)**: RAG corpus curation/summarization judgment calls, prompt engineering for the RAG generation step, reviewing/debugging tricky statistical logic (bust-threshold derivation, calibration), and any task requiring careful reasoning about scientific validity (e.g., double-checking the time-split logic for leakage) — Claude is well suited to the "explain why this is right" tasks, Antigravity to the "build and test it" tasks.
- **Manual (user)**: choosing the exact bounding box/date window (a judgment call informed by a quick look at the data, not something to blindly delegate), reviewing evaluation numbers before they go in the PPT, recording the video, and any deployment credential/account setup (CDS account, hosting account) that requires a human to click "accept terms."
- **Too risky to delegate blindly**: the exact bust-threshold percentile choice (Task 06) and the final "does the ML model genuinely beat baseline" call (Task 09) should always get a human eyeball before being treated as final, even though an agent computes them — these are the numbers the whole PPT narrative rests on.

## 5. Credit Efficiency Strategy

- One task at a time, from the Build Map below, in order; do not let an agent "get ahead" and start Task 08 work while Task 05 is still unverified.
- Each task's prompt to the agent should reference **`PROJECT_CONTEXT.md`** (kept short, updated after every task with: what exists now, what the next task is, any gotchas found) instead of re-explaining the whole project every time.
- No re-generation of already-working code "for style" — only touch files a task explicitly requires.
- Smoke test after every task before proceeding; a failing smoke test gets ONE targeted fix prompt, not a full task re-do.
- Batch related small changes into one task rather than issuing many tiny separate agent calls for trivial edits.

**`PROJECT_CONTEXT.md` template (create in Task 01, update after every task):**
```markdown
## Status (last updated: <task N>)
- Working: <bullet list of what functions/scripts/endpoints exist and pass their smoke test>
- In progress: <current task>
- Known gotchas: <e.g., "Open-Meteo previous-runs endpoint needs `models=` param or it 400s">
- Do NOT touch: <files that are done and tested>
- Next task: <Task N+1 title + one-line goal>
```

## 6. API Contracts

Small, fixed set — **[RECOMMENDATION]**, FastAPI, JSON in/out:

| Endpoint | Method | Purpose |
|---|---|---|
| `/reliability` | GET | region + lead-time array → confidence band + bust probability per lead time |
| `/bust-probability` | GET | region + lead time → raw calibrated probability + error-distribution context |
| `/region-confidence-map` | GET | whole sub-region, one lead time → per-cell confidence, for the map layer |
| `/explain` | GET | region + lead time + date → rule-based summary + SHAP top features |
| `/rag-query` | POST | free-text question, or auto-triggered from `/explain` output → cited explanation |
| `/replay` | GET | a historical date → what the model would have said then + what actually happened |
| `/metrics` | GET | model performance summary (AUC, PR-AUC, calibration data, baseline comparison) — powers the Model Performance dashboard panel |

## 7. Testing Strategy & Smoke Tests

Each task in §9 specifies its own smoke test. General principle: a smoke test is a **fast, deterministic, real-data check** (not a mock) — e.g., "pull 3 days of data for 1 grid cell and assert the response has the expected columns and no nulls in the truth column" — never testing against fabricated fixture data that isn't representative of the real pipeline.

## 8. Failure Modes & Recovery

| Risk | Early warning | Fallback |
|---|---|---|
| Open-Meteo historical archive gap/outage for chosen region/dates | Task 02/03 smoke pull returns nulls or errors | Shrink date window or shift sub-region slightly; fall back to direct ERA5-via-CDS or TIGGE (§DATA_STRATEGY backup) |
| Download too large / too slow | Task 03 pull exceeds a few minutes for 1 month of data | Shrink grid-point count or reduce to fewer lead times |
| Too few bust events in chosen stratum | Task 06 shows near-zero positive rate for some strata | Lower the percentile threshold slightly (document why) or merge thin strata (e.g., combine adjacent lead times) |
| Class imbalance hurts model | Task 09 metrics show poor PR-AUC despite good ROC-AUC | Apply class weighting; report PR-AUC prominently; adjust the classification threshold, don't just report accuracy |
| Leakage suspected | Test-set performance implausibly high vs. validation | Re-audit historical-stat feature computation per fold (§MODEL_METHODOLOGY §8); re-run temporal split |
| RAG hallucinates | Manual eval (§RAG_BIBLE §10) flags an invented claim | Tighten prompt constraint; add the structured-output numeric check; reduce k or raise similarity threshold |
| Map/dashboard perf issues | Rendering >8–15 grid cells lags in the browser | Aggregate to a coarser display grid; use static PNG/SVG choropleth instead of live tile re-render if needed |
| Free-tier deployment breaks during judging | Any live-demo dependency fails a pre-demo check | **Historical replay mode, pre-fetched and bundled, is the default demo path** — it needs no live API at demo time |
| Agent introduces a subtle bug mid-refactor | Smoke test fails after a task that "shouldn't have touched" a file | Revert to last known-good commit; re-issue a narrower, more explicit task prompt |

## 9. 72-Hour Schedule

**DAY 1 — Data → Label → Baseline (scientific-core start)**
- Morning: Task 01 (skeleton), Task 02 (source validation + region/window decision).
- Midday: Task 03 (small real sample pull, then full-window pull).
- Afternoon: Task 04 (alignment), Task 05 (error calculation).
- Evening: Task 06 (bust label), Task 07 (climatological + logistic baseline) — **milestone: a real, if crude, baseline number exists by end of Day 1.**

**DAY 2 — Model → Validation → API/Dashboard skeleton**
- Morning: Task 08 (LightGBM model, time-aware split), Task 09 (full evaluation suite incl. baseline comparison).
- Midday: Task 10 (calibration), Task 11 (SHAP + rule-based explainability) — **milestone: scientific core fully done and verified by midday Day 2, per PRD stop condition.**
- Afternoon: Task 12 (API endpoints wrapping the trained model), Task 13 (dashboard map skeleton).
- Evening: Task 14 (region-detail view + Why-panel).

**DAY 3 — RAG → Historical Replay → Integration → Polish → Demo materials**
- Morning: Task 15 (RAG corpus + retrieval + generation), Task 16 (historical replay mode, pre-fetched).
- Midday: Task 17 (integration pass across frontend/backend), Task 18 (deployment attempt, with local-fallback accepted per stop condition) — **no new features after midday, per PRD stop condition.**
- Afternoon: Task 19 (final smoke test of the whole flow), Task 20 (demo/video/PPT preparation, screenshots, script per DEMO_AND_PPT_BIBLE.md).

Priority order if time runs short at any point: **DATA → LABEL → BASELINE → MODEL → VALIDATION** always come before **DASHBOARD → RAG → POLISH → VIDEO/PPT**, per PRD non-negotiable ordering.

## 10. Build Map — Task by Task

> Each task below follows: TASK ID · TITLE · PURPOSE · PRECONDITIONS · AGENT · PROMPT · FILES CHANGED · OUTPUT · SMOKE TEST · PASS CONDITION · FAILURE/RECOVERY · COMPLEXITY · DEPENDENCIES.

**TASK 01 — Repository + Project Skeleton**
- Purpose: create the folder structure (§2) and `PROJECT_CONTEXT.md`.
- Preconditions: none.
- Agent: Antigravity.
- Prompt: *"Create the repository skeleton exactly as specified in BUILD_MAP_BIBLE.md §2, plus an initial PROJECT_CONTEXT.md using the template in §5. Do not add any dependencies or code beyond empty/stub files yet."*
- Files: all top-level folders + `PROJECT_CONTEXT.md` + empty `README.md`.
- Output: runnable empty scaffold.
- Smoke test: `ls -R` matches the expected structure.
- Pass condition: structure matches §2.
- Failure/Recovery: re-issue with an explicit tree diagram (already given above).
- Complexity: trivial. Dependencies: none.

**TASK 02 — Data-Source Validation + Region/Window Decision**
- Purpose: confirm Open-Meteo Previous-Runs/Single-Runs/ERA5 endpoints actually return usable data for candidate India sub-regions; lock the bounding box, date window, and grid-point list.
- Preconditions: Task 01 done.
- Agent: Antigravity for the API probing script; **human** for the final region/window decision (too judgment-heavy to fully delegate).
- Prompt: *"Write a small script in src/ingest/ that queries the Open-Meteo Previous Runs API and ERA5 archive API for 3 candidate India bounding boxes (to be provided) and reports date coverage, null-rate, and variable availability for rainfall. Do not process or model the data yet — just report coverage."*
- Files: `src/ingest/validate_sources.py`.
- Output: a coverage report (printed/CSV) per candidate region.
- Smoke test: script runs end-to-end without error and returns non-empty coverage stats for at least one candidate region.
- Pass condition: at least one region shows >90% non-null coverage across the target window.
- Failure/Recovery: try an alternate bounding box or shrink the window; consult DATA_STRATEGY.md §4 backup sources.
- Complexity: low. Dependencies: Task 01.

**TASK 03 — Download Real Sample, Then Full Window**
- Purpose: pull real forecast + truth data for the locked region/window.
- Preconditions: Task 02 decision made.
- Agent: Antigravity.
- Prompt: *"Using the locked region/window from PROJECT_CONTEXT.md, first pull 1 month of Previous-Runs forecast data + matching ERA5 truth for the chosen grid points, save to data/raw/ as parquet, and print row counts and null rates. Only after I confirm this looks correct, extend the same script to pull the full window."*
- Files: `src/ingest/pull_forecasts.py`, `src/ingest/pull_era5.py`, `data/raw/*.parquet`.
- Output: raw parquet files.
- Smoke test: row count roughly matches expectation (issue-dates × lead-times × grid-points), no fully-null columns.
- Pass condition: human confirms the 1-month sample looks sane before Antigravity is told to scale to the full window.
- Failure/Recovery: check for endpoint parameter errors (a common gotcha — log it in PROJECT_CONTEXT.md); shrink scope if rate-limited.
- Complexity: medium. Dependencies: Task 02.

**TASK 04 — Forecast/Observation Alignment**
- Purpose: join forecast rows to their corresponding truth value by grid cell + valid time.
- Preconditions: Task 03 full pull done.
- Agent: Antigravity.
- Prompt: *"Write src/features/align.py that joins data/raw forecast and ERA5 truth on (grid_cell, valid_time), producing data/aligned/aligned.parquet with columns: issue_time, valid_time, lead_time_days, grid_cell, lat, lon, forecast_value, truth_value. Drop rows with no truth match; log the drop rate."*
- Files: `src/features/align.py`, `data/aligned/aligned.parquet`.
- Output: aligned table.
- Smoke test: no row has both a forecast and a null truth; drop rate is reported and <10%.
- Pass condition: drop rate acceptable, spot-check 5 rows manually against raw sources.
- Failure/Recovery: check timezone/rounding mismatches between forecast valid-time and ERA5 timestamp granularity — a classic silent alignment bug.
- Complexity: medium. Dependencies: Task 03.

**TASK 05 — Error Calculation**
- Purpose: compute the per-row forecast error using the variable-appropriate metric (MODEL_METHODOLOGY.md §3).
- Preconditions: Task 04 done.
- Agent: Antigravity.
- Prompt: *"Implement src/features/error.py computing, for rainfall, the climatology-relative error described in MODEL_METHODOLOGY.md §3: first compute per-grid-cell/day-of-year climatology from the ERA5 truth series, then express each row's |forecast-truth| as a percentile within that cell/season's historical error distribution. Add columns: climatology_value, error_raw, error_percentile."*
- Files: `src/features/error.py`, updated `data/aligned/aligned.parquet` (or a new `data/features/errors.parquet`).
- Output: error-annotated table.
- Smoke test: `error_percentile` is between 0–100 for all rows; distribution isn't degenerate (not all zeros/ones).
- Pass condition: spot-check the climatology computation against a manual calculation for 2–3 rows.
- Failure/Recovery: check enough history exists per grid cell to compute a stable climatology; widen the day-of-year window (e.g., ±7 days) if too sparse.
- Complexity: medium. Dependencies: Task 04.

**TASK 06 — Bust Label Definition**
- Purpose: derive the stratified percentile threshold and produce the binary bust label.
- Preconditions: Task 05 done.
- Agent: Antigravity, with **human** review of the chosen percentile and resulting bust-rate table (per PRD "too risky to delegate blindly").
- Prompt: *"Implement src/features/bust_label.py: for each (lead_time_bucket, region_group, season) stratum, compute the 85th, 87.5th, and 90th percentile of error_percentile/error_raw as candidate thresholds, output a table of resulting bust-rate per stratum for each candidate percentile, and do not pick one — present the table for review."*
- Files: `src/features/bust_label.py`, `data/features/bust_rate_report.csv`.
- Output: candidate threshold report.
- Smoke test: report is non-empty and shows plausible bust rates (roughly 8–20%) for most strata at at least one candidate percentile.
- Pass condition: human picks the final percentile from the report; Antigravity then re-runs to bake in the chosen label as `data/features/labeled.parquet`.
- Failure/Recovery: if all strata show near-0% or near-100% bust rate at every candidate, revisit error metric (Task 05) before touching thresholds further.
- Complexity: medium. Dependencies: Task 05.

**TASK 07 — Baselines**
- Purpose: build the climatological lookup-table baseline and the logistic-regression baseline.
- Preconditions: Task 06 labeled data ready.
- Agent: Antigravity.
- Prompt: *"Implement src/models/baseline.py: (a) a climatological baseline that predicts each row's stratum historical bust rate as its probability, computed strictly from prior-in-time rows only per the temporal split in MODEL_METHODOLOGY.md §8; (b) a logistic regression on the MVP feature set. Evaluate both on a chronological 70/15/15 split and print ROC-AUC, PR-AUC, Brier score."*
- Files: `src/models/baseline.py`, `models/baseline_metrics.json`.
- Output: first real baseline numbers.
- Smoke test: both baselines run end-to-end and produce metrics in [0,1] ranges.
- Pass condition: numbers are sane (not exactly 0.5 AUC everywhere, not exactly 1.0 either — either extreme signals a bug).
- Failure/Recovery: re-check temporal split boundaries and that historical-stat features are computed per-fold, not globally (leakage check).
- Complexity: medium. Dependencies: Task 06.

**TASK 08 — First ML Model**
- Purpose: train LightGBM (or XGBoost) on the same split.
- Preconditions: Task 07 done (baseline numbers exist for comparison).
- Agent: Antigravity.
- Prompt: *"Implement src/models/train.py: train a LightGBM classifier on the same feature set and split as baseline.py, with class weighting for the bust-rate imbalance. Save the model to models/model.txt. Print the same metrics as the baseline for direct comparison."*
- Files: `src/models/train.py`, `models/model.txt`.
- Output: trained model + metrics.
- Smoke test: model trains without error in a reasonable time (minutes, not hours) on local/Colab-free compute.
- Pass condition: metrics print successfully; whether it beats baseline is assessed in Task 09, not assumed here.
- Failure/Recovery: if LightGBM install fails on the agent's environment, fall back to XGBoost or scikit-learn's `HistGradientBoostingClassifier`.
- Complexity: medium. Dependencies: Task 07.

**TASK 09 — Full Evaluation Suite**
- Purpose: produce every metric in MODEL_METHODOLOGY.md §9, with mandatory baseline comparison.
- Preconditions: Task 08 done.
- Agent: Antigravity, with **human** sign-off on the final "ML beats baseline" claim.
- Prompt: *"Implement src/models/evaluate.py producing: ROC-AUC, PR-AUC, precision/recall/F1 at a justified threshold, confusion matrix, Brier score, a reliability diagram, lead-time-stratified and region-stratified performance tables, and a side-by-side comparison table against baseline.py's numbers, all computed on the same held-out test set. Save all outputs to models/evaluation/."*
- Files: `src/models/evaluate.py`, `models/evaluation/*`.
- Output: the numbers that go directly into the PPT.
- Smoke test: all outputs generate without error; reliability diagram is monotonic-ish (not wildly miscalibrated in the raw pre-calibration model — that's expected and fixed in Task 10).
- Pass condition: **this is the milestone gate — scientific core must be done and human-reviewed before Task 10 begins.**
- Failure/Recovery: if ML does not beat baseline, do not fabricate a better number — revisit features (Task 05/06) or accept and honestly report a smaller/partial improvement in the PPT.
- Complexity: medium-high. Dependencies: Task 08.

**TASK 10 — Calibration**
- Purpose: isotonic calibration on validation fold, re-evaluate reliability on test fold.
- Preconditions: Task 09 milestone passed.
- Agent: Antigravity.
- Prompt: *"Implement src/models/calibrate.py: fit isotonic regression on the validation fold's raw model outputs vs. true labels, save to models/calibrator.pkl, then apply to the test fold and regenerate the reliability diagram from Task 09 for comparison (before/after calibration)."*
- Files: `src/models/calibrate.py`, `models/calibrator.pkl`.
- Output: calibrated probabilities + before/after reliability comparison.
- Smoke test: calibrated reliability diagram is visibly closer to the diagonal than the raw one.
- Pass condition: visible calibration improvement, or a documented reason why isotonic didn't help (e.g., too little validation data — fall back to Platt scaling).
- Failure/Recovery: switch to Platt/sigmoid calibration if isotonic overfits on a small validation fold.
- Complexity: low-medium. Dependencies: Task 09.

**TASK 11 — Explainability**
- Purpose: SHAP values + rule-based plain-language driver summary.
- Preconditions: Task 10 done.
- Agent: Antigravity for SHAP plumbing; Claude for writing the rule-based-summary logic and phrasing (judgment-heavy natural-language mapping from feature values to plain sentences).
- Prompt (Antigravity): *"Implement src/explain/shap_explain.py producing global SHAP summary values and a per-row top-3-feature extraction function, saved as a reusable module the API can call."* Prompt (Claude): *"Given MODEL_METHODOLOGY.md §5's feature list, write the rule-based mapping logic in src/explain/rules.py that turns raw feature values into plain-language driver phrases (e.g., 'high disagreement with neighboring grid forecasts'), used as Level 1 explainability and as RAG's query input."*
- Files: `src/explain/shap_explain.py`, `src/explain/rules.py`.
- Output: reusable explanation functions.
- Smoke test: for 5 sample rows, both functions return non-empty, sensible outputs.
- Pass condition: human spot-checks 3 explanations for plausibility.
- Failure/Recovery: if SHAP is too slow on the full test set, compute it only for the rows the demo/dashboard actually needs, not the entire dataset.
- Complexity: medium. Dependencies: Task 10.

**TASK 12 — Confidence/Bust-Probability API**
- Purpose: wrap the trained + calibrated model and explainability functions in FastAPI endpoints.
- Preconditions: Task 11 done.
- Agent: Antigravity.
- Prompt: *"Implement src/api/main.py (FastAPI) with the endpoints listed in BUILD_MAP_BIBLE.md §6 except /rag-query and /replay (later tasks): /reliability, /bust-probability, /region-confidence-map, /explain, /metrics. Load model.txt + calibrator.pkl once at startup, not per request."*
- Files: `src/api/main.py`, `src/api/schemas.py`.
- Output: running local API.
- Smoke test: `curl` each endpoint locally with a valid region/lead-time and confirm a well-formed JSON response, no 500s.
- Pass condition: all 5 endpoints respond correctly for at least one real region/lead-time combination.
- Failure/Recovery: check model/calibrator file paths and that feature-computation-at-request-time matches training-time feature logic exactly (a common serving/training skew bug).
- Complexity: medium. Dependencies: Task 11.

**TASK 13 — Dashboard: Command Center Map**
- Purpose: React map view showing regional confidence for a selectable lead time.
- Preconditions: Task 12 API running.
- Agent: Antigravity.
- Prompt: *"Build frontend/ (React+Vite+Tailwind) with a Command Center view: a Leaflet map of the chosen sub-region, colored by confidence band per grid cell, fetched from /region-confidence-map, with a Day 1/3/5/7/10 selector."*
- Files: `frontend/src/CommandCenter.jsx` (+ supporting files).
- Output: working map view against the live local API.
- Smoke test: map renders real API data (not mock JSON) for at least 2 different lead-time selections.
- Pass condition: human visually confirms the map looks reasonable and reacts to the lead-time selector.
- Failure/Recovery: if too many grid cells lag rendering, aggregate to a coarser display grid (per §Failure Modes).
- Complexity: medium. Dependencies: Task 12.

**TASK 14 — Region Detail + Why-Panel**
- Purpose: drill-down view per region: confidence by lead time, and the "Why is confidence low?" explanation panel.
- Preconditions: Task 13 done.
- Agent: Antigravity.
- Prompt: *"Add a Region Detail view: clicking a map cell shows a lead-time confidence chart (Plotly) from /reliability, plus a Why-panel showing /explain's rule-based summary and SHAP bars for that cell/lead-time. Leave a placeholder slot for the RAG explanation text (filled in Task 17)."*
- Files: `frontend/src/RegionDetail.jsx`, `frontend/src/WhyPanel.jsx`.
- Output: working drill-down view.
- Smoke test: clicking any rendered cell opens a detail view with real (non-mock) data.
- Pass condition: human confirms the drill-down flow works end to end.
- Failure/Recovery: none expected beyond standard frontend debugging.
- Complexity: medium. Dependencies: Task 13.

**TASK 15 — RAG Build**
- Purpose: corpus ingestion, embedding, FAISS index, retrieval, and cited generation.
- Preconditions: Task 11 explanation functions exist (RAG's query input).
- Agent: Claude (corpus curation, prompt engineering) + Antigravity (ingestion/embedding/index code, /rag-query endpoint).
- Prompt (Claude): *"Curate 15-30 short, high-signal meteorological reference documents per RAG_BIBLE.md §2, save as text files in a rag_corpus/ folder with source metadata headers."* Prompt (Antigravity): *"Implement src/rag/ingest.py (chunk + embed with sentence-transformers + build FAISS index), src/rag/retrieve.py, and add a /rag-query POST endpoint to the API implementing the prompt structure in RAG_BIBLE.md §6, including the structured-output numeric check from §8."*
- Files: `rag_corpus/*.txt`, `src/rag/ingest.py`, `src/rag/retrieve.py`, `rag_store/*`, API update.
- Output: working cited RAG endpoint.
- Smoke test: 5 representative test queries (per RAG_BIBLE.md §10) each return a cited, non-hallucinated answer.
- Pass condition: human evaluation per RAG_BIBLE.md §10 checklist passes for all 5.
- Failure/Recovery: if answers hallucinate, tighten the prompt and lower retrieval k first before touching the corpus.
- Complexity: medium-high. Dependencies: Task 11.

**TASK 16 — Historical Replay**
- Purpose: pre-fetch a specific real past date's full pipeline output so the demo needs no live API.
- Preconditions: Tasks 12–15 done.
- Agent: Antigravity.
- Prompt: *"Implement src/api/replay.py + a /replay endpoint: given a real historical issue date within our data window, run the full inference pipeline (model + calibration + explanation + RAG) using ONLY information available as of that issue date, cache the result, then separately fetch and attach the real ERA5 truth for the valid date so the frontend can show 'predicted vs. actual.' Pre-generate and cache 2-3 good replay dates now."*
- Files: `src/api/replay.py`, `frontend/src/Replay.jsx`, cached replay JSON files.
- Output: a fully offline-capable replay demo.
- Smoke test: replay endpoint returns a complete result with zero live external calls once cached.
- Pass condition: at least one cached replay date shows a clear, honest predicted-vs-actual story (bust correctly flagged, or honestly not — either is fine, fabrication is not).
- Failure/Recovery: try a different historical date if the first pick's story is muddy or ambiguous.
- Complexity: medium. Dependencies: Tasks 12-15.

**TASK 17 — Integration Pass**
- Purpose: wire RAG output into the Why-panel placeholder from Task 14; final cross-check of all views against the live API.
- Preconditions: Task 16 done.
- Agent: Antigravity.
- Prompt: *"Connect the Why-panel's RAG placeholder to the real /rag-query endpoint, wire the Replay view into navigation, and do a full click-through of every dashboard view checking for console errors or stale mock data."*
- Files: various frontend files.
- Output: fully integrated dashboard.
- Smoke test: full click-through, zero console errors, zero mock data remaining anywhere.
- Pass condition: human does the click-through personally once.
- Failure/Recovery: standard debugging; do not add new features here, only fix integration issues.
- Complexity: low-medium. Dependencies: Task 16.

**TASK 18 — Deployment (optional) / Local Finalization**
- Purpose: attempt a free-tier public deployment; otherwise finalize a robust local run.
- Preconditions: Task 17 done.
- Agent: Antigravity.
- Prompt: *"Attempt to deploy frontend to a free static host and the API to a free small-app host, verifying current free-tier limits first. If deployment introduces any instability, stop and instead produce a one-command local startup script (start.sh) and confirm it works from a clean checkout."*
- Files: deployment configs or `start.sh`.
- Output: either a public link or a bulletproof local start script.
- Smoke test: fresh clone + `start.sh` (or the deployed link) works without manual fixing.
- Pass condition: whichever path is chosen works reliably twice in a row.
- Failure/Recovery: local-only is an acceptable final state — deployment is not required for a successful demo, per §Failure Modes.
- Complexity: low-medium. Dependencies: Task 17.

**TASK 19 — Final Smoke Test**
- Purpose: one last full end-to-end pass before demo prep.
- Preconditions: Task 18 done.
- Agent: Antigravity, human final check.
- Prompt: *"Run through every acceptance criterion in PRD_BIBLE.md §20 and report pass/fail for each with evidence (a screenshot path or output log)."*
- Files: `docs/final_smoke_report.md`.
- Output: a checked acceptance-criteria list.
- Smoke test: is itself the smoke test.
- Pass condition: all PRD §20 items pass.
- Failure/Recovery: any failing item is fixed now, before demo-prep time is spent.
- Complexity: low. Dependencies: Task 18.

**TASK 20 — Demo Preparation**
- Purpose: screenshots, video recording, PPT population, per DEMO_AND_PPT_BIBLE.md.
- Preconditions: Task 19 all-pass.
- Agent: human (recording/narration) with Claude assisting on PPT text and script per DEMO_AND_PPT_BIBLE.md.
- Prompt: n/a (human-led).
- Files: video file, PPT.
- Output: final deliverables.
- Smoke test: watch the video once end-to-end before submission.
- Pass condition: video and PPT both reference only real, already-produced numbers/screenshots.
- Failure/Recovery: none — this is the last task.
- Complexity: low (execution), high (stakes). Dependencies: Task 19.

## 11. User Operator Guide

**YOU:**
1. Open Antigravity (or Claude, per the "Agent" field on each task above).
2. Paste that task's Prompt.
3. Let it complete.
4. Run the stated Smoke Test yourself (or ask the agent to run it and show you the output).
5. If PASS → move to the next task's prompt.
6. If FAIL → paste a short, specific fix instruction referencing exactly what failed (don't re-paste the whole original task prompt).
7. Continue in order; never skip ahead.
8. At Tasks 02, 06, and 09, you personally review the decision/number before continuing (region/window choice, bust-threshold percentile, "does ML beat baseline") — these are the three "too risky to delegate blindly" checkpoints.
9. Use Colab only if local compute genuinely struggles with Task 08's model training (unlikely at this data size, but keep it as your pressure-release valve).
10. Take PPT screenshots as each dashboard view is completed in Tasks 13–17, rather than waiting until Task 20 to hunt for good screenshots retroactively.
11. Stop adding features per the STOP CONDITIONS in PRD_BIBLE.md — when in doubt, protect Task 20's time budget over any single extra feature.
