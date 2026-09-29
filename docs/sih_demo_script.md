# 🏆 Smart India Hackathon (SIH) — Demo Video Script (2:30 min)

**Project Title:** AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts  
**Target Duration:** 2 Minutes 30 Seconds (Strictly within the 2–3 min SIH guideline)  
**Tone:** Confident, technical, high-energy, and impact-driven.

---

## ⏱️ Scene-by-Scene Breakdown

| Timeframe | Section | Core Focus |
|---|---|---|
| **0:00 – 0:20** (20s) | **The Core Problem** | The hidden danger of medium-range forecast "busts" during the Indian Monsoon. |
| **0:20 – 0:50** (30s) | **Our Solution & Innovation** | AI-driven meta-predictability engine combining dynamical physics with calibrated ML & Synoptic RAG. |
| **0:50 – 2:05** (75s) | **Live Prototype Walkthrough** | Map view, Lead Day toggle, 10-Day Trajectory, SHAP drivers, Synoptic RAG, Historical Replay & Metrics. |
| **2:05 – 2:30** (25s) | **Impact & Roadmap** | IMD/NDMA operational deployment, saving lives, agricultural protection, and scalability. |

---

## 🎬 Full Script with Screen Directions

### 📍 PART 1: The Core Problem (0:00 – 0:20)
* **Visual on Screen:** Title slide transitioning into news clips/graphics of sudden flash floods, unpredicted cloudbursts, and crop loss in Maharashtra / Western Ghats.
* **Voiceover:**
> *"Every monsoon, numerical weather prediction models like GEFS and ECMWF guide disaster management across India. But in the critical Day 3 to Day 10 medium range, these models experience catastrophic forecast 'busts'—days where extreme rainfall is either missed completely or falsely alarmed due to rapid convective amplification.*  
> *When a forecast busts, dams overflow without warning, farmers lose entire harvests, and disaster relief teams are caught unprepared. Today, forecasters have no automated tool that tells them: **'Is this forecast actually trustworthy?'**"*

---

### 📍 PART 2: Our Innovation & Solution (0:20 – 0:50)
* **Visual on Screen:** Architecture slide / System Diagram highlighting the three-tier stack: NOAA GEFSv12 ensemble reforecasts + IMD 0.25° gridded ground truth $\rightarrow$ Calibrated XGBoost with Isotonic Regression $\rightarrow$ FAISS-powered Synoptic RAG.
* **Voiceover:**
> *"Introducing the **AI-Based Forecast Bust Detector**—an operational meta-reliability engine that audits numerical weather predictions before disaster strikes.*  
> *Instead of blindly accepting raw forecasts, our system analyzes multi-physics signals—including ensemble spread, orographic moisture flux, vorticity, and historical regional biases. Using chronologically validated, isotonic-calibrated Machine Learning paired with a domain-specific Synoptic RAG engine, we output calibrated bust probabilities and plain-language meteorological explanations in real time."*

---

### 📍 PART 3: Live Prototype Walkthrough (0:50 – 2:05)

#### 🔹 1. Regional Map & Lead-Time Degradation (0:50 – 1:15)
* **Visual on Screen:** Screen recording of the Live Dashboard (`http://127.0.0.1:5173/`).
* **Action:** Toggle from **Day 1 (D1)** to **Day 5 (D5)** to **Day 7 (D7)** on the map. Point out the regional summary bar updating dynamically.
* **Voiceover:**
> *"Let's look at the live platform. Here in our dark-mode operational console over Maharashtra and the Western Ghats, each grid cell is colored by calibrated bust risk: green for high confidence, amber for moderate risk, and red for high bust probability.*  
> *Notice how at Day 1, short-range confidence is high. But as we advance to Lead Day 7, the system immediately flags elevated bust risk along the orographic barrier of the Western Ghats where convective uncertainty escalates."*

#### 🔹 2. 10-Day Trajectory, SHAP Explainability & Synoptic RAG (1:15 – 1:45)
* **Visual on Screen:** Click on a high-risk red/amber cell along the coast.
* **Action:** 
  1. Show the **10-Day Bust Probability Trajectory histogram** in the right panel.
  2. Show the **Feature Drivers (SHAP)** breakdown.
  3. Click **"💬 Explain with Meteorological Context"** and show the instant RAG answer with document citations.
* **Voiceover:**
> *"Clicking any grid point reveals its complete 10-Day Trajectory, showing exactly at what lead day forecast skill degrades. Below, Level-1 SHAP explainability isolates the physical drivers—such as wide ensemble spread and large negative anomalies.*  
> *For operational meteorologists, clicking 'Explain with Meteorological Context' invokes our FAISS-powered RAG layer, synthesizing authoritative IMD and ECMWF domain literature to explain the synoptic physics behind the bust risk with zero hallucinations."*

#### 🔹 3. Historical Replay & Verification Benchmarks (1:45 – 2:05)
* **Visual on Screen:** Switch to the **Replay** tab (click "2003-07-01 Peak Monsoon Active Surge"), then switch to the **Metrics** tab.
* **Voiceover:**
> *"Under the **Replay Tab**, we can audit real historical events, such as the 2003 Peak Monsoon Surge, proving our model flagged the upcoming bust using strictly pre-event forecast data verified against IMD ground truth.*  
> *And under **Metrics**, our chronologically held-out test evaluation proves superior performance: achieving a **0.93 ROC-AUC** and **0.051 Brier score**, dramatically outperforming linear baselines."*

---

### 📍 PART 4: Impact & Road Ahead (2:05 – 2:30)
* **Visual on Screen:** Roadmap graphic showing IMD / NDMA integration, Early Warning SMS feeds, and pan-India expansion.
* **Voiceover:**
> *"This system is 100% modular, open-source ready, and designed for direct integration into IMD and State Disaster Management Authorities.*  
> *By turning raw weather predictions into calibrated, explainable confidence intelligence, we empower authorities to pre-position NDRF teams, optimize reservoir discharges, and protect millions of agricultural livelihoods.  
> **Forecast Bust Detector: Bringing transparency, physics, and trust to weather forecasting.** Thank you."*

---

## 🎙️ Recording Checklist & Tips
1. **Screen Resolution:** Record in 1080p (1920x1080) in full-screen dark mode.
2. **Pacing:** Speak at ~130–140 words per minute; keep mouse movements smooth and intentional.
3. **Audio Quality:** Use a decent external microphone and remove background noise.
4. **Highlights:** Use cursor circles or zoom-ins when pointing out the 10-day histogram and RAG citations.
