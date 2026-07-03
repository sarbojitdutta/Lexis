import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import DATA_PROCESSED, FAISS_INDEX, FAISS_META, EMBEDDING_MODEL

print("Loading Embedding Model...")
model = SentenceTransformer(EMBEDDING_MODEL)
DIM = model.get_embedding_dimension()
print(f"Embedding dimension: {DIM}")

def _load_or_create_index() -> tuple[faiss.Index, list]:
    """
    Load existing FAISS index and metadata from disk
    if they exist, otherwise create fresh ones.
    This allows incremental ingestion — running embedder
    again with a new document adds to the existing index
    rather than overwriting it.
    """

    if FAISS_INDEX.exists() and FAISS_META.exists():
        print("Existing index found -loading...")
        index = faiss.read_index(str(FAISS_INDEX))
        with open(FAISS_META, encoding="utf-8") as f:
            meta = json.load(f)
        print(f"Loaded index with {index.ntotal} existing vectors")
        return index, meta
    
    print("No existing index — creating fresh...")
    index = faiss.IndexFlatIP(DIM)
    return index, []

def _save_index(index: faiss.Index, meta: list):
    """
    Persist FAISS index and metadata sidecar to disk.
    """
    FAISS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX))
    with open(FAISS_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Index saved — total vectors: {index.ntotal}")
    print(f"  Index : {FAISS_INDEX}")
    print(f"  Meta  : {FAISS_META}")


def _already_registered(meta: list, source: str) -> bool:
    """
    Check if chunks from this source document are already
    in the index. Prevents duplicate embeddings if you
    accidentally run embedder twice on the same file.
    """
    return any(m["source"] == source for m in meta)

def embed_chunks(chunks: list[dict], batch_size: int = 8) -> np.ndarray:
    """
    Generate normalized embeddings for a list of chunks.
    Batching keeps RAM usage flat — only batch_size chunks
    are in memory at once rather than all at once.

    normalize_embeddings=True is required for IndexFlatIP
    to behave as cosine similarity search.

    batch_size=8 is conservative for 4GB RAM — increase to
    16 or 32 if you have headroom.
    """
    texts = [chunk["text"] for chunk in chunks]

    print(f"Embedding {len(texts)} chunks "
          f"in batches of {batch_size}...")

    embeddings = model.encode(
        texts,
        batch_size          = batch_size,
        normalize_embeddings= True,
        show_progress_bar   = True,
        convert_to_numpy    = True,
    )
    return embeddings.astype("float32")


def _build_meta_entries(chunks: list[dict]) -> list[dict]:
    """
    For each chunk store lightweight metadata in the sidecar.
    We don't store the full text in FAISS (it only stores vectors)
    so this sidecar is what we look up after a search to get
    the actual text and metadata back.
    """

    return [
        {
            "chunk_id"        : chunk["chunk_id"],
            "section_id"      : chunk["section_id"],
            "chunk_index"     : chunk["chunk_index"],
            "total_chunks"    : chunk["total_chunks"],
            "text"            : chunk["text"],
            "title"           : chunk["title"],
            "source"          : chunk["source"],
            "part"            : chunk["part"],
            "chapter"         : chunk["chapter"],
            "has_proviso"     : chunk["has_proviso"],
            "has_exception"   : chunk["has_exception"],
            "has_definition"  : chunk["has_definition"],
            "has_amendment"   : chunk["has_amendment"],
            "cross_references": chunk["cross_references"],
        }
        for chunk in chunks
    ]
    

def ingest_chunks(chunks: list[dict]) -> None:
    """
    Embed a list of chunks and add them to the FAISS index.
    Skips if the source document is already in the index.
    """

    if not chunks:
        print("No chunks to ingest.")
        return
    
    source = chunks[0]["source"]
    index, meta = _load_or_create_index()

    if _already_registered(meta, source):
        print(f"Skipping '{source}' — already in index.")
        return
    
    embedding = embed_chunks(chunks)
    meta_entries = _build_meta_entries(chunks)

    index.add(embedding)
    meta.extend(meta_entries)
    _save_index(index, meta)
    print(f"Added {len(chunks)} chunks from '{source}' to index.")

def search(query: str, k: int = 4) -> list[dict]:
    """
    Embed a query and return top-k matching chunks
    with their similarity scores.

    This function is imported and used by
    retrieval/vector_search.py — not called during ingestion.
    """
     
    if not FAISS_INDEX.exists():
        raise FileNotFoundError("FAISS index not found. Run embedder.py first.")
    
    index = faiss.read_index(str(FAISS_INDEX))
    with open(FAISS_META, encoding="utf-8") as f:
        meta = json.load(f)

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True
    ).astype("float32")

    scores, indices = index.search(query_embedding, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        entry = meta[idx].copy()
        entry["score"] = float(score)
        results.append(entry)

    return results


if __name__ == "__main__":
    from chunker import chunk_from_file

    processed_dir = DATA_PROCESSED
    json_files    = list(processed_dir.glob("*.json"))

    if not json_files:
        print(f"No processed JSON files found in '{processed_dir}'.")
        print("Run parser.py first.")
        sys.exit(0)

    print(f"Found {len(json_files)} processed file(s):\n")

    for json_path in json_files:
        print(f"Processing '{json_path.name}'...")
        chunks = chunk_from_file(json_path)
        ingest_chunks(chunks)
        print()

    # Quick search test to verify index works
    print("--- Running test search ---\n")
    test_query   = "capacity to contract"
    results      = search(test_query, k=3)

    print(f"Query : '{test_query}'")
    print(f"Top {len(results)} results:\n")
    for r in results:
        print(f"  score      : {r['score']:.4f}")
        print(f"  section_id : {r['section_id']}")
        print(f"  title      : {r['title']}")
        print(f"  text       : {r['text'][:120]}...")
        print()