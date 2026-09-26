# PRD_BIBLE.md — Forecast Bust Detection & Reliability Engine
### Problem Statement 26079 — AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts

---

## 0. Legend
Every claim below is tagged: **[FACT]** (verified), **[ASSUMPTION]** (working hypothesis until tested), **[RECOMMENDATION]** (our chosen design), **[OPTION]** (alternative considered, not chosen).

---

## 1. Executive Summary

Medium-range NWP forecasts (Day 1–10) are usually good, but occasionally fail badly during fast-evolving systems — monsoon depressions, western disturbances, heavy-rain bursts, heat waves. Forecasters currently have no systematic, quantitative early-warning signal for *when a specific forecast, for a specific place and lead time, is unusually likely to be wrong*.

We are building a **Forecast Reliability Engine**: a machine-learned model that looks at a live/historical NWP forecast, compares its behaviour (spread, revision, regime) against decades of historical forecast-error patterns for that variable/region/lead-time/season, and outputs a **calibrated probability that this forecast will "bust"** — plus a plain-language and literature-grounded explanation of *why*.

**[RECOMMENDATION]** Positioning: *"A forecast reliability and early-warning decision-support system, not a replacement for NWP."* Product promise: *"Don't just ask what the forecast says. Ask how much you should trust it."*

The system is **not** a chatbot wrapper. The ML core (bust-probability model, trained on real forecast-vs-reality error history) must work end-to-end and produce genuine, tested numbers even with the RAG/LLM layer switched off. RAG is an explanation layer bolted on top of real model outputs, never a substitute for them.

---

## 2. Problem

- NWP models (GFS, ECMWF IFS, IMD's own models) are generally skillful at Day 1–3 and degrade gradually to Day 10. But the degradation is **not uniform**: certain regions, seasons, variables and synoptic regimes (active monsoon onset, cyclogenesis, western disturbance interaction with the Himalayas) produce much larger and more volatile errors than the "average" skill score would suggest.
- Forecasters and disaster managers currently rely on experience and manual cross-checking (ensemble spread, multi-model agreement) to judge whether *this particular* forecast run is trustworthy — this is slow, inconsistent, and not scalable to daily operations across all districts.
- There is no simple, standard, *quantified* "trust score" attached to a medium-range forecast product today, comparable to how a weather app shows a temperature number but never a "how sure are we" number.

## 3. Users

**[RECOMMENDATION]**

**Primary user: State/District Disaster Management Authorities and IMD-adjacent operational forecasters.**
Why: they must decide *today* whether to issue alerts, pre-position resources, or wait — for exactly the Day 1–10 horizon this system targets. They are harmed most by forecast busts (over-warning fatigue, or under-warning during a real event) and stand to benefit most from an explicit reliability signal layered on top of the official forecast, without needing to reinterpret raw NWP output themselves.

**Secondary users:**
- **Agro-advisory services / Krishi Vigyan Kendras** — sowing/harvest/irrigation timing decisions are sensitive to rainfall bust risk in the 3–10 day window.
- **Aviation / logistics / power-grid operations planners** — need to know when a Day 3–7 wind/temperature forecast is unreliable enough to trigger contingency planning.
- **Operational meteorologists at IMD/state met centres** — as a second-opinion QC tool layered on top of their own multi-model comparison workflow, not a replacement for their forecast issuance authority.
- **Researchers in forecast verification** — the historical-analogue and error-attribution tooling is directly reusable for verification science.

**[ASSUMPTION]** We do not claim any of these users today have API-level integration appetite in 3 days; the MVP demonstrates the concept at dashboard level, not as an already-integrated operational feed.

## 4. Goals

1. Produce a **real, tested, probabilistic bust/confidence estimate** per region–variable–lead-time, derived from genuine historical forecast-error learning (not hardcoded thresholds dressed up as AI).
2. Show that the ML model **beats a simple climatological baseline** on a held-out, time-safe test set, using standard verification metrics.
3. Provide **explainability** at three levels: rule-based driver summary, feature-importance/SHAP, and a RAG-grounded meteorological explanation with citations.
4. Ship a working dashboard + a small API that a non-technical demo audience can operate live, plus a historical-replay mode that does not depend on any live API being up during judging.
5. Do all of this inside a 3-day, credit-efficient, agent-driven build process, with clean fallbacks at every stage.

## 5. Non-Goals (explicitly out of scope for the hackathon)

- We are **not** replacing or recalibrating the NWP model itself (no data assimilation, no new physical forecast).
- We are **not** building a full India-wide, all-variable, all-regime operational system in 3 days — geographic and variable scope is deliberately narrowed (see MVP).
- We are **not** claiming operational-grade accuracy, uptime, or official-warning authority. The system is explicitly a research/decision-support prototype.
- We are **not** hand-building a custom NWP verification archive from scratch — we reuse existing free forecast-archival infrastructure (see DATA_STRATEGY.md).
- We are **not** doing full regime classification (active/break monsoon, cyclogenesis detection) as a supervised sub-model in the MVP — these are Tier 3 roadmap items.

## 6. Use Cases

1. **District officer view**: "Show me Day 1–10 rainfall bust probability for my district this week, and tell me in one sentence why Day 6 looks unreliable."
2. **Forecaster QC view**: "Which regions have the least trustworthy Day 3 temperature forecast right now, and what does the historical error distribution for this lead time/season look like?"
3. **Analyst / researcher view**: "Show me 10 historical situations similar to the current forecast pattern, and how many of them busted."
4. **Judge / demo view (historical replay)**: "Rewind to a real date in the past, show what the model would have said using only information available then, then reveal what actually happened."

## 7. Functional Requirements

- FR1: Ingest historical forecast data (issued-at-time-t, valid-at-time-t+n) and the corresponding real observation/reanalysis "truth" for the same location/time, for at least one core variable (rainfall) over India, spanning at least 1–2 years and ideally more.
- FR2: Compute forecast error and define a defensible "bust" label conditioned on lead time / region / season, from the real error distribution — never an arbitrary constant threshold.
- FR3: Train and validate at least one baseline model and one stronger ML model, with strict time-aware splitting (no leakage).
- FR4: Output, per grid cell / region and lead time (Day 1–10): (a) bust probability, (b) a human-interpretable confidence label, (c) top contributing features.
- FR5: Serve outputs via a small REST API and a map-based dashboard, plus a region-detail drill-down view.
- FR6: Provide a RAG-backed explanation endpoint that turns model drivers into a cited, meteorologically grounded explanation, without inventing facts the model didn't produce.
- FR7: Provide a historical-replay mode: pick a past date, show what the model predicted using only pre-that-date information, then reveal the real outcome.
- FR8: Show model performance (metrics, calibration) transparently inside the dashboard.

## 8. Scientific Definitions

See MODEL_METHODOLOGY.md for full detail. Summary:

- **Forecast error**: a variable-appropriate distance between the forecast valid at t+n (issued at t) and the best available real reference for that same time/place (ERA5 reanalysis, or IMD gridded observation where usable).
- **Forecast anomaly**: forecast value minus the local climatological normal for that day-of-year/location — used as a feature, not the target.
- **Forecast bust**: a binary label = 1 when the forecast error, at a given variable/lead-time/region/season, exceeds a *data-derived* high percentile (e.g. 85th–90th) of the historical error distribution for that stratum — i.e., an operationally unusual, meaningfully large miss, not an arbitrary fixed number.
- **Forecast confidence**: 1 − calibrated bust probability, presented with a plain-language band (High / Moderate / Low reliability) rather than a bare number.
- **Bust probability**: the model's calibrated P(error exceeds the bust threshold | current forecast-derived features).

## 9. Data Requirements

See DATA_STRATEGY.md. **[RECOMMENDATION]** Primary: Open-Meteo's free Historical Forecast / Previous-Runs / Single-Runs APIs (forecast side) + ERA5 reanalysis (truth side), both reachable via simple JSON HTTP, no API key, since they solve the exact "forecast issued at t + truth at t+n" requirement with minimal engineering burden. Backup: direct ECMWF TIGGE archive (GRIB2, via ECDS) for ensemble-based spread features, and IMD 0.25° gridded rainfall as an India-specific truth cross-check.

## 10. ML Requirements

See MODEL_METHODOLOGY.md. Gradient-boosted trees (LightGBM/XGBoost) as the primary model, logistic regression as baseline, isotonic/Platt calibration, SHAP for explainability, strict temporal validation.

## 11. RAG Requirements

See RAG_BIBLE.md. Grounded in real meteorological reference material (WMO, IMD, ECMWF documentation, peer-reviewed verification literature), retrieval-augmented, always cited, never permitted to state a probability or invent an event the ML layer didn't produce.

## 12. Explainability Requirements

Three layers, always in this order, always consistent with each other:
1. Rule-derived plain-language driver list from the feature values themselves.
2. SHAP/feature-importance ranking from the trained model.
3. RAG-generated meteorological narrative that explains layer-2's top features using retrieved literature, with citations, and never claiming causal certainty beyond what verification science supports.

## 13. Dashboard Requirements

Command Center map → Region Detail → "Why is confidence low?" panel → Historical Analogues (stretch) → RAG Assistant → Model Performance panel. See BUILD_MAP_BIBLE.md and DEMO_AND_PPT_BIBLE.md for exact layout and priority order.

## 14. API Requirements

Small, fixed set of endpoints (forecast reliability, bust probability, regional confidence, feature explanation, historical replay, RAG query, model metrics). See BUILD_MAP_BIBLE.md §API Contracts.

## 15. Evaluation Requirements

ROC-AUC, PR-AUC, precision/recall/F1, confusion matrix, Brier score, reliability diagram, lead-time-stratified performance, region-stratified performance, and a mandatory head-to-head comparison against the climatological baseline. No metric is reported without the baseline comparison alongside it.

## 16. Constraints

- 3-day build, agent-driven (Antigravity primary, Claude secondary), strict credit efficiency, one task at a time.
- No datasets/APIs provided by organizers — must use free, real, externally accessible sources.
- No synthetic data anywhere in the final architecture; any unavoidable placeholder must be explicitly labeled as a temporary dev placeholder and must not appear in the demo.
- Must degrade gracefully if any live API is down during judging (historical replay is the primary demo mode for exactly this reason).

## 17. MVP (Tier 1)

- Variable: **rainfall** only (mm/24h accumulated).
- Geography: a **bounded India sub-region** with strong monsoon-season signal (e.g. a west-coast/central-India rectangle spanning several IMD subdivisions) at ERA5/Open-Meteo native grid resolution (~0.25°–0.4°), aggregated to a small set of representative points/cells for the demo — not full India at full resolution.
- Data window: as much historical Previous-Runs/Historical-Forecast + ERA5 overlap as can be pulled in the time budget (realistically a recent 1–3 year window, see DATA_STRATEGY.md for exact dates).
- Lead times: Day 1, 3, 5, 7, 10 (a representative subset of Day 1–10, not necessarily every single day, to control data volume).
- Model: logistic regression baseline + LightGBM/XGBoost primary model, with basic calibration.
- Explainability: rule-based + SHAP. RAG present but with a small, curated (not massive) corpus.
- Dashboard: Command Center map + Region Detail + Why-panel + Model Performance. Historical replay for the demo.
- API: the 6–7 endpoints listed above, backing the dashboard only (not hardened for external third-party use).

## 18. Advanced / Future (Tier 3, roadmap only — do not build now)

Weather-regime-aware sub-models (active/break monsoon, western disturbance, cyclogenesis classifiers), multi-NWP ensemble disagreement features, full India + full variable set, conformal-prediction uncertainty bounds, transformer/graph-based spatio-temporal models, online model updating and drift detection, decision-impact scoring and alerting integration, ensemble spread from full TIGGE multi-centre archive.

## 19. Risks

See BUILD_MAP_BIBLE.md §Failure Modes for the full table (data availability, class imbalance, leakage, compute limits, RAG hallucination, deployment fragility, agent-introduced bugs).

## 20. Acceptance Criteria (MVP "done")

- [ ] Real forecast + real truth data pulled and aligned for the chosen sub-region/window, zero synthetic rows.
- [ ] Bust label built from an empirically derived percentile threshold, documented per stratum.
- [ ] Baseline and ML model both trained on a leakage-safe, time-ordered split; ML beats baseline on at least one primary metric (documented, not assumed).
- [ ] Reliability diagram and lead-time-stratified performance produced from real held-out predictions.
- [ ] Dashboard renders live model outputs (not mocked JSON) for at least the Command Center and Region Detail views.
- [ ] RAG answers at least 5 representative meteorological questions with citations, without contradicting model outputs.
- [ ] Historical replay works fully offline (pre-fetched data), independent of any live API during judging.
- [ ] PPT and video demo reference only real, executed numbers — nothing is a placeholder in the final materials.

---

## WHAT WE ARE ACTUALLY BUILDING

A rainfall-focused forecast reliability engine for a defined Indian sub-region. It pulls real historical medium-range forecasts and compares them against real ERA5/observation truth to learn, statistically, when and where forecasts have historically gone badly wrong by lead time, season, and location. A gradient-boosted model outputs a calibrated bust probability and confidence label for Day 1/3/5/7/10, beating a climatological baseline on standard verification metrics computed on a proper time-safe holdout. Every low-confidence result is explained three ways: plain rules, SHAP drivers, and a cited RAG narrative grounded in real meteorological documentation — never inventing reasons the model didn't produce. A map dashboard and a small API expose this, and a historical-replay mode lets us demo a real past date (prediction vs what actually happened) without depending on any live service being up during judging. It is explicitly a decision-support layer on top of official NWP output, not a replacement for it.

## FIRST 10 THINGS WE WILL DO

1. Stand up the repo skeleton + `PROJECT_CONTEXT.md` (Task 01).
2. Validate Open-Meteo Previous-Runs/Historical-Forecast + ERA5 access for the chosen sub-region with a tiny manual smoke pull (Task 02).
3. Pick and lock the exact sub-region (bounding box), variable (rainfall), lead times, and date window (Task 02, human decision).
4. Download a small real sample (1 month) end-to-end and confirm forecast/truth alignment works (Task 03).
5. Scale the download to the full chosen window (Task 03b).
6. Build the forecast/observation alignment table (Task 04).
7. Compute forecast error per row and derive the stratified bust-threshold table (Task 05–06).
8. Build and evaluate the climatological baseline (Task 07).
9. Train the first LightGBM/XGBoost bust-probability model with a time-aware split (Task 08).
10. Run the full evaluation suite (ROC-AUC, PR-AUC, calibration, baseline comparison) and only then proceed to dashboard/RAG work (Task 09).

## STOP CONDITIONS

- Stop adding variables/geography the moment rainfall-over-the-chosen-sub-region works end to end — do not expand scope "because there's time," expand only if Day-2 finishes early and Day-3 buffer is still intact.
- Stop model iteration once ML beats baseline on ROC-AUC/PR-AUC with a believable reliability diagram — do not chase marginal metric gains at the expense of dashboard/demo time.
- Stop adding dashboard views once Command Center + Region Detail + Why-panel + Model Performance work — Historical Analogues and RAG Assistant chat are the first things cut if time runs short.
- Stop RAG corpus growth once ~15–30 solid documents answer the demo's anticipated questions — do not try to ingest an exhaustive meteorological library.
- By end of Day 2 evening: scientific core (data→label→baseline→model→evaluation) must be fully working, or the plan must be re-scoped that night, not on Day 3.
- On Day 3: no new features after midday. Afternoon is polish, video, and PPT only.

## ONE-PAGE MASTER MAP

```
DATA (Open-Meteo forecasts + ERA5 truth, India sub-region, rainfall)
   ↓
ERROR (forecast − truth, variable-appropriate metric)
   ↓
BUST LABEL (stratified empirical high-percentile threshold: variable × lead time × region × season)
   ↓
ML (LightGBM/XGBoost bust-probability model vs. logistic-regression + climatology baselines)
   ↓
CALIBRATION (isotonic/Platt on held-out fold)
   ↓
CONFIDENCE (1 − calibrated bust probability → High/Moderate/Low band, Day1–10 × region)
   ↓
EXPLANATION (rule-based drivers → SHAP feature importance)
   ↓
RAG (cited meteorological narrative grounded in explanation layer, never overriding the model)
   ↓
API (reliability, bust-probability, region, explanation, replay, RAG-query, metrics endpoints)
   ↓
DASHBOARD (Command Center map → Region Detail → Why-panel → Historical Analogues → RAG chat → Model Performance)
   ↓
DEMO (historical replay: predict on past date with only pre-date info, then reveal real outcome)
```
