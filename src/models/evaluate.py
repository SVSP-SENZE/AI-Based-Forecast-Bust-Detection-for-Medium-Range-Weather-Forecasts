"""
src/models/evaluate.py
========================
Task 04 — Full Evaluation Suite

Reads models/evaluation/test_predictions.parquet
Produces:
  - Confusion matrix, precision/recall/F1
  - ROC-AUC, PR-AUC, Brier score
  - Reliability diagram data
  - Lead-time and season stratified tables
  - Baseline vs ML comparison

Saves all to models/evaluation/
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss,
    confusion_matrix, precision_recall_fscore_support,
)

ROOT_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL_DIR  = os.path.join(ROOT_DIR, "models", "evaluation")
TEST_PATH = os.path.join(EVAL_DIR, "test_predictions.parquet")


def reliability_bins(y_true, y_prob, n_bins=10):
    """Compute reliability diagram data (predicted prob bucket vs actual bust rate)."""
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers, bin_freqs, bin_counts = [], [], []
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
        if mask.sum() == 0:
            continue
        bin_centers.append(round(float((bins[i] + bins[i + 1]) / 2), 3))
        bin_freqs.append(round(float(y_true[mask].mean()), 4))
        bin_counts.append(int(mask.sum()))
    return {"bin_centers": bin_centers, "actual_bust_rate": bin_freqs, "counts": bin_counts}


def evaluate_all(test_df):
    y_true = test_df["is_bust"].values

    results = {}
    for col, name in [("raw_prob", "XGBoost"), ("lr_prob", "LogisticRegression"),
                      ("clim_prob", "ClimatologicalBaseline")]:
        if col not in test_df.columns:
            continue
        y_prob = test_df[col].values
        # Choose threshold at 50th percentile of predicted probs
        threshold = np.median(y_prob)
        y_pred = (y_prob >= threshold).astype(int)
        prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
        cm = confusion_matrix(y_true, y_pred).tolist()
        rel = reliability_bins(y_true, y_prob)
        results[name] = {
            "roc_auc":  round(float(roc_auc_score(y_true, y_prob)), 4),
            "pr_auc":   round(float(average_precision_score(y_true, y_prob)), 4),
            "brier":    round(float(brier_score_loss(y_true, y_prob)), 4),
            "precision": round(float(prec), 4),
            "recall":    round(float(rec), 4),
            "f1":        round(float(f1), 4),
            "threshold": round(float(threshold), 4),
            "confusion_matrix": cm,
            "reliability": rel,
        }

    return results


def stratified_table(test_df, group_col, prob_col="raw_prob"):
    if prob_col not in test_df.columns:
        return {}
    rows = []
    for val, grp in test_df.groupby(group_col):
        if len(grp) < 5:
            continue
        y_true = grp["is_bust"].values
        y_prob = grp[prob_col].values
        try:
            roc = roc_auc_score(y_true, y_prob)
            pr  = average_precision_score(y_true, y_prob)
        except Exception:
            roc, pr = float("nan"), float("nan")
        rows.append({group_col: val, "roc_auc": round(roc, 4), "pr_auc": round(pr, 4),
                     "bust_rate": round(float(y_true.mean()), 4), "n": len(grp)})
    return pd.DataFrame(rows)


def main():
    print("=" * 60)
    print("TASK 04 — MODEL EVALUATION")
    print("=" * 60)

    if not os.path.exists(TEST_PATH):
        print(f"FAIL: {TEST_PATH} not found. Run train.py first.")
        sys.exit(1)

    test_df = pd.read_parquet(TEST_PATH)
    print(f"Test set: {len(test_df)} rows, bust rate: {test_df['is_bust'].mean():.2%}")

    # Overall metrics
    all_metrics = evaluate_all(test_df)

    print("\n── Overall Metrics (Test Set) ──")
    print(f"{'Model':<30} {'ROC-AUC':>8} {'PR-AUC':>8} {'Brier':>8} {'F1':>8}")
    print("-" * 60)
    for name, m in all_metrics.items():
        print(f"{name:<30} {m['roc_auc']:>8.4f} {m['pr_auc']:>8.4f} {m['brier']:>8.4f} {m['f1']:>8.4f}")

    # Stratified tables
    lead_table  = stratified_table(test_df, "lead_day")
    season_table = stratified_table(test_df, "season")

    print("\n── By Lead Day (XGBoost) ──")
    print(lead_table.to_string(index=False))
    print("\n── By Season (XGBoost) ──")
    print(season_table.to_string(index=False))

    # Save
    with open(os.path.join(EVAL_DIR, "all_metrics.json"), "w") as f:
        json.dump(all_metrics, f, indent=2)
    lead_table.to_csv(os.path.join(EVAL_DIR, "lead_day_metrics.csv"), index=False)
    season_table.to_csv(os.path.join(EVAL_DIR, "season_metrics.csv"), index=False)

    print(f"\nAll outputs saved to: {EVAL_DIR}")
    print("\nPASS")


if __name__ == "__main__":
    main()
