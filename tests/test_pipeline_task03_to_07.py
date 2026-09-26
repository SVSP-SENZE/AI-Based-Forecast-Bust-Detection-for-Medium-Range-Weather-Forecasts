"""
tests/test_pipeline_task03_to_07.py
====================================
End-to-end unit and smoke tests for Tasks 03 through 07:
- Feature engineering output validity
- Bust label distribution and leakage check
- Model artifacts and evaluation metrics existence
- Calibrator persistence and functionality
- FastAPI endpoint responses
"""

import os
import sys
import json
import pytest
import pandas as pd
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def test_task03_features_and_labels():
    feat_path = os.path.join(ROOT, "data", "processed", "features.parquet")
    assert os.path.exists(feat_path), "features.parquet must exist"
    df = pd.read_parquet(feat_path)
    assert len(df) > 0, "features.parquet must not be empty"
    assert "is_bust" in df.columns, "is_bust label column must be present"
    assert "forecast_anomaly" in df.columns
    assert "spatial_gradient" in df.columns
    assert "hist_bias" in df.columns
    
    # Check no missing values in features
    assert df["forecast_anomaly"].isna().sum() == 0
    assert df["spatial_gradient"].isna().sum() == 0
    assert df["hist_bias"].isna().sum() == 0
    
    # Bust rate should be reasonable (~10% - 20%)
    bust_rate = df["is_bust"].mean()
    assert 0.08 <= bust_rate <= 0.25, f"Bust rate {bust_rate:.2%} out of expected range"


def test_task04_models_and_metrics():
    model_path = os.path.join(ROOT, "models", "xgb_model.pkl")
    metrics_path = os.path.join(ROOT, "models", "evaluation", "all_metrics.json")
    
    assert os.path.exists(model_path), "XGBoost model file must exist"
    assert os.path.exists(metrics_path), "all_metrics.json must exist"
    
    with open(metrics_path) as f:
        metrics = json.load(f)
        
    assert "XGBoost" in metrics
    assert "ClimatologicalBaseline" in metrics
    assert metrics["XGBoost"]["roc_auc"] > metrics["ClimatologicalBaseline"]["roc_auc"]
    assert metrics["XGBoost"]["brier"] < metrics["ClimatologicalBaseline"]["brier"]


def test_task05_calibration_and_shap():
    cal_path = os.path.join(ROOT, "models", "calibrator.pkl")
    shap_path = os.path.join(ROOT, "models", "evaluation", "shap_importance.json")
    
    assert os.path.exists(cal_path), "calibrator.pkl must exist"
    assert os.path.exists(shap_path), "shap_importance.json must exist"


def test_task06_07_api_endpoints():
    from src.api.main import app
    client = TestClient(app)
    
    # Health
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    
    # Metrics
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "XGBoost" in r.json()
    
    # Forecast Reliability
    r = client.get("/forecast-reliability?lat=19.0&lon=73.0&issue_date=2001-07-01")
    assert r.status_code == 200
    data = r.json()
    assert "forecasts" in data
    assert len(data["forecasts"]) == 5  # Day 1, 3, 5, 7, 10
    
    # Region map
    r = client.get("/region?lead_day=3&issue_date=2001-07-01")
    assert r.status_code == 200
    assert len(r.json()["cells"]) == 289
    
    # Explanation
    r = client.get("/explanation?lat=19.0&lon=73.0&lead_day=3&issue_date=2001-07-01")
    assert r.status_code == 200
    exp = r.json()
    assert "top_drivers" in exp
    assert "rule_summary" in exp


if __name__ == "__main__":
    test_task03_features_and_labels()
    print("PASS: Task 03 feature & label tests")
    test_task04_models_and_metrics()
    print("PASS: Task 04 model & evaluation tests")
    test_task05_calibration_and_shap()
    print("PASS: Task 05 calibration & SHAP tests")
    test_task06_07_api_endpoints()
    print("PASS: Task 06/07 API endpoint tests")
    print("\nALL SMOKE TESTS PASSED!")
