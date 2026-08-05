import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import json
import sqlite3
from fastapi      import APIRouter, HTTPException, BackgroundTasks
from api.schemas  import (
    IngestRequest, IngestResponse,
    DocumentListResponse, DocumentInfo
)
from config       import DATA_RAW, DATA_PROCESSED, GRAPH_DB, FAISS_META

router = APIRouter()


# ─────────────────────────────────────────────
# GET /api/documents
# ─────────────────────────────────────────────

@router.get("/documents", response_model=DocumentListResponse)
def list_documents():
    """
    List all ingested documents with their
    section and chunk counts.
    """
    processed_files = list(DATA_PROCESSED.glob("*.json"))

    if not processed_files:
        return DocumentListResponse(
            documents    = [],
            total_chunks = 0
        )

    documents    = []
    total_chunks = 0

    for json_path in processed_files:
        try:
            with open(json_path) as f:
                sections = json.load(f)

            # Count chunks from FAISS meta
            chunk_count = 0
            if FAISS_META.exists():
                with open(FAISS_META) as f:
                    meta = json.load(f)
                chunk_count = sum(
                    1 for m in meta
                    if m.get("source", "").startswith(
                        json_path.stem
                    )
                )

            documents.append(DocumentInfo(
                filename     = json_path.stem + ".pdf",
                section_count= len(sections),
                chunk_count  = chunk_count,
                status       = "ingested"
            ))
            total_chunks += chunk_count

        except Exception:
            documents.append(DocumentInfo(
                filename     = json_path.stem + ".pdf",
                section_count= 0,
                chunk_count  = 0,
                status       = "error"
            ))

    return DocumentListResponse(
        documents    = documents,
        total_chunks = total_chunks
    )


# ─────────────────────────────────────────────
# POST /api/ingest
# ─────────────────────────────────────────────

def _run_ingestion(filename: str) -> dict:
    """
    Run the full ingestion pipeline for one PDF.
    Called in background so API does not timeout.
    """
    import json as _json
    from ingestion.parser   import parse_document
    from ingestion.chunker  import chunk_document
    from ingestion.embedder import ingest_chunks
    from graph.extractor    import extract_all
    from graph.builder      import build_graph, graph_stats

    pdf_path = DATA_RAW / filename

    # Parse
    sections = parse_document(pdf_path)

    # Chunk
    chunks = chunk_document(sections)

    # Embed into FAISS
    ingest_chunks(chunks)

    # Extract SAT triples
    sat_results = extract_all(sections, delay=0.5)

    # Build graph
    build_graph(sections, sat_results)

    # Stats
    stats = graph_stats()

    return {
        "sections"   : len(sections),
        "chunks"     : len(chunks),
        "graph_nodes": stats.get("nodes", 0),
        "graph_edges": stats.get("edges", 0),
    }


@router.post("/ingest", response_model=IngestResponse)
def ingest_document(request: IngestRequest,
                    background_tasks: BackgroundTasks):
    """
    Trigger ingestion of a PDF from data/raw/.
    Runs ingestion in background so request
    does not timeout on large documents.
    """
    pdf_path = DATA_RAW / request.filename

    if not pdf_path.exists():
        raise HTTPException(
            status_code = 404,
            detail      = f"File '{request.filename}' not found "
                          f"in data/raw/ folder."
        )

    if not request.filename.endswith(".pdf"):
        raise HTTPException(
            status_code = 400,
            detail      = "Only PDF files are supported."
        )

    try:
        result = _run_ingestion(request.filename)

        # Reload FAISS index after ingestion
        from retrieval import vector_search
        import importlib
        importlib.reload(vector_search)

        return IngestResponse(
            filename    = request.filename,
            sections    = result["sections"],
            chunks      = result["chunks"],
            graph_nodes = result["graph_nodes"],
            graph_edges = result["graph_edges"],
            status      = "success",
            message     = f"Successfully ingested {request.filename}"
        )

    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail      = f"Ingestion failed: {str(e)}"
        )