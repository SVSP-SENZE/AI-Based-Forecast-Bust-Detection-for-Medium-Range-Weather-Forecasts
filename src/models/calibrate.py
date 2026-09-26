"""
src/models/calibrate.py
========================
Task 05 — Isotonic Calibration

Loads raw validation predictions (val_predictions.parquet),
fits isotonic regression, saves calibrator.pkl,
then applies to test predictions and updates test_predictions.parquet
with a 'cal_prob' column.
"""

import os
import sys
import pickle
import json
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

ROOT_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL_DIR  = os.path.join(ROOT_DIR, "models", "evaluation")
MODELS_DIR = os.path.join(ROOT_DIR, "models")

VAL_PATH  = os.path.join(EVAL_DIR, "val_predictions.parquet")
TEST_PATH = os.path.join(EVAL_DIR, "test_predictions.parquet")
CAL_PATH  = os.path.join(MODELS_DIR, "calibrator.pkl")


def reliability_bins(y_true, y_prob, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1)
    centers, actuals, counts = [], [], []
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
        if mask.sum() == 0:
            continue
        centers.append(round(float((bins[i] + bins[i + 1]) / 2), 3))
        actuals.append(round(float(y_true[mask].mean()), 4))
        counts.append(int(mask.sum()))
    return {"bin_centers": centers, "actual_bust_rate": actuals, "counts": counts}


def main():
    print("=" * 60)
    print("TASK 05 — CALIBRATION")
    print("=" * 60)

    if not os.path.exists(VAL_PATH):
        print(f"FAIL: {VAL_PATH} not found. Run train.py first.")
        sys.exit(1)

    val_df  = pd.read_parquet(VAL_PATH)
    test_df = pd.read_parquet(TEST_PATH)

    y_val      = val_df["is_bust"].values
    y_val_prob = val_df["raw_prob"].values
    y_test     = test_df["is_bust"].values
    y_test_prob = test_df["raw_prob"].values

    # ── Fit isotonic regression on validation fold ─────────────────
    ir = IsotonicRegression(out_of_bounds="clip")
    ir.fit(y_val_prob, y_val)

    # ── Apply to test ──────────────────────────────────────────────
    cal_test = ir.predict(y_test_prob)

    brier_raw = brier_score_loss(y_test, y_test_prob)
    brier_cal = brier_score_loss(y_test, cal_test)
    print(f"Brier score (raw)       : {brier_raw:.4f}")
    print(f"Brier score (calibrated): {brier_cal:.4f}")
    print(f"Calibration {'IMPROVED' if brier_cal < brier_raw else 'NOT improved'}")

    # Reliability before/after
    rel_before = reliability_bins(y_test, y_test_prob)
    rel_after  = reliability_bins(y_test, cal_test)

    # ── Save ──────────────────────────────────────────────────────
    with open(CAL_PATH, "wb") as f:
        pickle.dump(ir, f)
    print(f"Calibrator saved: {CAL_PATH}")

    test_df["cal_prob"] = cal_test
    test_df.to_parquet(TEST_PATH, index=False)

    cal_report = {
        "brier_raw": round(brier_raw, 4),
        "brier_calibrated": round(brier_cal, 4),
        "reliability_before": rel_before,
        "reliability_after":  rel_after,
    }
    with open(os.path.join(EVAL_DIR, "calibration_report.json"), "w") as f:
        json.dump(cal_report, f, indent=2)

    print("\nPASS")


if __name__ == "__main__":
    main()
