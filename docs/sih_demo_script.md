# Smart India Hackathon (SIH) — 2.5 Minute Winning Video Demo Script

**Project Name:** AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts  
**Problem Category:** Climate & Disaster Management / Weather Risk Intelligence  
**Target Video Duration:** **2 Minutes 30 Seconds** (Strictly within the 2–3 Minute SIH Format)

---

## 🎬 Video Overview & Timestamp Breakdown

| Timestamp | Section Name | Focus & On-Screen Visuals | Key Standout Element |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:20** | **1. Problem & Challenge** | Flood footage, satellite monsoon map, failed rainfall warnings | **Impact of unpredicted forecast busts** |
| **0:20 – 0:50** | **2. Innovation & Impact** | High-level system architecture diagram, ROC-AUC 0.9316 benchmark | **Physics-Informed ML + Calibrated XGBoost + RAG** |
| **0:50 – 2:00** | **3. Live MVP Walkthrough** | Interactive Web Dashboard ([http://127.0.0.1:5173](http://127.0.0.1:5173)) | **Grid Map ⟶ SHAP Drivers ⟶ RAG Assistant ⟶ Replay** |
| **2:00 – 2:30** | **4. Roadmap & Future** | Pan-India deployment map, IMD/NDRF integration plan | **Scale to 3.2M sq. km & National Emergency Ops** |

---

## 📜 Full Script with Voiceover & Screen Recording Directions

---

### SECTION 1: Problem Statement & Core Challenge (0:00 – 0:20 | 20 Seconds)

**🎥 Visuals:**  
*Opening shot: Flash floods over urban/coastal India, followed by an overlay showing standard 7-day IMD/GEFS weather forecasts vs actual torrential rain.*

**🎙️ Voiceover (Paced & Impactful):**  
> *"In medium-range weather forecasting, when a numerical model predicts light rain but localized torrential downpours hit—that's a **Forecast Bust**. 
> 
> Current global ensemble systems provide spread, but they fail to quantify localized predictability limits over terrain like the Western Ghats. When forecast busts strike unannounced, disaster response agencies lose precious lead time, leading to catastrophic flash floods and crop damage."*

---

### SECTION 2: Innovation & Solution Impact (0:20 – 0:50 | 30 Seconds)

**🎥 Visuals:**  
*Smooth transition to an animated architecture diagram showing GEFS + IMD High-Res Data ⟶ Feature Engine ⟶ Calibrated XGBoost ⟶ SHAP Explainability ⟶ Meteorological RAG. Highlight big bold metric text: **ROC-AUC: 0.9316 | Brier Score: 0.0513**.*

**🎙️ Voiceover (Energetic & Confident):**  
> *"To solve this, we built India’s first **Physics-Informed AI Forecast Bust Detector**. 
> 
> Instead of blindly trusting ensemble averages, our system extracts 10 spatial-temporal signals—including convective gradient disagreement, historical systematic bias, and ensemble divergence. 
> 
> Powered by an Isotonic-Calibrated XGBoost classifier trained on 35,200 grid points, our solution achieves an extraordinary **0.9316 ROC-AUC** and catches **95.7% of forecast busts** before they happen—converting raw uncertainty into calibrated, actionable risk intelligence."*

---

### SECTION 3: Live MVP & Website Walkthrough (0:50 – 2:00 | 70 Seconds)

**🎥 Visuals:**  
*Screen recording of the live dashboard running at `http://127.0.0.1:5173/`.*

#### 📍 Step A: Interactive Spatial Map (0:50 – 1:10)
**Screen Action:** Mouse hovers over the 0.25° gridded Leaflet map over Maharashtra and Western Ghats. Click on grid cell $(20.0^\circ\text{N}, 73.0^\circ\text{E})$.  
**🎙️ Voiceover:**  
> *"Here is our live dashboard. Forecasters can view the 0.25° grid over high-risk regions. When we select a cell near Mumbai, the system instantly computes the 10-day forecast reliability trajectory. While Days 1 to 3 remain confident, Day 5 jumps to a **72% High-Risk Bust Warning**."*

#### 🔍 Step B: SHAP Feature Attribution (1:10 – 1:30)
**Screen Action:** Scroll down to the "Model Feature Drivers (SHAP)" and "Key Signals" panel showing green/red arrows.  
**🎙️ Voiceover:**  
> *"Why is the model flagging a bust? Our SHAP explainability engine reveals the exact physical drivers: high spatial gradient disagreement of 14.2 mm/day combined with severe ensemble spread across GEFS members."*

#### 📖 Step C: Meteorological Knowledge RAG Assistant (1:30 – 1:45)
**Screen Action:** Click the **💬 Explain with Meteorological Context** button. The blue RAG panel expands showing physics text and citations `[1] IMD Monsoon Mission Report`, `[2] WMO Forecast Verification Guide`.  
**🎙️ Voiceover:**  
> *"For operational teams who need atmospheric context, our embedded **Meteorological RAG Assistant** retrieves grounded explanations directly from IMD and WMO literature—explaining how convective instability degrades medium-range predictability without hallucinating."*

#### 🔄 Step D: Pre-Cached Offline Historical Replay (1:45 – 2:00)
**Screen Action:** Switch date selector to **July 15, 2002 Drought Bust Case**. The historical observed vs predicted rainfall comparison chart animates.  
**🎙️ Voiceover:**  
> *"And for zero-failure operational resilience, our system includes pre-cached historical replays. Here during the historic July 2002 monsoon drought bust, our AI flagged an 84% bust probability 5 days in advance."*

---

### SECTION 4: Market Impact & Business / Deployment Roadmap (2:00 – 2:30 | 30 Seconds)

**🎥 Visuals:**  
*Graphic showing Pan-India expansion map (3.2M sq. km grid) integrated with IMD/NCMRWF weather API feeds, NDRF disaster portals, and agricultural advisory SMS alerts.*

**🎙️ Voiceover (Closing & Inspiring):**  
> *"Our vision extends beyond a prototype. Designed with sub-20 millisecond API microservices, our platform seamlessly integrates into IMD forecasting workflows, NDRF emergency control rooms, and farmer advisory apps. 
> 
> By scaling across all 36 Indian meteorological sub-divisions, we turn weather uncertainty into early disaster preparedness—saving lives, protecting infrastructure, and safeguarding agricultural yields. 
> 
> Thank you."*

---

## 🌟 Why This Script Will Make Your Presentation Stand Out at SIH

1. **Strict 2.5-Minute Pacing**: Fits the SIH evaluation guidelines perfectly (between 2 to 3 minutes, under 4 minutes).
2. **Empirical Grounding**: Mentions exact benchmark numbers (**ROC-AUC 0.9316**, **Brier Score 0.0513**, **35,200 grid rows**, **95.7% Recall**) which judges look for.
3. **Shows Real Working Technology**: Walks through live interactive map, SHAP explainability, RAG literature assistant, and offline replays.
4. **Clear Market & Social Impact**: Connects advanced AI directly to disaster management (NDRF) and agricultural protection in India.
