# MODEL_METHODOLOGY.md — Scientific Core

Legend: **[FACT]** · **[ASSUMPTION]** · **[RECOMMENDATION]** · **[OPTION]**

---

## 1. Formal Prediction Problem

For a given variable *v* (rainfall, primary), grid cell/location *g*, forecast issue time *t*, and lead time *n* (Day 1, 3, 5, 7, 10):

- Forecast value: `F(v, g, t, n)` — the value predicted at issue time *t* for valid time *t+n*.
- Truth value: `O(v, g, t+n)` — the real/ERA5-reanalysis value observed at valid time *t+n*.
- **Forecast error**: `E = error_metric(F, O)` (metric chosen per variable, §3).
- **Bust label**: `Y = 1` if `E > threshold(v, g_region, n, season)`, else `0` — threshold is **empirically derived**, not fixed (§4).
- **Target**: estimate `P(Y = 1 | X)` where `X` is a feature vector built only from information available **at issue time t** (never from `O` or from anything only knowable after *t*).

This is a **binary classification with a probabilistic, calibrated output** — not a point regression of the error itself, because operational users care about "is this forecast trustworthy" (a decision-relevant yes/no with a confidence) more than the raw error magnitude, though we also report the underlying error distribution for full transparency (§9).

## 2. Single Global Model vs. Variable/Lead-Time-Specific vs. Hierarchical

**[RECOMMENDATION]**: A **single model per variable**, with **lead time as a feature** (not a separate model per lead time), plus region/season as features. This is the standard, credit-efficient approach: it lets the model learn shared structure (errors grow with lead time in a smooth, learnable way) while still being able to specialize behavior conditionally on lead time via tree splits. A fully separate model per lead time (5 models) multiplies training/maintenance cost for a 3-day sprint with limited data volume per stratum, and a single monolithic model across *all* variables at once would dilute rainfall-specific signal for no benefit in the MVP (only rainfall is modeled in Tier 1).

**[OPTION, future]**: A genuinely hierarchical model (global base model + regime-specific fine-tuned heads for monsoon depression / western disturbance / heat wave) is scientifically attractive but is explicitly Tier 3 — it requires regime labels we do not have time to construct reliably in 3 days.

## 3. Error Metrics Per Variable

**[RECOMMENDATION]**

| Variable | Error metric | Why |
|---|---|---|
| Rainfall | **Normalized/anomaly-based error**: `E = |F − O| `, evaluated relative to the local climatological rainfall variability for that day-of-year/location (e.g., error expressed in units of the local historical standard deviation, or as an exceedance of a percentile-based threshold) rather than raw percentage error | Raw percentage error is pathological when `O ≈ 0` (common on dry days) — dividing by near-zero truth blows up; a climatology-relative or percentile-based error avoids this entirely and is standard practice in precipitation verification |
| Temperature | Absolute error (°C) or bias-corrected anomaly error | Roughly Gaussian, well-behaved; raw MAE is meaningful |
| Wind | Absolute/vector error on wind speed (and optionally direction error separately) | Direction error is circular and needs separate handling; speed error is a simple magnitude difference |
| Humidity / Pressure | Absolute error in native units | Both are well-behaved, bounded variables |

**[RECOMMENDATION]** For the MVP (rainfall only), we specifically avoid MAPE/percentage error and instead use a **percentile-based / anomaly-normalized error**, computing, per grid cell and season, the empirical distribution of `|F − O|` and expressing each new error as its percentile rank within that stratified historical distribution. This directly and cleanly feeds the bust-label definition below.

## 4. Bust Label Construction

**[RECOMMENDATION]** Methodology:
1. For each stratum `(variable, lead_time_bucket, region/grid-cell-group, season)`, collect the historical distribution of `E`.
2. Define the **bust threshold** as the **85th–90th percentile** of that stratum's historical error distribution (exact percentile chosen empirically per variable during Task 06, based on resulting class balance — see §7 imbalance handling; not fixed a priori for the write-up).
3. Label `Y = 1` for any forecast whose realized error exceeded that stratum's threshold.
4. Document the resulting bust rate per stratum in the final materials (this table is itself a useful verification artifact, independent of the ML model).

This directly implements the recommended default from the problem statement ("historical errors → condition by variable/lead time/location/season → estimate distribution → define unusually large error → create bust label") and is the scientifically standard approach in forecast verification (extreme/high-percentile exceedance relative to a conditioned historical baseline), rather than an arbitrary constant like "error > 20 mm everywhere."

## 5. Features

**Core (MVP, all computable from pre-issue-time information):**
- Forecast value itself, and forecast anomaly (forecast − local day-of-year climatology).
- Lead time (Day 1/3/5/7/10, numeric).
- Region/grid-cell identifier (or its lat/lon, plus a coarse region label).
- Season / month / day-of-year (cyclically encoded).
- **Recent forecast revision**: difference between the current run's forecast for this valid time and an earlier run's forecast for the same valid time (available from Single-Runs archive — this is a genuinely predictive "forecast is unstable" signal).
- **Persistence**: how much today's forecast pattern resembles yesterday's actual conditions (a simple, well-established predictability proxy).
- **Local spatial gradient / neighboring-grid disagreement**: difference between this cell's forecast and its immediate neighbors' — high spatial gradient often correlates with higher bust risk (frontal/convective boundaries).
- **Local temporal volatility**: rolling standard deviation of recent forecast values for this cell.
- **Lead-time-dependent historical bias**: mean historical error for this exact stratum (a "known systematic bias" feature, distinct from the label itself — computed on strictly prior data only, per fold, to avoid leakage).
- Basic pressure tendency / wind change if those variables are pulled alongside rainfall.

**[RECOMMENDATION]** Ensemble spread (from TIGGE, if the Tier-2 stretch is reached) is the single most valuable *additional* feature to add if time allows, since ensemble disagreement is the textbook predictor of forecast uncertainty.

**Advanced/Tier 3 (not built now)**: explicit regime indicators (active/break monsoon, monsoon depression, cyclone, western disturbance flags), extreme-event indicators, full spatio-temporal graph features.

## 6. Baseline Models

**[RECOMMENDATION]** In increasing sophistication, all required, all compared head-to-head:
1. **Climatological/persistence baseline**: predict the stratum's *historical bust rate* itself as the probability (i.e., "how often has this exact lead-time/region/season combination busted historically" — a non-ML lookup table). This is the true "can the AI beat a lookup table" bar.
2. **Logistic regression** on the feature set above — a simple, interpretable linear baseline.
3. **Gradient-boosted trees (LightGBM or XGBoost)** — primary model, chosen for: strong tabular performance, native handling of nonlinearity/interactions between lead time/season/region, fast CPU training (no GPU needed — respects the compute constraint), and mature SHAP support for explainability.

**[OPTION, rejected for MVP]**: Neural networks / deep tabular models — rejected because they need more data and tuning time than we have, and do not outperform gradient boosting on small-to-medium tabular verification data; would also complicate the credit-efficient agent workflow for no demonstrated benefit.

## 7. Class Imbalance

**[ASSUMPTION]** With an 85th–90th percentile threshold, the positive (bust) class will be roughly 10–15% of rows by construction — moderate, not extreme, imbalance. **[RECOMMENDATION]** Handle via: class-weighting in the loss (LightGBM's `scale_pos_weight` / `is_unbalance`), reporting PR-AUC (more informative than ROC-AUC under imbalance) as a primary metric, and avoiding naive oversampling/SMOTE on time-ordered weather data (which risks synthesizing implausible or leaking synthetic feature combinations) — consistent with the "no synthetic data" constraint.

## 8. Leakage Prevention — Time-Awareness

**[RECOMMENDATION, mandatory]**:
- **Temporal holdout, not random split.** Train on the earliest ~70% of issue dates, validate on the next ~15%, test on the final ~15% chronologically. Never shuffle issue dates across the split.
- Any feature computed as "historical stratum statistic" (e.g., historical bias, historical bust rate) must be computed **only from data strictly before the current row's issue date**, recomputed per fold — never from the full dataset including future rows.
- **No spatial leakage check**: verify that nearby grid cells in train vs. test are not so tightly correlated that the model is trivially memorizing a location rather than learning general bust drivers; if the sub-region is small, consider a spatial holdout of a few cells in addition to the temporal one, as a robustness check (not the primary split).
- Prefer a **rolling-origin validation** (walk-forward: train up to month M, validate on M+1, roll forward) if time allows, as a secondary robustness check beyond the single temporal holdout — described as a stretch validation step, not required for MVP acceptance.

## 9. Evaluation (ML + Forecasting-specific)

**Required ML metrics**: ROC-AUC, PR-AUC, precision, recall, F1 (at a chosen operating threshold, justified), confusion matrix, Brier score, reliability/calibration diagram (predicted probability bucket vs. observed bust frequency).

**Required forecasting-specific evaluation**:
- Predicted bust probability vs. actual realized error (scatter/binned plot) — does higher predicted probability really correspond to bigger misses?
- Confidence vs. actual forecast quality, stratified by lead time (does skill degrade the way meteorological theory predicts — gradually — and does the model correctly track that degradation?).
- Region-wise and variable-wise performance breakdown.
- **Mandatory baseline comparison**: ML model's PR-AUC/ROC-AUC/Brier score vs. the climatological lookup-table baseline's, reported side by side, on the exact same test set.
- Stretch, if time allows: top-k highest-risk-region precision (of the top-N flagged region/day/lead-time combinations, how many actually busted).

**[RECOMMENDATION]** The PPT claim "ML improved bust identification over baseline" is only written after this evaluation actually runs — the number is filled in from real Task-09 output, never estimated in advance.

## 10. Calibration

**[RECOMMENDATION]** Fit **isotonic regression** (or Platt/sigmoid scaling if the validation fold is too small for isotonic to be stable) on the *validation* fold only, applied to the raw model output, then evaluate calibration quality on the held-out *test* fold's reliability diagram — this is what allows us to say "bust probability = 69%" and have that number mean something, rather than an arbitrary score.

## 11. Explainability

- **Global**: standard SHAP summary plot across the test set, to state overall top drivers of bust risk in the PPT.
- **Local/per-prediction**: SHAP force/waterfall values for the specific region/lead-time/date shown in the demo, feeding directly into the "Why is confidence low?" dashboard panel and into the RAG explanation layer (RAG_BIBLE.md).

## 12. Advanced Modelling Roadmap (explicitly NOT built now)

Weather-regime-conditioned sub-models; ensemble-spread integration from full TIGGE multi-centre archive; conformal-prediction-based uncertainty intervals around the confidence score itself; spatio-temporal graph or transformer models over the full India grid; online recalibration/drift detection as new forecast-truth pairs accumulate; multi-NWP-model disagreement as an explicit feature once more than one forecast source is integrated.
