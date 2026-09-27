"""
src/rag/ingest.py
=================
Task 1 (RAG) — Corpus ingestion, chunking, embedding, FAISS index construction.

Usage:
    python -m src.rag.ingest

Reads all .txt files from rag_corpus/, chunks them into 200-400 token excerpts,
embeds with sentence-transformers (all-MiniLM-L6-v2), and writes a FAISS index
+ chunk metadata JSON to rag_store/.
"""

import os
import sys
import json
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORPUS_DIR = os.path.join(ROOT_DIR, "rag_corpus")
STORE_DIR  = os.path.join(ROOT_DIR, "rag_store")

CHUNK_TOKEN_TARGET = 300  # ~300 tokens per chunk
CHUNK_OVERLAP_CHARS = 200  # ~15% overlap


def simple_sentence_split(text: str) -> list:
    """Split text into sentences using simple heuristics."""
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip()]


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def chunk_document(doc_path: str) -> list:
    """
    Parse a corpus document and chunk it into 200-400 token segments.
    Each chunk carries source metadata from the document header.
    Returns list of chunk dicts.
    """
    with open(doc_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Parse header metadata
    source = ""
    citation = ""
    url = ""
    section = ""
    
    lines = raw.split("\n")
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("SOURCE:"):
            source = line[len("SOURCE:"):].strip()
        elif line.startswith("CITATION:"):
            citation = line[len("CITATION:"):].strip()
        elif line.startswith("URL:"):
            url = line[len("URL:"):].strip()
        elif line.startswith("SECTION:"):
            section = line[len("SECTION:"):].strip()
        elif line.strip() == "---":
            body_start = i + 1
            break

    body = "\n".join(lines[body_start:]).strip()
    doc_id = os.path.splitext(os.path.basename(doc_path))[0]

    # Split body into paragraphs first
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""
    current_tokens = 0
    chunk_idx = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        
        # If a single paragraph exceeds limit, split further
        if para_tokens > 450:
            sentences = simple_sentence_split(para)
            for sent in sentences:
                sent_tokens = estimate_tokens(sent)
                if current_tokens + sent_tokens > 400 and current_chunk:
                    # Emit current chunk
                    chunks.append({
                        "chunk_id": f"{doc_id}_chunk{chunk_idx}",
                        "doc_id": doc_id,
                        "source": source,
                        "citation": citation,
                        "url": url,
                        "section": section,
                        "text": current_chunk.strip(),
                        "approx_tokens": current_tokens,
                    })
                    chunk_idx += 1
                    # Start new chunk with overlap
                    overlap_text = current_chunk[-CHUNK_OVERLAP_CHARS:] if len(current_chunk) > CHUNK_OVERLAP_CHARS else ""
                    current_chunk = overlap_text + " " + sent
                    current_tokens = estimate_tokens(current_chunk)
                else:
                    current_chunk += " " + sent
                    current_tokens += sent_tokens
        else:
            if current_tokens + para_tokens > 400 and current_chunk:
                # Emit current chunk
                chunks.append({
                    "chunk_id": f"{doc_id}_chunk{chunk_idx}",
                    "doc_id": doc_id,
                    "source": source,
                    "citation": citation,
                    "url": url,
                    "section": section,
                    "text": current_chunk.strip(),
                    "approx_tokens": current_tokens,
                })
                chunk_idx += 1
                overlap_text = current_chunk[-CHUNK_OVERLAP_CHARS:] if len(current_chunk) > CHUNK_OVERLAP_CHARS else ""
                current_chunk = overlap_text + "\n\n" + para
                current_tokens = estimate_tokens(current_chunk)
            else:
                current_chunk += "\n\n" + para
                current_tokens += para_tokens

    # Emit final chunk
    if current_chunk.strip():
        chunks.append({
            "chunk_id": f"{doc_id}_chunk{chunk_idx}",
            "doc_id": doc_id,
            "source": source,
            "citation": citation,
            "url": url,
            "section": section,
            "text": current_chunk.strip(),
            "approx_tokens": current_tokens,
        })

    return chunks


def build_index():
    """Main function: ingest corpus, embed, build FAISS index."""
    print("=" * 60)
    print("RAG INGEST — Building FAISS Index")
    print("=" * 60)

    os.makedirs(STORE_DIR, exist_ok=True)

    # 1. Chunk all documents
    doc_files = sorted([
        os.path.join(CORPUS_DIR, f)
        for f in os.listdir(CORPUS_DIR)
        if f.endswith(".txt")
    ])
    
    if not doc_files:
        print(f"ERROR: No .txt files found in {CORPUS_DIR}")
        sys.exit(1)
    
    print(f"\nFound {len(doc_files)} corpus documents.")
    
    all_chunks = []
    for doc_path in doc_files:
        chunks = chunk_document(doc_path)
        print(f"  {os.path.basename(doc_path)}: {len(chunks)} chunks")
        all_chunks.extend(chunks)
    
    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Avg tokens/chunk: {sum(c['approx_tokens'] for c in all_chunks) / len(all_chunks):.0f}")

    # 2. Embed with sentence-transformers
    print("\nLoading sentence-transformer model (all-MiniLM-L6-v2)...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    texts = [c["text"] for c in all_chunks]
    print(f"Embedding {len(texts)} chunks...")
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=True, convert_to_numpy=True)
    print(f"Embedding shape: {embeddings.shape}")

    # 3. Build FAISS index
    print("\nBuilding FAISS index (IndexFlatL2)...")
    import faiss
    import numpy as np
    
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)  # Flat L2 — exact search, no training needed
    
    # Normalize for cosine similarity (L2 normalize → L2 distance = cosine distance)
    faiss.normalize_L2(embeddings)
    index.add(embeddings.astype(np.float32))
    
    print(f"Index total vectors: {index.ntotal}")

    # 4. Save index + metadata
    index_path = os.path.join(STORE_DIR, "faiss_index.bin")
    chunks_path = os.path.join(STORE_DIR, "chunks.json")
    
    faiss.write_index(index, index_path)
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    
    # Also save embed model info
    meta = {
        "embed_model": "all-MiniLM-L6-v2",
        "embed_dim": dim,
        "total_chunks": len(all_chunks),
        "n_documents": len(doc_files),
        "normalized": True,
    }
    with open(os.path.join(STORE_DIR, "index_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"\nSaved:")
    print(f"  FAISS index -> {index_path}")
    print(f"  Chunk store -> {chunks_path}")
    print(f"  Metadata   -> {os.path.join(STORE_DIR, 'index_meta.json')}")
    print("\nPASS — RAG index built successfully.")
    return all_chunks, embeddings


if __name__ == "__main__":
    build_index()
