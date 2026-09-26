# RAG_BIBLE.md — Meteorological Knowledge RAG Layer

Legend: **[FACT]** · **[ASSUMPTION]** · **[RECOMMENDATION]** · **[OPTION]**

---

## 1. Purpose and Boundaries (read this first)

The RAG system's **only** job is to *explain*, in grounded and cited meteorological language, the drivers that the ML model has already identified (SHAP top features + rule-based summary). It must never:
- Generate a bust probability, confidence score, or any number — those come only from the ML model.
- Invent a historical event, statistic, or forecast outcome not present in our own data or in retrieved documents.
- Override, contradict, or "improve" a model output.
- Claim causal certainty ("this caused the bust") when the evidence is correlational — it should use hedged, verification-science-appropriate language ("historically associated with," "consistent with known predictability limits during...").

**Architecture, restated precisely:**
```
ML model → top SHAP drivers + rule-based summary (structured JSON)
     ↓
Retriever → fetches relevant chunks from the curated meteorological corpus,
            using the driver names/values as the query
     ↓
LLM (generation) → writes a short explanation using ONLY retrieved chunks + the
                    structured driver JSON as context, with inline citations
     ↓
Dashboard shows: explanation text + citation list (source, section)
```

## 2. Corpus Design

**[RECOMMENDATION]** Keep the corpus small, curated, and high-signal — 15–30 documents is enough for a 3-day MVP; a huge indiscriminate scrape both wastes build time and increases hallucination/irrelevant-retrieval risk.

**Candidate sources [FACT — publicly available meteorological documentation]:**
- IMD public documentation on monsoon behaviour, forecast products, and terminology (IMD's own site/press releases/annual monsoon reports).
- WMO guidance on forecast verification concepts and terminology (WMO publishes public verification methodology guidance).
- ECMWF public documentation on medium-range forecast skill, ensemble spread, and predictability (ECMWF publishes public technical memoranda and user guides, several of which were consulted directly for this project — see DATA_STRATEGY.md).
- NOAA/NWS public explainers on forecast uncertainty, western-disturbance-equivalent frontal systems, and monsoon/heat-wave background (for general predictability-science context, used carefully since NOAA content is US-centric).
- A small number of peer-reviewed or widely cited papers/technical notes on medium-range forecast bust behaviour, monsoon depression predictability, and western disturbance interaction with orography (retrieved and their abstracts/key sections chunked — never full-text reproduced verbatim beyond fair, short paraphrased excerpts, consistent with copyright practice).
- Our own generated **model documentation** (MODEL_METHODOLOGY.md's definitions section) — included in the corpus so the RAG layer can correctly explain *our own* bust/confidence definitions, not just generic meteorology.

**[ASSUMPTION]** Exact document list is finalized during Task 15, prioritizing documents that answer the specific driver types our feature set actually produces (forecast revision volatility, spatial disagreement, lead-time degradation, seasonal/monsoon context) rather than trying to cover all of meteorology.

## 3. Ingestion & Chunking

**[RECOMMENDATION]**
- Chunk size: ~200–400 tokens per chunk, with light overlap (~15%), split on natural section/paragraph boundaries rather than fixed character counts where the source has clear structure (PDF headings, HTML sections).
- Each chunk stores: source title, source URL/citation, section heading (if available), and the chunk text.
- No OCR pipeline needed if all sources are digital-native text/HTML/PDF-with-text-layer; if a scanned PDF sneaks in, drop it rather than build OCR infrastructure for a 3-day sprint.

## 4. Embedding & Vector Store

**[RECOMMENDATION]** Given the compute/hardware constraint (no expensive GPU, local-first):
- Embeddings: a lightweight, free, locally-runnable sentence-embedding model (e.g., a small `sentence-transformers` model such as `all-MiniLM-L6-v2`), which runs comfortably on CPU for a corpus of this size.
- Vector store: **FAISS** (pure local, no server, trivial to set up) or **Chroma** if the agent workflow benefits from its slightly higher-level API — either is fine; **[RECOMMENDATION]** default to FAISS for minimal dependency footprint.
- **[OPTION]** A hosted embedding API (e.g., via the Anthropic/OpenAI embedding endpoints) is viable if local embedding setup proves troublesome, but adds an external dependency and a cost/rate-limit surface we'd rather avoid for a demo that must work reliably during judging.

## 5. Retrieval

**[RECOMMENDATION]** Simple top-k dense retrieval (k = 3–5 chunks) using the SHAP driver names/values (converted into a short natural-language query, e.g., "high spatial disagreement between neighboring grid forecasts during monsoon season") as the query. A light keyword/metadata filter (e.g., prefer chunks tagged "monsoon" when the current month is June–September) is a reasonable, low-cost precision boost — full hybrid BM25+dense search is a nice-to-have, not required for MVP.

## 6. Answer Generation & Prompting

**[RECOMMENDATION]** The generation prompt structure:
```
System: You explain forecast reliability results using ONLY the retrieved
context and the structured model output provided. Never state a probability
or number not present in the structured model output. Never invent events,
statistics, or historical outcomes. If retrieved context does not support a
claim, omit the claim rather than guess. Always cite the source of any
meteorological claim using the provided source titles.

Context: <retrieved chunks with source labels>
Model output: <structured JSON: top SHAP drivers, rule-based summary,
               bust probability, confidence band, region, lead time>

Task: Write a 3-5 sentence explanation, in plain operational language, of
why this forecast has {confidence band} confidence, grounded in the
provided context, citing sources inline as [Source Name].
```

## 7. Citation System

Every substantive RAG answer must show, alongside the generated text, a short reference list (source title + link/identifier) for each chunk actually used, mirroring the citation discipline used throughout this planning document set. The dashboard's RAG panel renders these as clickable/visible source chips beneath the explanation text.

## 8. Hallucination Controls

**[RECOMMENDATION, layered defenses]**:
1. **Grounding constraint in the prompt** (above) — explicit "don't invent" instruction.
2. **Structured-output check**: any number appearing in the RAG answer is programmatically checked against the structured model-output JSON before display; if the LLM emits a number not present in that JSON, the answer is regenerated with a stricter instruction or the numeric claim is stripped.
3. **Retrieval-empty fallback**: if retrieval returns no chunk above a similarity threshold, the RAG layer returns the rule-based/SHAP explanation only, with a note that no additional literature context was found — it does not force a citation-free generic answer.
4. **No RAG-only demo claims**: nothing the RAG layer says is ever used, by itself, as evidence of model quality in the PPT — only Section 9/§Evaluation numbers from MODEL_METHODOLOGY.md are used for accuracy claims.

## 9. Context Injection From Model Outputs

The retriever and generator both receive the **exact same structured JSON** the dashboard's "Why is confidence low?" panel renders (bust probability, confidence band, SHAP top-3 features with their direction/magnitude, region name, lead time, date) — this is the single source of truth passed into the RAG call, preventing any drift between what the dashboard numerically shows and what the RAG text narratively claims.

## 10. Evaluation of the RAG Layer

**[RECOMMENDATION]** Lightweight but real: assemble ~10 representative test questions/scenarios spanning the driver types our features actually produce (high revision volatility, high spatial disagreement, long lead time, monsoon-season context, etc.), and manually check each RAG answer for (a) correct citation presence, (b) no invented numbers, (c) meteorological plausibility. This is a qualitative but genuine check, appropriately scoped for a 3-day build — a full RAG-eval framework (RAGAS-style automated scoring) is documented as a Tier-3 future step, not built now.

## 11. What RAG Can and Cannot Claim — Summary Table

| Can claim | Cannot claim |
|---|---|
| "Historical documentation notes that western disturbance interaction with the Himalayan terrain is associated with rapid, hard-to-predict rainfall intensification [Source]." | "This forecast will bust with 69% probability" (only the ML model states this — RAG may *repeat* the model's own number, never generate a new one) |
| "High disagreement between neighboring grid-point forecasts is a recognized signature of frontal/convective uncertainty [Source]." | "This specific event is definitely a monsoon depression" (regime classification is not built in the MVP — RAG must not assert a regime label the model didn't produce) |
| "Forecast skill for medium-range rainfall is well documented to degrade with lead time [Source]." | Any statistic, date, or number not traceable to either the retrieved corpus or the structured model-output JSON |
