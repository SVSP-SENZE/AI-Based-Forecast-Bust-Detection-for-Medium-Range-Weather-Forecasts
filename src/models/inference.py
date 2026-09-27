"""
src/models/inference.py
========================
Task 06 — Inference Engine

Loads trained model + calibrator + encoders at startup.
Provides predict() to get bust probabilities + explanations
for a given (issue_date, lat, lon, lead_days).

Also provides batch_predict_region() for the /region endpoint.
"""

import os
import sys
import json
import pickle
import datetime
import numpy as np
import pandas as pd

# Ensure libomp path is set for XGBoost on macOS
libomp_path = "/opt/homebrew/opt/libomp/lib"
if os.path.exists(libomp_path):
    existing = os.environ.get("DYLD_LIBRARY_PATH", "")
    if libomp_path not in existing:
        os.environ["DYLD_LIBRARY_PATH"] = f"{libomp_path}:{existing}" if existing else libomp_path

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
FEAT_PATH  = os.path.join(ROOT_DIR, "data", "processed", "features.parquet")

sys.path.insert(0, ROOT_DIR)
from src.explain.rules import get_rule_summary, confidence_band
from src.explain.shap_explain import get_top_drivers


def _season(month: int) -> str:
    if month in (6, 7, 8, 9):   return "monsoon"
    if month in (10, 11):        return "post_monsoon"
    if month in (12, 1, 2):      return "winter"
    return "pre_monsoon"


class BustPredictor:
    """Singleton-style inference engine. Load once, call many times."""

    def __init__(self):
        self._load()

    def _load(self):
        model_path = os.path.join(MODELS_DIR, "xgb_model.pkl")
        cal_path   = os.path.join(MODELS_DIR, "calibrator.pkl")
        feat_path  = os.path.join(MODELS_DIR, "feature_cols.json")
        enc_path   = os.path.join(MODELS_DIR, "season_encoder.pkl")
        bias_path  = os.path.join(MODELS_DIR, "hist_bias_lookup.json")

        with open(model_path, "rb") as f:
            self.model = pickle.load(f)
        with open(cal_path, "rb") as f:
            self.calibrator = pickle.load(f)
        with open(feat_path) as f:
            self.feature_cols = json.load(f)["features"]
        with open(enc_path, "rb") as f:
            self.le_season = pickle.load(f)

        # Historical bias lookup (lead_day, season) -> mean error
        if os.path.exists(bias_path):
            with open(bias_path) as f:
                raw = json.load(f)
            self.hist_bias = {tuple(k.split("|")): v for k, v in raw.items()}
        else:
            self.hist_bias = {}

        # Load feature dataset for climatology
        if os.path.exists(FEAT_PATH):
            df = pd.read_parquet(FEAT_PATH)
            df["issue_time"] = pd.to_datetime(df["issue_time"])
            df["month"] = df["issue_time"].dt.month
            # Climatology: mean observed_rainfall per (lat, lon, month)
            self.clim = (
                df.groupby(["lat", "lon", "month"])["observed_rainfall"]
                .mean()
                .to_dict()
            )
            # Global hist_bias fallback per (lead_day, season) over entire dataset
            df["season_str"] = df["issue_time"].dt.month.apply(_season)
            self.global_bias = (
                df.groupby(["lead_day", "season_str"])["forecast_error"]
                .mean()
                .to_dict()
            )
        else:
            self.clim = {}
            self.global_bias = {}

    def _build_feature_vector(self, issue_date: datetime.date, lat: float, lon: float,
                               lead_day: int, forecast_mean: float, forecast_spread: float,
                               forecast_min: float, forecast_max: float) -> dict:
        month  = issue_date.month
        season = _season(month)
        doy    = issue_date.timetuple().tm_yday
        clim_val = self.clim.get((round(lat, 4), round(lon, 4), month), forecast_mean)
        bias_val = self.global_bias.get((lead_day, season), 10.0)

        feat = {
            "lead_day":         lead_day,
            "lat":              lat,
            "lon":              lon,
            "month":            month,
            "doy_sin":          np.sin(2 * np.pi * doy / 365),
            "doy_cos":          np.cos(2 * np.pi * doy / 365),
            "forecast_mean":    forecast_mean,
            "forecast_spread":  forecast_spread,
            "forecast_min":     forecast_min,
            "forecast_max":     forecast_max,
            "forecast_range":   forecast_max - forecast_min,
            "forecast_anomaly": forecast_mean - clim_val,
            "spatial_gradient": forecast_spread,   # proxy when neighbors not available
            "hist_bias":        bias_val,
            "season_enc":       int(self.le_season.transform(
                                    [season if season in self.le_season.classes_ else self.le_season.classes_[0]]
                                )[0]),
        }
        return feat

    def predict(self, issue_date: datetime.date, lat: float, lon: float,
                lead_days: list = None, forecast_data: dict = None) -> list:
        """
        Predict bust probability for each lead day.

        Args:
            issue_date: forecast issue date
            lat, lon: location
            lead_days: list of lead days (default [1,3,5,7,10])
            forecast_data: optional dict {lead_day: {"mean":, "spread":, "min":, "max":}}

        Returns:
            List of dicts, one per lead day.
        """
        if lead_days is None:
            lead_days = [1, 3, 5, 7, 10]
        if forecast_data is None:
            forecast_data = {}

        results = []
        for ld in lead_days:
            fd = forecast_data.get(ld, {})
            feat = self._build_feature_vector(
                issue_date, lat, lon, ld,
                forecast_mean   = fd.get("mean", 10.0),
                forecast_spread = fd.get("spread", 5.0),
                forecast_min    = fd.get("min", 5.0),
                forecast_max    = fd.get("max", 20.0),
            )
            x = np.array([[feat.get(c, 0.0) for c in self.feature_cols]])
            raw_prob = float(self.model.predict_proba(x)[0, 1])
            cal_prob = float(np.clip(self.calibrator.predict([raw_prob])[0], 0, 1))

            drivers  = get_top_drivers(feat)
            rules    = get_rule_summary(feat)
            band     = confidence_band(cal_prob)
            valid_dt = issue_date + datetime.timedelta(days=ld)

            results.append({
                "lead_day":        ld,
                "valid_date":      str(valid_dt),
                "bust_probability": round(cal_prob, 4),
                "raw_probability": round(raw_prob, 4),
                "confidence_band": band,
                "top_drivers":     drivers,
                "rule_summary":    rules,
            })
        return results

    def batch_predict_region(self, issue_date: datetime.date, lead_day: int,
                              lats: list, lons: list) -> list:
        """Predict for all (lat, lon) pairs at one lead day."""
        out = []
        for lat in lats:
            for lon in lons:
                res = self.predict(issue_date, lat, lon, lead_days=[lead_day])
                item = res[0]
                item["lat"] = lat
                item["lon"] = lon
                out.append(item)
        return out


# Module-level singleton (loaded once when the API starts)
_predictor = None

def get_predictor() -> BustPredictor:
    global _predictor
    if _predictor is None:
        _predictor = BustPredictor()
    return _predictor


if __name__ == "__main__":
    print("Loading predictor...")
    p = BustPredictor()
    result = p.predict(datetime.date(2001, 7, 1), lat=19.0, lon=73.0)
    print("Prediction for 2001-07-01, lat=19.0, lon=73.0:")
    for r in result:
        print(f"  Day {r['lead_day']:2d}: prob={r['bust_probability']:.3f}  "
              f"band={r['confidence_band']}  rules={r['rule_summary'][:1]}")
    print("\nPASS")
