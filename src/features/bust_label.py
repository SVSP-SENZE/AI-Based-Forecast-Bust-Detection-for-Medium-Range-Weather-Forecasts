"""
src/features/bust_label.py
===========================
Task 03 — Bust Label Generation

Reads data/processed/features.parquet (output of engineer_features.py).

For each stratum (lead_day, season):
  - Computes 85th, 87.5th, 90th percentile of forecast_error on TRAINING rows only
  - Prints a bust-rate report table for human review
  - Applies the chosen percentile (default 85th) to create is_bust (0/1)
  - Saves updated data/processed/features.parquet with is_bust column

Usage:
    python src/features/bust_label.py [--percentile 85]
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FEAT_PATH = os.path.join(ROOT_DIR, "data", "processed", "features.parquet")
REPORT_PATH = os.path.join(ROOT_DIR, "data", "processed", "bust_threshold_report.csv")


def chronological_train_mask(df: pd.DataFrame, train_frac: float = 0.70) -> pd.Series:
    """Return boolean mask for the earliest train_frac of issue dates."""
    unique_dates = df["issue_time"].drop_duplicates().sort_values()
    n_train = max(1, int(len(unique_dates) * train_frac))
    train_dates = set(unique_dates.iloc[:n_train])
    return df["issue_time"].isin(train_dates)


def compute_bust_report(df_train: pd.DataFrame) -> pd.DataFrame:
    """Compute bust-rate table for candidate percentiles, on training rows only."""
    strata = df_train.groupby(["lead_day", "season"])
    rows = []
    for (lead, season), grp in strata:
        errs = grp["forecast_error"].dropna()
        if len(errs) < 10:
            continue
        for pct in [85, 87.5, 90]:
            thresh = np.percentile(errs, pct)
            bust_rate = (errs > thresh).mean()
            rows.append({
                "lead_day": lead,
                "season": season,
                "percentile": pct,
                "threshold_mm": round(thresh, 3),
                "bust_rate_pct": round(bust_rate * 100, 1),
                "n_train_rows": len(errs),
            })
    return pd.DataFrame(rows).sort_values(["lead_day", "season", "percentile"])


def apply_bust_label(df: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    """Apply bust label using pre-computed thresholds per (lead_day, season)."""
    df = df.copy()
    df["is_bust"] = 0
    for (lead, season), thresh in thresholds.items():
        mask = (df["lead_day"] == lead) & (df["season"] == season)
        df.loc[mask & (df["forecast_error"] > thresh), "is_bust"] = 1
    return df


def main():
    parser = argparse.ArgumentParser(description="Bust label generation")
    parser.add_argument("--percentile", type=float, default=85.0,
                        help="Percentile to use for bust threshold (default: 85)")
    args = parser.parse_args()

    print("=" * 60)
    print("TASK 03 — BUST LABEL GENERATION")
    print(f"Using {args.percentile}th percentile threshold")
    print("=" * 60)

    if not os.path.exists(FEAT_PATH):
        print(f"FAIL: {FEAT_PATH} not found. Run engineer_features.py first.")
        sys.exit(1)

    df = pd.read_parquet(FEAT_PATH)
    df["issue_time"] = pd.to_datetime(df["issue_time"])
    print(f"Loaded {len(df)} rows, {df['issue_time'].nunique()} issue dates.")

    train_mask = chronological_train_mask(df)
    df_train = df[train_mask]
    print(f"Training rows: {train_mask.sum()} ({train_mask.mean()*100:.0f}%)")

    # ── Bust rate report ───────────────────────────────────────────
    report = compute_bust_report(df_train)
    report.to_csv(REPORT_PATH, index=False)
    print(f"\nBust-rate report saved to: {REPORT_PATH}")
    print("\n" + report.to_string(index=False))

    # ── Apply chosen threshold ─────────────────────────────────────
    chosen_report = report[report["percentile"] == args.percentile]
    thresholds = {}
    for _, row in chosen_report.iterrows():
        thresholds[(int(row["lead_day"]), row["season"])] = row["threshold_mm"]

    if not thresholds:
        print(f"FAIL: No thresholds found for percentile {args.percentile}")
        sys.exit(1)

    df_labeled = apply_bust_label(df, thresholds)

    # ── Summary stats ──────────────────────────────────────────────
    overall_bust_rate = df_labeled["is_bust"].mean()
    print(f"\nOverall bust rate (full dataset): {overall_bust_rate:.2%}")
    print("\nBust rate by lead_day & season:")
    print(df_labeled.groupby(["lead_day", "season"])["is_bust"].mean().round(3).to_string())

    # ── Save ──────────────────────────────────────────────────────
    df_labeled.to_parquet(FEAT_PATH, engine="pyarrow", index=False)
    print(f"\nSaved with is_bust column to: {FEAT_PATH}")
    print("\nPASS")


if __name__ == "__main__":
    main()
