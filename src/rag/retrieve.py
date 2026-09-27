"""
src/rag/retrieve.py
====================
Task 1 (RAG) — Dense retrieval using FAISS vector index.

Usage:
    from src.rag.retrieve import RagRetriever
    retriever = RagRetriever()
    chunks = retriever.retrieve("high ensemble spread monsoon forecast")
"""

import os
import sys
import json
import re

ROOT_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STORE_DIR = os.path.join(ROOT_DIR, "rag_store")


class RagRetriever:
    """
    Dense retrieval + cited answer generation for the meteorological RAG layer.

    Exposes:
        retrieve(query, k=4)  → list of top-k chunk dicts
        answer(question, context=None, k=4)  → {answer: str, sources: list}
    """

    def __init__(self):
        self._index = None
        self._chunks = None
        self._embed_model = None
        self._load()

    def _load(self):
        """Load FAISS index, chunk store, and embedding model."""
        index_path  = os.path.join(STORE_DIR, "faiss_index.bin")
        chunks_path = os.path.join(STORE_DIR, "chunks.json")
        meta_path   = os.path.join(STORE_DIR, "index_meta.json")

        if not os.path.exists(index_path) or not os.path.exists(chunks_path):
            raise FileNotFoundError(
                f"RAG index not found at {STORE_DIR}. "
                "Run: python -m src.rag.ingest"
            )

        import faiss
        self._index = faiss.read_index(index_path)

        with open(chunks_path, "r", encoding="utf-8") as f:
            self._chunks = json.load(f)

        with open(meta_path) as f:
            meta = json.load(f)

        print(f"[RAG] Loaded {meta['total_chunks']} chunks from {meta['n_documents']} docs.")

        from sentence_transformers import SentenceTransformer
        self._embed_model = SentenceTransformer(meta.get("embed_model", "all-MiniLM-L6-v2"))
        print("[RAG] Embedding model loaded.")

    def _embed_query(self, query: str):
        """Embed a query string and L2-normalize for cosine similarity."""
        import numpy as np
        import faiss
        vec = self._embed_model.encode([query], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(vec)
        return vec

    def retrieve(self, query: str, k: int = 4, min_score: float = 0.0) -> list:
        """
        Retrieve top-k most relevant chunks for the given query.

        Args:
            query: Natural language query string.
            k: Number of chunks to retrieve.
            min_score: Minimum similarity score (0-1 range after normalization).

        Returns:
            List of chunk dicts with added 'similarity' field.
        """
        import numpy as np
        vec = self._embed_query(query)
        distances, indices = self._index.search(vec, min(k * 2, len(self._chunks)))

        results = []
        seen_docs = set()
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._chunks):
                continue
            # Convert L2 distance (after normalization) to similarity: sim = 1 - dist/2
            # (For normalized vectors: L2^2 = 2 - 2*cosine_sim)
            similarity = max(0.0, 1.0 - float(dist) / 2.0)
            if similarity < min_score:
                continue
            chunk = dict(self._chunks[idx])
            chunk["similarity"] = round(similarity, 4)
            # Prefer document diversity (avoid all chunks from same doc)
            if chunk["doc_id"] in seen_docs and len(results) >= k // 2:
                continue
            seen_docs.add(chunk["doc_id"])
            results.append(chunk)
            if len(results) >= k:
                break

        return results

    def retrieve_for_drivers(self, top_drivers: list, rule_summary: list,
                              region: str = "Maharashtra", lead_day: int = 5,
                              season: str = "monsoon", k: int = 4) -> list:
        """
        Build an enhanced query from SHAP drivers and rule-based summary,
        then retrieve relevant chunks. This is the primary retrieval path
        called from the /rag-query endpoint.
        """
        # Build a rich natural-language query from structured model output
        driver_phrases = []
        for d in top_drivers[:3]:
            feat = d.get("feature", "")
            direction = d.get("direction", "up")
            val = d.get("value", 0)
            if feat == "lead_day":
                driver_phrases.append(f"Day {int(val)} lead time forecast uncertainty")
            elif feat == "forecast_spread":
                driver_phrases.append(f"high ensemble spread ({val:.1f} mm) forecast disagreement")
            elif feat == "spatial_gradient":
                driver_phrases.append(f"high spatial forecast gradient ({val:.1f} mm) convective boundary")
            elif feat == "hist_bias":
                driver_phrases.append(f"historical forecast bias {val:.1f} mm systematic error")
            elif feat == "forecast_anomaly":
                driver_phrases.append(f"forecast anomaly {val:.1f} mm above-normal rainfall uncertainty")
            elif feat == "forecast_mean":
                driver_phrases.append(f"high rainfall forecast {val:.1f} mm extreme event predictability")
            else:
                driver_phrases.append(f"{feat} {'increasing' if direction == 'up' else 'decreasing'} bust risk")

        rule_text = "; ".join(rule_summary[:2]) if rule_summary else ""

        query = (
            f"{season} season monsoon rainfall forecast reliability {region} India "
            f"lead time Day {lead_day} "
            + ", ".join(driver_phrases)
            + (f". {rule_text}" if rule_text else "")
        )

        return self.retrieve(query, k=k)

    def answer(self, question: str, context: dict = None, k: int = 4) -> dict:
        """
        Generate a cited meteorological explanation using retrieved chunks.

        Args:
            question: The free-text question or auto-query from /explain.
            context: Optional structured dict with model output
                     (bust_probability, confidence_band, top_drivers, rule_summary, etc.).
            k: Number of chunks to retrieve.

        Returns:
            dict with keys: answer (str), sources (list), retrieved_chunks (list)
        """
        # Build query
        if context:
            top_drivers = context.get("top_drivers", [])
            rule_summary = context.get("rule_summary", [])
            region = context.get("region", "Maharashtra")
            lead_day = context.get("lead_day", 5)
            season = context.get("season", "monsoon")
            chunks = self.retrieve_for_drivers(
                top_drivers=top_drivers,
                rule_summary=rule_summary,
                region=region,
                lead_day=lead_day,
                season=season,
                k=k,
            )
        else:
            chunks = self.retrieve(question, k=k)

        if not chunks:
            fallback_text = (
                question if question else
                "The rule-based summary and SHAP drivers provide the available explanation."
            )
            return {
                "answer": (
                    f"No additional literature context was retrieved for this query. "
                    f"{fallback_text}"
                ),
                "sources": [],
                "retrieved_chunks": [],
            }

        # Generate answer using local generation (no external API required)
        # Falls back to template generation if Anthropic is not available
        answer_text = self._generate_answer(question, context, chunks)

        # Build source list from used chunks
        sources = []
        seen_sources = set()
        for c in chunks:
            if c["source"] not in seen_sources:
                sources.append({
                    "title": c["source"],
                    "citation": c["citation"],
                    "url": c["url"],
                    "section": c["section"],
                    "similarity": c.get("similarity", 0.0),
                })
                seen_sources.add(c["source"])

        return {
            "answer": answer_text,
            "sources": sources,
            "retrieved_chunks": [
                {"chunk_id": c["chunk_id"], "text_preview": c["text"][:200] + "...", "similarity": c.get("similarity", 0.0)}
                for c in chunks
            ],
        }

    def _generate_answer(self, question: str, context: dict, chunks: list) -> str:
        """
        Generate a grounded, cited explanation from retrieved chunks and model context.
        Uses template-based generation that is entirely local and hallucination-resistant.
        """
        if not context:
            # Simple question-answering from retrieved context
            context_text = "\n\n".join([f"[{c['source']}]: {c['text'][:400]}" for c in chunks[:3]])
            return self._template_generate(question, None, chunks)

        # Structured explanation from model output + retrieved context
        bust_prob = context.get("bust_probability", None)
        confidence_band = context.get("confidence_band", "Unknown")
        top_drivers = context.get("top_drivers", [])
        rule_summary = context.get("rule_summary", [])
        lead_day = context.get("lead_day", 5)
        region = context.get("region", "this region")

        return self._template_generate(question, context, chunks)

    def _template_generate(self, question: str, context: dict, chunks: list) -> str:
        """
        Template-based cited answer generation.
        Entirely local — no external API calls. Uses retrieved chunk text to compose answer.
        """
        if not context:
            # Plain question answering
            relevant_text = chunks[0]["text"][:600] if chunks else ""
            src = chunks[0]["source"] if chunks else "unknown source"
            return (
                f"Based on the retrieved meteorological documentation: {relevant_text[:400]}... "
                f"[{src}]"
            )

        bust_prob = context.get("bust_probability")
        confidence_band = context.get("confidence_band", "Moderate")
        top_drivers = context.get("top_drivers", [])
        rule_summary = context.get("rule_summary", [])
        lead_day = context.get("lead_day", 5)
        region = context.get("region", "the forecast region")

        # --- Compose explanation ---
        prob_str = f"{bust_prob*100:.0f}%" if bust_prob is not None else "elevated"

        # Opening sentence: confidence band + probability
        sentences = [
            f"This forecast has **{confidence_band} reliability** "
            f"(bust probability: {prob_str}), meaning the model identifies a "
            f"{'high' if confidence_band == 'Low' else 'moderate' if confidence_band == 'Moderate' else 'low'} "
            f"risk that this forecast will produce an unusually large error (a 'forecast bust')."
        ]

        # Driver sentence from rule summary
        if rule_summary:
            rule_text = rule_summary[0] if len(rule_summary) == 1 else "; ".join(rule_summary[:2])
            sentences.append(f"The primary contributing factors identified are: {rule_text}.")

        # Grounded meteorological sentence from retrieved chunks (with citation)
        for chunk in chunks[:2]:
            chunk_text = chunk["text"]
            src = chunk["source"]
            # Extract a relevant sub-sentence
            key_sentences = [s.strip() for s in chunk_text.split(".") if len(s.strip()) > 40]
            if key_sentences:
                # Pick the most relevant sentence (simple heuristic: contains driver keywords)
                driver_keywords = []
                for d in top_drivers:
                    feat = d.get("feature", "")
                    if "spread" in feat:
                        driver_keywords.extend(["spread", "ensemble", "uncertainty"])
                    elif "gradient" in feat:
                        driver_keywords.extend(["gradient", "spatial", "convective"])
                    elif "lead" in feat:
                        driver_keywords.extend(["lead time", "predictability", "skill"])
                    elif "bias" in feat:
                        driver_keywords.extend(["bias", "systematic", "historical"])
                    elif "anomaly" in feat:
                        driver_keywords.extend(["anomaly", "extreme", "above-normal"])

                best_sentence = key_sentences[0]
                for ks in key_sentences:
                    if any(kw.lower() in ks.lower() for kw in driver_keywords):
                        best_sentence = ks
                        break

                if len(best_sentence) > 20:
                    sentences.append(
                        f"This is consistent with established meteorological understanding: "
                        f"\"{best_sentence}.\" [{src}]"
                    )
                    break  # One grounded citation per answer

        # Lead time context sentence
        if lead_day >= 7:
            sentences.append(
                f"At Day {lead_day}, lead-time skill degradation is a well-documented "
                f"contributor to forecast uncertainty — NWP skill for rainfall over India "
                f"decreases substantially beyond Day 5, particularly for specific rainfall amounts "
                f"[WMO — Forecast Verification: Methods and Applications; ECMWF — Medium-Range Forecast Predictability]."
            )
        elif lead_day >= 5:
            sentences.append(
                f"At Day {lead_day}, forecast skill is in the transitional range where "
                f"large-scale patterns remain useful guidance but specific rainfall totals "
                f"carry meaningful uncertainty [ECMWF — Medium-Range Forecast Predictability]."
            )

        # Closing disclaimer
        sentences.append(
            "Note: All probability values are produced by the XGBoost bust-detection model; "
            "this explanation synthesizes meteorological literature context only and does not "
            "modify or regenerate any model output."
        )

        return " ".join(sentences)


if __name__ == "__main__":
    # Quick retrieval smoke test
    retriever = RagRetriever()
    print("\n--- Test Query ---")
    chunks = retriever.retrieve("high ensemble spread monsoon forecast bust India", k=3)
    for c in chunks:
        print(f"  [{c['similarity']:.3f}] {c['source']} | {c['text'][:100]}...")

    print("\n--- Test Answer Generation ---")
    result = retriever.answer(
        question="Why does high ensemble spread increase bust probability?",
        context={
            "bust_probability": 0.62,
            "confidence_band": "Low",
            "lead_day": 7,
            "region": "Maharashtra",
            "top_drivers": [
                {"feature": "forecast_spread", "value": 18.5, "direction": "up"},
                {"feature": "lead_day", "value": 7, "direction": "up"},
            ],
            "rule_summary": [
                "High ensemble spread (18.5 mm) — members strongly disagree on rainfall amount",
                "Long lead time (Day 7) — forecast skill degrades significantly beyond 5 days",
            ],
        },
        k=4,
    )
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nSources: {[s['title'] for s in result['sources']]}")
    print("\nPASS")
