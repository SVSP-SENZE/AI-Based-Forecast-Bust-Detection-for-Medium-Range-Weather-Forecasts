"""
src/models/train.py
=====================
Task 04 — Baseline + ML Model Training

Reads data/processed/features.parquet (with is_bust column).
Performs chronological 70/15/15 split.
Trains:
  1. Climatological baseline (stratum bust rate from train set)
  2. Logistic Regression baseline
  3. XGBoost classifier (primary model)

Saves:
  models/logistic_baseline.pkl
  models/xgb_model.pkl
  models/evaluation/metrics_summary.json
  models/evaluation/train_split_info.json
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FEAT_PATH  = os.path.join(ROOT_DIR, "data", "processed", "features.parquet")
MODELS_DIR = os.path.join(ROOT_DIR, "models")
EVAL_DIR   = os.path.join(MODELS_DIR, "evaluation")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(EVAL_DIR, exist_ok=True)

FEATURE_COLS = [
    "lead_day", "lat", "lon",
    "month", "doy_sin", "doy_cos",
    "forecast_mean", "forecast_spread", "forecast_min", "forecast_max", "forecast_range",
    "forecast_anomaly", "spatial_gradient", "hist_bias",
]
LABEL_COL = "is_bust"


def chronological_split(df: pd.DataFrame, train_frac=0.70, val_frac=0.15):
    unique_dates = df["issue_time"].drop_duplicates().sort_values().tolist()
    n = len(unique_dates)
    n_train = int(n * train_frac)
    n_val   = int(n * val_frac)
    train_dates = set(unique_dates[:n_train])
    val_dates   = set(unique_dates[n_train:n_train + n_val])
    test_dates  = set(unique_dates[n_train + n_val:])
    return (
        df[df["issue_time"].isin(train_dates)],
        df[df["issue_time"].isin(val_dates)],
        df[df["issue_time"].isin(test_dates)],
    )


def clim_baseline_predict(df_train, df_eval):
    """Predict bust probability as historical bust rate per (lead_day, season)."""
    rates = df_train.groupby(["lead_day", "season"])[LABEL_COL].mean().to_dict()
    global_rate = df_train[LABEL_COL].mean()
    preds = df_eval.apply(
        lambda r: rates.get((r["lead_day"], r["season"]), global_rate), axis=1
    )
    return preds.values


def evaluate_model(y_true, y_prob, name):
    roc  = roc_auc_score(y_true, y_prob)
    pr   = average_precision_score(y_true, y_prob)
    brier = brier_score_loss(y_true, y_prob)
    print(f"  {name:35s}  ROC-AUC={roc:.4f}  PR-AUC={pr:.4f}  Brier={brier:.4f}")
    return {"model": name, "roc_auc": round(roc, 4), "pr_auc": round(pr, 4), "brier": round(brier, 4)}


def encode_categoricals(df_train, df_val, df_test):
    """Label-encode season column."""
    le = LabelEncoder()
    le.fit(df_train["season"])
    for df in [df_train, df_val, df_test]:
        df["season_enc"] = le.transform(df["season"].map(
            lambda x: x if x in le.classes_ else le.classes_[0]
        ))
    return df_train, df_val, df_test, le


def main():
    print("=" * 60)
    print("TASK 04 — MODEL TRAINING")
    print("=" * 60)

    if not os.path.exists(FEAT_PATH):
        print(f"FAIL: {FEAT_PATH} not found.")
        sys.exit(1)

    df = pd.read_parquet(FEAT_PATH)
    df["issue_time"] = pd.to_datetime(df["issue_time"])

    if LABEL_COL not in df.columns:
        print(f"FAIL: '{LABEL_COL}' column not found. Run bust_label.py first.")
        sys.exit(1)

    print(f"Loaded {len(df)} rows. Bust rate: {df[LABEL_COL].mean():.2%}")

    df_train, df_val, df_test = chronological_split(df)
    print(f"Split: train={len(df_train)} ({df_train['issue_time'].nunique()} dates), "
          f"val={len(df_val)} ({df_val['issue_time'].nunique()} dates), "
          f"test={len(df_test)} ({df_test['issue_time'].nunique()} dates)")

    df_train, df_val, df_test, le_season = encode_categoricals(df_train.copy(), df_val.copy(), df_test.copy())

    feat_cols = FEATURE_COLS + ["season_enc"]
    X_train = df_train[feat_cols].values
    y_train = df_train[LABEL_COL].values
    X_val   = df_val[feat_cols].values
    y_val   = df_val[LABEL_COL].values
    X_test  = df_test[feat_cols].values
    y_test  = df_test[LABEL_COL].values

    results = []

    # ── 1. Climatological baseline ─────────────────────────────────
    print("\n[1] Climatological baseline")
    clim_val_preds  = clim_baseline_predict(df_train, df_val)
    clim_test_preds = clim_baseline_predict(df_train, df_test)
    results.append(evaluate_model(y_test, clim_test_preds, "Climatological Baseline"))

    # ── 2. Logistic Regression ────────────────────────────────────
    print("\n[2] Logistic Regression")
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr.fit(X_train, y_train)
    lr_test_preds = lr.predict_proba(X_test)[:, 1]
    results.append(evaluate_model(y_test, lr_test_preds, "Logistic Regression"))
    with open(os.path.join(MODELS_DIR, "logistic_baseline.pkl"), "wb") as f:
        pickle.dump(lr, f)

    # ── 3. XGBoost ───────────────────────────────────────────────
    print("\n[3] XGBoost")
    try:
        from xgboost import XGBClassifier
        scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
        xgb = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            scale_pos_weight=scale_pos_weight,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
        xgb.fit(X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False)
        xgb_test_preds = xgb.predict_proba(X_test)[:, 1]
        results.append(evaluate_model(y_test, xgb_test_preds, "XGBoost"))
        with open(os.path.join(MODELS_DIR, "xgb_model.pkl"), "wb") as f:
            pickle.dump(xgb, f)
        # Also save val predictions for calibration
        xgb_val_preds = xgb.predict_proba(X_val)[:, 1]
        val_df = df_val[["issue_time", "lead_day", "lat", "lon", "season", LABEL_COL]].copy()
        val_df["raw_prob"] = xgb_val_preds
        val_df.to_parquet(os.path.join(EVAL_DIR, "val_predictions.parquet"), index=False)
        test_df = df_test[["issue_time", "lead_day", "lat", "lon", "season", LABEL_COL]].copy()
        test_df["raw_prob"] = xgb_test_preds
        test_df["clim_prob"] = clim_test_preds
        test_df["lr_prob"] = lr_test_preds
        test_df.to_parquet(os.path.join(EVAL_DIR, "test_predictions.parquet"), index=False)
        primary_model = "XGBoost"
    except ImportError:
        print("  XGBoost not installed. Trying LightGBM...")
        try:
            import lightgbm as lgb
            scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
            lgb_model = lgb.LGBMClassifier(
                n_estimators=300, max_depth=5, learning_rate=0.05,
                scale_pos_weight=scale_pos_weight, random_state=42, n_jobs=-1, verbose=-1
            )
            lgb_model.fit(X_train, y_train)
            lgb_test_preds = lgb_model.predict_proba(X_test)[:, 1]
            results.append(evaluate_model(y_test, lgb_test_preds, "LightGBM"))
            with open(os.path.join(MODELS_DIR, "xgb_model.pkl"), "wb") as f:
                pickle.dump(lgb_model, f)
            lgb_val_preds = lgb_model.predict_proba(X_val)[:, 1]
            val_df = df_val[["issue_time", "lead_day", "lat", "lon", "season", LABEL_COL]].copy()
            val_df["raw_prob"] = lgb_val_preds
            val_df.to_parquet(os.path.join(EVAL_DIR, "val_predictions.parquet"), index=False)
            test_df = df_test[["issue_time", "lead_day", "lat", "lon", "season", LABEL_COL]].copy()
            test_df["raw_prob"] = lgb_test_preds
            test_df["clim_prob"] = clim_test_preds
            test_df["lr_prob"] = lr_test_preds
            test_df.to_parquet(os.path.join(EVAL_DIR, "test_predictions.parquet"), index=False)
            primary_model = "LightGBM"
        except ImportError:
            print("  Neither XGBoost nor LightGBM installed.")
            primary_model = "Logistic Regression"
            results[-1]["model"] = "Primary (LogReg fallback)"

    # ── Save metrics ─────────────────────────────────────────────
    split_info = {
        "train_dates": int(df_train["issue_time"].nunique()),
        "val_dates": int(df_val["issue_time"].nunique()),
        "test_dates": int(df_test["issue_time"].nunique()),
        "train_rows": len(df_train),
        "val_rows": len(df_val),
        "test_rows": len(df_test),
        "train_bust_rate": round(float(y_train.mean()), 4),
        "test_bust_rate": round(float(y_test.mean()), 4),
        "primary_model": primary_model,
    }

    with open(os.path.join(EVAL_DIR, "metrics_summary.json"), "w") as f:
        json.dump({"split": split_info, "test_metrics": results}, f, indent=2)

    with open(os.path.join(EVAL_DIR, "train_split_info.json"), "w") as f:
        json.dump(split_info, f, indent=2)

    # Save LabelEncoder for inference
    with open(os.path.join(MODELS_DIR, "season_encoder.pkl"), "wb") as f:
        pickle.dump(le_season, f)
    with open(os.path.join(MODELS_DIR, "feature_cols.json"), "w") as f:
        json.dump({"features": feat_cols, "label": LABEL_COL}, f)

    print(f"\nModels saved to: {MODELS_DIR}")
    print(f"Evaluation saved to: {EVAL_DIR}")
    print("\nPASS")


if __name__ == "__main__":
    main()
