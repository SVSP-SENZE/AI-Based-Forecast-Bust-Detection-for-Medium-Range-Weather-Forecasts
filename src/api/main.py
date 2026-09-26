"""
src/api/main.py
================
Task 07 — FastAPI Application

Endpoints:
  GET  /health
  GET  /forecast-reliability   ?lat=&lon=&issue_date=
  GET  /region                 ?lead_day=&issue_date=
  GET  /explanation            ?lat=&lon=&lead_day=&issue_date=
  GET  /metrics
  GET  /replay                 ?issue_date=
  POST /rag-query              body: {"question": str, "context": dict}

Run:
  uvicorn src.api.main:app --reload --port 8000
"""

import os
import sys
import json
import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(
    title="Forecast Bust Detector API",
    description="AI-based forecast bust detection for medium-range rainfall forecasts over India.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lazy-load heavy components ─────────────────────────────────────
_predictor = None
_metrics   = None
_rag       = None

def get_predictor():
    global _predictor
    if _predictor is None:
        from src.models.inference import BustPredictor
        _predictor = BustPredictor()
    return _predictor

def get_metrics():
    global _metrics
    if _metrics is None:
        path = os.path.join(ROOT_DIR, "models", "evaluation", "all_metrics.json")
        if os.path.exists(path):
            with open(path) as f:
                _metrics = json.load(f)
        else:
            _metrics = {}
    return _metrics

def get_rag():
    global _rag
    if _rag is None:
        try:
            from src.rag.retrieve import RagRetriever
            _rag = RagRetriever()
        except Exception:
            _rag = None
    return _rag

# Grid for the region endpoint
TARGET_LATS = [round(18.0 + i * 0.25, 2) for i in range(17)]  # 18.0 to 22.0
TARGET_LONS = [round(72.0 + i * 0.25, 2) for i in range(17)]  # 72.0 to 76.0


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "Forecast Bust Detector"}


@app.get("/forecast-reliability")
def forecast_reliability(
    lat: float = Query(..., description="Latitude (18–22)"),
    lon: float = Query(..., description="Longitude (72–76)"),
    issue_date: str = Query(..., description="Issue date YYYY-MM-DD"),
):
    """Return Day 1–10 bust probability + confidence for one location."""
    try:
        issue_dt = datetime.date.fromisoformat(issue_date)
    except ValueError:
        raise HTTPException(400, "issue_date must be YYYY-MM-DD")

    p = get_predictor()
    results = p.predict(issue_dt, lat, lon)
    return {
        "location": {"lat": lat, "lon": lon},
        "issue_date": issue_date,
        "forecasts": results,
    }


@app.get("/region")
def region_confidence(
    lead_day: int = Query(..., description="Lead day (1,3,5,7,10)"),
    issue_date: str = Query(..., description="Issue date YYYY-MM-DD"),
):
    """Return per-cell bust probability over the whole grid for one lead day."""
    if lead_day not in [1, 3, 5, 7, 10]:
        raise HTTPException(400, "lead_day must be one of 1,3,5,7,10")
    try:
        issue_dt = datetime.date.fromisoformat(issue_date)
    except ValueError:
        raise HTTPException(400, "issue_date must be YYYY-MM-DD")

    p = get_predictor()
    cells = p.batch_predict_region(issue_dt, lead_day, TARGET_LATS, TARGET_LONS)
    # Return compact format for the map
    return {
        "lead_day": lead_day,
        "issue_date": issue_date,
        "cells": [
            {
                "lat": c["lat"], "lon": c["lon"],
                "bust_probability": c["bust_probability"],
                "confidence_band": c["confidence_band"],
            }
            for c in cells
        ],
    }


@app.get("/explanation")
def explanation(
    lat: float = Query(...),
    lon: float = Query(...),
    lead_day: int = Query(...),
    issue_date: str = Query(...),
):
    """Return SHAP top drivers + rule-based explanation for one prediction."""
    try:
        issue_dt = datetime.date.fromisoformat(issue_date)
    except ValueError:
        raise HTTPException(400, "issue_date must be YYYY-MM-DD")

    p = get_predictor()
    results = p.predict(issue_dt, lat, lon, lead_days=[lead_day])
    r = results[0]
    return {
        "location": {"lat": lat, "lon": lon},
        "issue_date": issue_date,
        "lead_day": lead_day,
        "bust_probability": r["bust_probability"],
        "confidence_band": r["confidence_band"],
        "top_drivers": r["top_drivers"],
        "rule_summary": r["rule_summary"],
    }


@app.get("/metrics")
def metrics():
    """Return model performance summary."""
    m = get_metrics()
    if not m:
        raise HTTPException(503, "Metrics not yet computed. Run evaluate.py first.")
    return m


class RagQuery(BaseModel):
    question: str
    context: Optional[dict] = None


@app.post("/rag-query")
def rag_query(body: RagQuery):
    """Answer a meteorological question using the RAG corpus."""
    rag = get_rag()
    if rag is None:
        return {
            "answer": "RAG system not yet initialized. Run src/rag/ingest.py first.",
            "sources": [],
        }
    try:
        result = rag.answer(body.question, context=body.context)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/replay")
def replay(issue_date: str = Query(..., description="Historical issue date YYYY-MM-DD")):
    """Return pre-cached historical replay for a past date."""
    replay_dir = os.path.join(ROOT_DIR, "models", "evaluation", "replays")
    replay_file = os.path.join(replay_dir, f"replay_{issue_date}.json")

    if os.path.exists(replay_file):
        with open(replay_file) as f:
            return json.load(f)

    # Generate on-the-fly if model is available
    try:
        issue_dt = datetime.date.fromisoformat(issue_date)
        p = get_predictor()
        predictions = p.predict(issue_dt, lat=20.0, lon=73.0)
        return {
            "issue_date": issue_date,
            "note": "On-the-fly prediction (no pre-cached replay for this date)",
            "predictions": predictions,
            "actual_rainfall": None,
        }
    except Exception as e:
        raise HTTPException(400, str(e))
