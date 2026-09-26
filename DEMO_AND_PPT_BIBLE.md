# DEMO_AND_PPT_BIBLE.md — Demo Story, Video, and Presentation Guide

Legend: **[FACT]** · **[ASSUMPTION]** · **[RECOMMENDATION]** · **[OPTION]**

---

## 1. 2–3 Minute Demo Story (Historical Replay Primary)

**[RECOMMENDATION]** Structure the video as a single continuous narrative, not a feature tour:

1. **(0:00–0:20) The problem, stated plainly.** "Medium-range forecasts are usually good — but sometimes they bust badly, and today there's no systematic way to know *in advance* which forecast, for which place and which day, is likely to be one of those busts." Show a simple before/after: official forecast vs. what actually happened, for a real historical date where the forecast missed.
2. **(0:20–0:40) Introduce the reframe.** "So instead of just asking what the forecast says, we built a system that asks: how much should you trust it?" Cut to the Command Center map.
3. **(0:40–1:20) Historical replay walkthrough.** Pick a real date from the cached replay set (Task 16). Show: the map at that issue date, colored by confidence for Day 1 through Day 7/10; click into the region that the system flagged low-confidence; show the Why-panel (rule-based drivers + SHAP + RAG explanation with citations).
4. **(1:20–1:45) Reveal the outcome.** Advance to the real valid date; show the actual ERA5/observation outcome side by side with the forecast; confirm (honestly) whether the flagged low-confidence forecast did or didn't bust.
5. **(1:45–2:15) Show the evidence it's not a wrapper.** Cut briefly to the Model Performance panel: ROC-AUC/PR-AUC/Brier score, reliability diagram, and the explicit baseline-comparison number from Task 09/MODEL_METHODOLOGY.md §9. Say the actual number, whatever it is.
6. **(2:15–2:45) Zoom out to positioning and users.** One sentence on primary user (disaster-management/operational forecasters), one sentence on the "not a replacement for NWP" framing, one sentence on the roadmap (regime-awareness, full India, ensemble spread).
7. **(2:45–3:00) Close.** Restate the core promise line.

**[RECOMMENDATION]** Live-mode is optional and only shown, if at all, *after* the historical replay has already made the case — never as the sole demo path, since live APIs can fail exactly when judges are watching.

## 2. Recommended Screenshots (capture as each view is finished, per BUILD_MAP_BIBLE.md Task 13-17, not retroactively)

1. Command Center map, Day 1 selected, whole sub-region visible.
2. Command Center map, Day 7 or Day 10 selected, showing visibly different (typically lower) confidence — this single side-by-side pair is the clearest illustration of "lead-time-dependent reliability" for the PPT.
3. Region Detail lead-time chart for the flagged region.
4. Why-panel: rule-based summary + SHAP bar chart + RAG cited explanation, all in one frame if the layout allows.
5. Historical Replay: predicted (pre-date) vs. actual (post-date) side by side.
6. Model Performance panel: reliability diagram + baseline-vs-ML comparison table.
7. Architecture diagram (from BUILD_MAP_BIBLE.md §1, redrawn cleanly for the PPT).

## 3. Key Claims We Can Safely Make (fill in the blanks only after Task 09/19 actually run)

- "Our model achieves an ROC-AUC of **[X]** and PR-AUC of **[Y]** on a strict, time-ordered held-out test set, spanning [region] and lead times Day 1–10 for rainfall."
- "This beats a climatological baseline by **[Z]** on [metric], on the identical test set."
- "The model's calibrated probabilities are meaningfully interpretable: in our reliability diagram, predicted-vs-observed bust rate tracks the diagonal within **[tolerance]**."
- "Every bust-probability number shown is produced by a model trained on real historical forecast-vs-ERA5-truth pairs — no synthetic data anywhere in the pipeline."
- "The explanation layer is grounded and cited — every meteorological claim traces to a real source document, and the RAG layer never generates a probability of its own."

**[RECOMMENDATION]** Do not write any of the bracketed numbers into the actual slides until they exist from a real run — leave them visibly blank in draft slides as a forcing function against accidental fabrication.

## 4. Architecture Diagram for the PPT

Reuse BUILD_MAP_BIBLE.md §1's pipeline diagram, simplified to ~8 boxes for a slide: Data → Alignment/Features → Bust Label → Model+Calibration → Explainability → RAG → API → Dashboard. Keep the "not a replacement for NWP" framing visible near the diagram.

## 5. Problem → Solution → Results Narrative (slide-by-slide skeleton)

1. Title + one-line promise ("Don't just ask what the forecast says. Ask how much you should trust it.")
2. The problem (forecast busts, why they matter operationally, PS 26079 framing).
3. Primary/secondary users and why each benefits.
4. The scientific reframe (error → conditioned distribution → bust label → calibrated probability) — 1 clean diagram, not a wall of text.
5. Data strategy in one slide (Open-Meteo + ERA5, real forecast-vs-truth pairs, India sub-region, no synthetic data — say this explicitly).
6. Model + evaluation results (the filled-in numbers from §3 above, plus the reliability diagram image).
7. Explainability — three-layer example on one real case (screenshot 4).
8. Historical replay demo screenshot (screenshots 1/2/5).
9. Architecture diagram.
10. MVP vs. roadmap (Tier 1 done, Tier 2/3 as clearly-labeled future work — do not blur this line).
11. Honest limitations / what we do NOT claim (§6 below) — a credibility-building slide, not a weakness.
12. Close: promise line + call to action (e.g., what integration would look like operationally).

## 6. What NOT to Claim

- Do **not** claim operational readiness, official-warning-authority, or guaranteed accuracy for any specific future date.
- Do **not** claim full-India, all-variable, all-regime coverage — the MVP is explicitly a bounded sub-region, rainfall-only, Day 1/3/5/7/10 subset.
- Do **not** present RAG-generated text as if it were an independent verification of the model's number — it explains the model's own number.
- Do **not** claim the system replaces expert IMD forecasters or NWP models — it is explicitly a decision-support layer on top of them.
- Do **not** state any performance number that wasn't actually produced by Task 09/19's real evaluation run.

## 7. Demo Fallback Plan

If the live dashboard/API is unreachable during judging (network issue, free-tier host down): the pre-recorded video is the primary fallback, and the cached historical-replay JSON (Task 16) can be shown running fully locally (`start.sh`, no internet required) as a live backup-of-the-backup. Never attempt to debug a live deployment issue in front of judges — switch to the local/video path immediately per the stop-condition discipline established in PRD_BIBLE.md.
