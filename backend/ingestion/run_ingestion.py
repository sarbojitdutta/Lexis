import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import time
from config import DATA_RAW, DATA_PROCESSED, FAISS_META

# Check which PDFs are already ingested

def _get_already_ingested() -> set[str]:
    """
    Check FAISS metadata to find which PDF
    files have already been ingested.
    Returns a set of filenames.
    """
    if not FAISS_META.exists():
        return set()

    with open(FAISS_META, encoding="utf-8") as f:
        meta = json.load(f)

    return set(m.get("source", "") for m in meta)

# Single document pipeline

def ingest_one(pdf_path: Path) -> dict:
    """
    Run the complete offline pipeline for
    a single PDF file:

    parse → chunk → embed → extract → build graph

    Returns a summary dict of what was processed.
    """
    from ingestion.parser   import parse_document
    from ingestion.chunker  import chunk_document
    from ingestion.embedder import ingest_chunks
    from graph.extractor    import extract_all
    from graph.builder      import build_graph

    print(f"\n{'='*55}")
    print(f" Processing: {pdf_path.name}")
    print(f"{'='*55}")

    start_time = time.time()

    # ── Step 1 — Parse ──
    print("\n[1/5] Parsing PDF...")
    sections = parse_document(pdf_path)
    print(f"      {len(sections)} sections extracted")

    if not sections:
        print(f"      Warning: no sections found — skipping")
        return {
            "file"    : pdf_path.name,
            "status"  : "skipped",
            "reason"  : "no sections extracted",
            "sections": 0,
            "chunks"  : 0,
            "nodes"   : 0,
            "edges"   : 0,
            "time"    : 0,
        }

    # ── Step 2 — Chunk ──
    print("\n[2/5] Chunking sections...")
    chunks = chunk_document(sections)
    print(f"      {len(chunks)} chunks created")

    # ── Step 3 — Embed ──
    print("\n[3/5] Embedding chunks into FAISS...")
    ingest_chunks(chunks)

    # ── Step 4 — Extract SAT triples ──
    print("\n[4/5] Extracting SAT triples via LLM...")
    print(f"      This may take a few minutes...")
    sat_results = extract_all(sections, delay=1.5)

    # ── Step 5 — Build graph ──
    print("\n[5/5] Building SAT graph...")
    G = build_graph(sections, sat_results)

    elapsed = round(time.time() - start_time, 1)

    return {
        "file"    : pdf_path.name,
        "status"  : "success",
        "sections": len(sections),
        "chunks"  : len(chunks),
        "nodes"   : G.number_of_nodes(),
        "edges"   : G.number_of_edges(),
        "time"    : elapsed,
    }


# Full pipeline — all PDFs in data/raw/


def run_all() -> None:
    """
    Run the ingestion pipeline for all PDFs
    in data/raw/ that have not been ingested yet.

    Safe to run multiple times — already ingested
    files are automatically skipped.
    """
    pdf_files = sorted(DATA_RAW.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in '{DATA_RAW}'")
        print("Drop your PDF files into data/raw/ and run again.")
        return

    # Check which are already done
    already_done = _get_already_ingested()
    pending      = [
        p for p in pdf_files
        if p.name not in already_done
    ]
    skipped      = [
        p for p in pdf_files
        if p.name in already_done
    ]

    print(f"\nLexis — Legal SAT Graph RAG")
    print(f"{'='*55}")
    print(f"PDFs found    : {len(pdf_files)}")
    print(f"Already done  : {len(skipped)}")
    print(f"To process    : {len(pending)}")

    if skipped:
        print(f"\nSkipping already ingested:")
        for p in skipped:
            print(f"  ✓ {p.name}")

    if not pending:
        print("\nAll PDFs already ingested. Nothing to do.")
        print("To re-ingest a file delete it from db/ and run again.")
        return

    print(f"\nProcessing {len(pending)} new file(s)...")

    # ── Process each pending PDF ──
    results  = []
    total_start = time.time()

    for i, pdf_path in enumerate(pending):
        print(f"\n[{i+1}/{len(pending)}] {pdf_path.name}")
        try:
            result = ingest_one(pdf_path)
            results.append(result)
        except Exception as e:
            print(f"  Error processing {pdf_path.name}: {e}")
            results.append({
                "file"    : pdf_path.name,
                "status"  : "failed",
                "reason"  : str(e),
                "sections": 0,
                "chunks"  : 0,
                "nodes"   : 0,
                "edges"   : 0,
                "time"    : 0,
            })

    total_elapsed = round(time.time() - total_start, 1)

    # ── Final summary ──
    _print_summary(results, total_elapsed)


# ─────────────────────────────────────────────
# Summary printer
# ─────────────────────────────────────────────

def _print_summary(results: list[dict],
                   total_time: float) -> None:

    print(f"\n\n{'='*55}")
    print(f" INGESTION COMPLETE")
    print(f"{'='*55}")

    successful = [r for r in results if r["status"] == "success"]
    failed     = [r for r in results if r["status"] == "failed"]
    skipped    = [r for r in results if r["status"] == "skipped"]

    print(f"\nResults:")
    print(f"  Successful : {len(successful)}")
    print(f"  Failed     : {len(failed)}")
    print(f"  Skipped    : {len(skipped)}")
    print(f"  Total time : {total_time}s")

    if successful:
        print(f"\nSuccessfully ingested:")
        total_sections = 0
        total_chunks   = 0
        total_nodes    = 0
        total_edges    = 0

        for r in successful:
            print(f"  ✓ {r['file']}")
            print(f"      sections : {r['sections']}")
            print(f"      chunks   : {r['chunks']}")
            print(f"      nodes    : {r['nodes']}")
            print(f"      edges    : {r['edges']}")
            print(f"      time     : {r['time']}s")
            total_sections += r["sections"]
            total_chunks   += r["chunks"]
            total_nodes    += r["nodes"]
            total_edges    += r["edges"]

        print(f"\nTotals across all documents:")
        print(f"  Sections : {total_sections}")
        print(f"  Chunks   : {total_chunks}")
        print(f"  Nodes    : {total_nodes}")
        print(f"  Edges    : {total_edges}")

    if failed:
        print(f"\nFailed:")
        for r in failed:
            print(f"  ✗ {r['file']} — {r.get('reason', 'unknown error')}")

    print(f"\nNext step:")
    print(f"  Start the API server:")
    print(f"  uvicorn api.main:app --reload --port 8000")
    print()


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    run_all()