"""
tests/test_rag_and_replays_task08.py
=====================================
Test suite verifying:
  - Task 1: RAG Retriever & Corpus Ingestion (rag_store/ and vector query)
  - Task 2: Pre-cached historical replay JSON files in models/evaluation/replays/
  - Task 3: Visual diagnostic figures in models/evaluation/figures/ & static/figures/
  - API endpoints (/rag-query, /replay, /forecast-reliability, /region, /explanation, /metrics)
"""

import os
import sys
import json
import unittest

# Ensure libomp path is set for XGBoost on macOS
libomp_path = "/opt/homebrew/opt/libomp/lib"
if os.path.exists(libomp_path):
    existing = os.environ.get("DYLD_LIBRARY_PATH", "")
    os.environ["DYLD_LIBRARY_PATH"] = f"{libomp_path}:{existing}" if existing else libomp_path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

class TestRagAndReplays(unittest.TestCase):

    def test_01_rag_store_exists(self):
        rag_dir = os.path.join(ROOT_DIR, "rag_store")
        index_file = os.path.join(rag_dir, "faiss_index.bin")
        chunks_file = os.path.join(rag_dir, "chunks.json")
        self.assertTrue(os.path.exists(index_file), "faiss_index.bin does not exist in rag_store/")
        self.assertTrue(os.path.exists(chunks_file), "chunks.json does not exist in rag_store/")

    def test_02_rag_query(self):
        from src.rag.retrieve import RagRetriever
        retriever = RagRetriever()
        res = retriever.answer("Why does forecast skill degrade at lead days 7-10?")
        self.assertIn("answer", res)
        self.assertIn("sources", res)
        self.assertGreater(len(res["sources"]), 0, "RAG query returned no matching sources")

    def test_03_replays_exist(self):
        replay_dir = os.path.join(ROOT_DIR, "models", "evaluation", "replays")
        index_file = os.path.join(replay_dir, "replay_index.json")
        self.assertTrue(os.path.exists(index_file), "replay_index.json does not exist")
        
        with open(index_file) as f:
            data = json.load(f)
        cases = data.get("replay_cases", []) or data.get("cases", [])
        self.assertGreaterEqual(len(cases), 3, "Fewer than 3 pre-cached replay cases found")

    def test_04_figures_exist(self):
        figures_dir = os.path.join(ROOT_DIR, "models", "evaluation", "figures")
        expected_figs = [
            "calibration_curve.png",
            "roc_pr_curves.png",
            "lead_time_degradation.png",
            "shap_feature_importance.png",
            "confusion_matrix.png",
            "spatial_bust_heatmaps.png",
        ]
        for fig in expected_figs:
            p = os.path.join(figures_dir, fig)
            self.assertTrue(os.path.exists(p), f"Diagnostic figure missing: {fig}")

    def test_05_api_endpoints(self):
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)

        # Health
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)

        # Forecast reliability
        res = client.get("/forecast-reliability?lat=20.0&lon=73.0&issue_date=2002-07-15")
        self.assertEqual(res.status_code, 200)

        # Region
        res = client.get("/region?lead_day=5&issue_date=2002-07-15")
        self.assertEqual(res.status_code, 200)

        # Explanation
        res = client.get("/explanation?lat=20.0&lon=73.0&lead_day=5&issue_date=2002-07-15")
        self.assertEqual(res.status_code, 200)

        # Replay
        res = client.get("/replay?issue_date=2002-07-15")
        self.assertEqual(res.status_code, 200)

        # RAG Query
        res = client.post("/rag-query", json={"question": "What causes monsoon forecast busts?"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("answer", res.json())

if __name__ == "__main__":
    unittest.main()
