"""
tests/test_dataset_task02.py
=============================
Test dataset validity for Task 02.
"""

import os
import sys
import unittest
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestDatasetTask02(unittest.TestCase):

    def test_dataset_integrity(self):
        p1 = os.path.join(ROOT_DIR, "models", "evaluation", "test_predictions.parquet")
        p2 = os.path.join(ROOT_DIR, "data", "processed", "features.parquet")
        parquet_file = p1 if os.path.exists(p1) else p2

        self.assertTrue(os.path.exists(parquet_file), f"Dataset file {parquet_file} does not exist.")
        df = pd.read_parquet(parquet_file)
        self.assertGreater(len(df), 0, "Dataset is empty.")

        # Check required columns
        for col in ["issue_time", "lead_day", "lat", "lon", "is_bust"]:
            self.assertIn(col, df.columns, f"Missing required column: {col}")

        # Check lead day set
        self.assertTrue(set(df["lead_day"].unique()).issubset({1, 3, 5, 7, 10}), "Unexpected lead days")

if __name__ == "__main__":
    unittest.main()
