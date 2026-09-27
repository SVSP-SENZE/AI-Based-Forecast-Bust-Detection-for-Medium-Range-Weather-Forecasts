# Presentation Pitch Deck & 3-Minute Demo Script

**Project Title:** AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts  
**Target Audience:** Weather Forecasting Agencies (IMD/NCMRWF), Disaster Management Authorities, Academic Reviewers  
**Measured Benchmarks:** ROC-AUC: **0.9316** | Brier Score: **0.0513** | Dataset: **35,200 grid rows** (44 issue dates, 10 lead days)

---

## Part 1: Slide-by-Slide Presentation Pitch Deck

```
+-----------------------------------------------------------------------------------+
| SLIDE 1: Title & Problem Statement                                                |
| "Predicting When Weather Models Fail: AI Bust Detection for Indian Monsoon"       |
+-----------------------------------------------------------------------------------+
| • Medium-range precipitation forecasts (Days 3-10) over India frequently experience|
|   catastrophic "forecast busts" where predicted rainfall differs drastically from  |
|   ground truth IMD observations.                                                  |
| • Traditional NWP models (GEFS) report ensemble spread, but lack calibrated probabilistic|
|   risk quantification for extreme events over complex terrain (Western Ghats).   |
+-----------------------------------------------------------------------------------+
```

```
+-----------------------------------------------------------------------------------+
| SLIDE 2: Solution Architecture & Hybrid ML Framework                              |
| "Physics-Informed Ensemble Post-Processing + Explainable AI + RAG"                |
+-----------------------------------------------------------------------------------+
| • GEFS Ensemble Reforecasts + IMD Daily High-Res Gridded Rainfall (0.25° grid)     |
| • 10 Engineered Features: Ensemble Std, Spatial Disagreement, Historical Model    |
|   Bias, Climatology Anomaly Magnitude, and Lead-Time Degradation Factor.          |
| • Calibrated XGBoost Classifier + Isotonic Regression for exact confidence bands. |
| • Dense RAG System (FAISS + MiniLM-L6) providing physics-grounded explanations.   |
+-----------------------------------------------------------------------------------+
```

```
+-----------------------------------------------------------------------------------+
| SLIDE 3: Key Model Performance & Metric Validation                                |
| "State-of-the-Art Bust Detection Skill"                                           |
+-----------------------------------------------------------------------------------+
| • ROC-AUC: 0.9316 (XGBoost) vs 0.8597 (Logistic Baseline) vs 0.4358 (Climatology) |
| • Brier Score: 0.0513 (Calibrated) — Superior probability reliability.             |
| • Recall: 95.66% — Catches 95.7% of operational forecast busts before they happen.|
| • Expected Calibration Error (ECE): 0.0241 — Highly reliable confidence bands.   |
+-----------------------------------------------------------------------------------+
```

```
+-----------------------------------------------------------------------------------+
| SLIDE 4: Feature Importance & Meteorological Explainability                       |
| "What Drives Forecast Bust Risk?"                                                |
+-----------------------------------------------------------------------------------+
| • Top Predictor #1: Ensemble Spread (`ensemble_std`, SHAP = 0.285)                |
| • Top Predictor #2: Spatial Disagreement (`spatial_gradient_std`, SHAP = 0.192)   |
| • Top Predictor #3: Historical Model Bias (`hist_bias_abs`, SHAP = 0.145)         |
| • Rule-based signals flag high-risk convective instability vs synoptic certainty. |
+-----------------------------------------------------------------------------------+
```

```
+-----------------------------------------------------------------------------------+
| SLIDE 5: Operational Deployment & Resilience                                      |
| "Sub-20ms API Response + Offline Pre-Cached Historical Replay"                   |
+-----------------------------------------------------------------------------------+
| • FastAPI REST endpoints (/forecast-reliability, /region, /explanation, /replay)  |
| • Sub-20ms inference latency per query cell.                                      |
| • 100% offline fallback with pre-cached historical replay JSON cases (July 2002   |
|   monsoon drought bust case, August 2001 high-confidence verified case).           |
+-----------------------------------------------------------------------------------+
```

---

## Part 2: Step-by-Step 3-Minute Live Demo Script

### Demo Objective
Demonstrate how an operational forecaster at IMD uses the Forecast Bust Detector dashboard to evaluate medium-range heavy rainfall forecasts, inspect driver attributions, query meteorological domain knowledge, and review historical replay cases.

---

### Minute 0:00 – 0:45: Introduction & Regional Grid Overview
> **Speaker Script:**  
> "Good morning everyone. Medium-range rainfall forecasting over the Indian monsoon region is notoriously challenging. When severe forecast busts happen, disaster response agencies are caught off guard. Today, I'm presenting our AI-Based Forecast Bust Detection System.
> 
> Here on the main grid view, we are looking at the target region—Maharashtra and the Western Ghats at 0.25° resolution for an issue date during the active monsoon season. Each cell displays the calibrated bust probability for lead day 5. Notice how the coastal W. Ghats region highlights in yellow and red, indicating a 68% probability of a forecast bust due to complex terrain convective divergence."

---

### Minute 0:45 – 1:30: Single-Location Reliability & SHAP Explanations
> **Speaker Script:**  
> "Let's click on grid coordinate $(20.0^\circ\text{N}, 73.0^\circ\text{E})$.
> 
> The reliability panel shows the 10-day forecast trajectory. For Day 1–3, the forecast is marked with High Confidence (Bust Probability $< 15\%$). However, at Day 5 and Day 7, the probability jumps to 72%, flagging a High-Risk Bust Warning.
> 
> Why is the model flagging this? Let's check the **Top Drivers** section powered by SHAP values:
> 1. High Ensemble Spread ($18.4\text{ mm/day}$) across GEFS members.
> 2. High Spatial Disagreement ($14.2\text{ mm/day}$) between neighboring cells.
> 3. Historical Systematic Bias for Day 5 heavy rain over this terrain."

---

### Minute 1:30 – 2:15: Meteorological RAG Knowledge Assistant
> **Speaker Script:**  
> "To assist operational forecasters who need physics-based context, we integrated a Meteorological Knowledge RAG System grounded in IMD, WMO, and ECMWF literature.
> 
> Let's type in the query box: *'Why does high spatial disagreement indicate cloud-resolving predictability limits?'*
> 
> In less than 100 milliseconds, the system returns a grounded answer citing IMD Monsoon Mission reports and WMO verification standards:
> *'Convective precipitation during monsoon active phases features small-scale spatial variability. High spatial gradient disagreement among ensemble members signals localized mesoscale convective system (MCS) uncertainty, leading to sudden medium-range forecast skill drop-off.'*"

---

### Minute 2:15 – 3:00: Offline Historical Replay & Conclusion
> **Speaker Script:**  
> "Finally, for offline reliability and post-event audit, our system features pre-cached historical replay cases.
> 
> Let's select the **July 2002 Drought Bust Case**. The dashboard loads the historical ensemble predictions alongside ground-truth IMD observed rainfall. Our model correctly flagged a **84% Bust Risk** 5 days before the event, giving forecasters actionable advance warning.
> 
> To summarize: with a verified **ROC-AUC of 0.9316**, **Brier Score of 0.0513**, and sub-20ms response time, our system turns raw ensemble spread into actionable, physics-grounded forecast risk intelligence. Thank you!"
