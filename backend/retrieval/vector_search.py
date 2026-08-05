
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from config import FAISS_INDEX, FAISS_META, EMBEDDING_MODEL

print("Loading embedding model...")
model = SentenceTransformer(EMBEDDING_MODEL)
print("Embedding model loaded.")

def _load_index() -> tuple[faiss.Index, list]:
    """
    Load FAISS index and metadata sidecar from disk.
    Called once at module level.
    """
    if not FAISS_INDEX.exists():
        raise FileNotFoundError(
            f"FAISS index not found at {FAISS_INDEX}. "
            f"Run embedder.py first."
        )
    if not FAISS_META.exists():
        raise FileNotFoundError(
            f"Metadata not found at {FAISS_META}. "
            f"Run embedder.py first."
        )

    index = faiss.read_index(str(FAISS_INDEX))
    with open(FAISS_META, encoding="utf-8") as f:
        meta = json.load(f)

    print(f"FAISS index loaded — {index.ntotal} vectors")
    return index, meta


try:
    index, meta = _load_index()
except FileNotFoundError as e:
    print(f"Warning: {e}")
    index = None
    meta  = []



def search(query: str, k: int = 4) -> list[dict]:
    """
    Embed a query and return top-k matching chunks
    from the FAISS index.

    Each result contains:
    - chunk_id
    - section_id
    - text
    - title
    - source
    - score (cosine similarity 0-1, higher is better)
    - has_exception, has_proviso etc.
    - cross_references
    """
    if index is None or index.ntotal == 0:
        print("Vector search unavailable — index not loaded.")
        return []

    # Embed the query using same model used during ingestion
    query_embedding = model.encode(
        [query],
        normalize_embeddings = True,
        convert_to_numpy     = True,
    ).astype("float32")

    # Search FAISS index
    scores, indices = index.search(query_embedding, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        # idx == -1 means FAISS found fewer than k results
        if idx == -1 or idx >= len(meta):
            continue

        entry         = meta[idx].copy()
        entry["score"] = float(score)
        results.append(entry)

    return results

def get_section_ids(query: str, k: int = 4) -> list[str]:
    """
    Convenience function that returns only the
    section IDs from vector search results.

    Used by graph_search.py to know which sections
    to expand via graph traversal.
    """
    results = search(query, k=k)
    seen    = set()
    ids     = []

    for r in results:
        sid = r.get("section_id", "")
        if sid and sid not in seen:
            seen.add(sid)
            ids.append(sid)

    return ids


def reload():
    global index, meta
    index, meta = _load_index()
    print(f"Index reloaded — {index.ntotal} vectors")


if __name__ == "__main__":

    test_queries = [
        "What is a contract",
        "free consent and coercion",
        "breach of contract compensation",
        "capacity to contract minor",
        "void agreement consideration",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)

        results = search(query, k=3)

        if not results:
            print("  No results found.")
            continue

        for i, r in enumerate(results):
            print(f"  [{i+1}] Score      : {r['score']:.4f}")
            print(f"       Section    : {r['section_id']} — {r['title']}")
            print(f"       Text       : {r['text'][:100]}...")
            print(f"       Exception  : {r.get('has_exception', False)}")
            print(f"       Cross-refs : {r.get('cross_references', [])}")
            print()

    print("\n--- Section IDs for 'free consent' ---")
    ids = get_section_ids("free consent", k=4)
    print(f"Section IDs: {ids}")