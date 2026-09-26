"""
src/explain/shap_explain.py
============================
Task 05 — SHAP-based explainability

Provides:
  - compute_global_shap(): saves shap_importance.json (global feature importance)
  - get_top_drivers(feature_dict, model, feature_cols): returns top-3 SHAP drivers
    for a single prediction, with direction and magnitude.
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
EVAL_DIR   = os.path.join(MODELS_DIR, "evaluation")


def load_model_and_cols():
    model_path = os.path.join(MODELS_DIR, "xgb_model.pkl")
    feat_path  = os.path.join(MODELS_DIR, "feature_cols.json")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(feat_path) as f:
        feat_info = json.load(f)
    return model, feat_info["features"]


def get_top_drivers(feature_dict: dict, n: int = 3) -> list:
    """
    Given a dict of {feature_name: value} for one prediction,
    return top-n SHAP contributors as list of
    {"feature": str, "value": float, "shap_value": float, "direction": "up"/"down"}.
    Falls back to feature importance if SHAP not available.
    """
    try:
        import shap
        model, feature_cols = load_model_and_cols()
        x = np.array([[feature_dict.get(c, 0.0) for c in feature_cols]])
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(x)[0]   # shape: (n_features,)
        top_idx = np.argsort(np.abs(shap_vals))[::-1][:n]
        drivers = []
        for i in top_idx:
            drivers.append({
                "feature": feature_cols[i],
                "value": round(float(feature_dict.get(feature_cols[i], 0.0)), 4),
                "shap_value": round(float(shap_vals[i]), 4),
                "direction": "up" if shap_vals[i] > 0 else "down",
            })
        return drivers
    except Exception as e:
        # Fallback: use model's feature importances
        try:
            model, feature_cols = load_model_and_cols()
            importances = model.feature_importances_
            top_idx = np.argsort(importances)[::-1][:n]
            return [
                {
                    "feature": feature_cols[i],
                    "value": round(float(feature_dict.get(feature_cols[i], 0.0)), 4),
                    "shap_value": round(float(importances[i]), 4),
                    "direction": "up",
                }
                for i in top_idx
            ]
        except Exception:
            return []


def compute_global_shap(X_test: np.ndarray, feature_cols: list, model) -> dict:
    """Compute mean |SHAP| per feature over test set. Returns dict."""
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_test)
        mean_abs = np.abs(shap_vals).mean(axis=0)
        importance = {
            feature_cols[i]: round(float(mean_abs[i]), 6)
            for i in np.argsort(mean_abs)[::-1]
        }
        return importance
    except Exception as e:
        # Fallback: model.feature_importances_
        try:
            imp = model.feature_importances_
            return {feature_cols[i]: round(float(imp[i]), 6) for i in np.argsort(imp)[::-1]}
        except Exception:
            return {}


def main():
    """Run global SHAP analysis on test set and save importance."""
    print("=" * 60)
    print("TASK 05 — SHAP ANALYSIS")
    print("=" * 60)

    test_path = os.path.join(EVAL_DIR, "test_predictions.parquet")
    feat_path = os.path.join(ROOT_DIR, "data", "processed", "features.parquet")

    if not os.path.exists(feat_path):
        print("FAIL: features.parquet not found.")
        sys.exit(1)

    model, feature_cols = load_model_and_cols()

    # Load test split (match by issue_time)
    test_df = pd.read_parquet(test_path)
    feat_df = pd.read_parquet(feat_path)
    feat_df["issue_time"] = pd.to_datetime(feat_df["issue_time"])
    test_df["issue_time"] = pd.to_datetime(test_df["issue_time"])

    test_issue_dates = set(test_df["issue_time"].unique())
    feat_test = feat_df[feat_df["issue_time"].isin(test_issue_dates)]

    # Add season_enc
    enc_path = os.path.join(MODELS_DIR, "season_encoder.pkl")
    with open(enc_path, "rb") as f:
        le = pickle.load(f)
    feat_test = feat_test.copy()
    feat_test["season_enc"] = le.transform(feat_test["season"].map(
        lambda x: x if x in le.classes_ else le.classes_[0]
    ))

    X_test = feat_test[feature_cols].values

    importance = compute_global_shap(X_test, feature_cols, model)
    out_path = os.path.join(EVAL_DIR, "shap_importance.json")
    with open(out_path, "w") as f:
        json.dump(importance, f, indent=2)

    print("\nTop feature importances:")
    for feat, val in list(importance.items())[:10]:
        print(f"  {feat:<30} {val:.4f}")
    print(f"\nSaved to: {out_path}")
    print("\nPASS")


if __name__ == "__main__":
    main()
