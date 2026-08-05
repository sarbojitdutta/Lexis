import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import faiss
import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import importlib

from api.routes  import query, documents, graphs
from config      import FAISS_INDEX, GRAPH_DB
from llm.client  import check_llm_connection

app = FastAPI(
    title       = "Lexis — Legal SAT Graph RAG",
    description = "AI-powered Indian legal document search and Q&A",
    version     = "0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000"],
    allow_methods     = ["*"],
    allow_headers     = ["*"],
    allow_credentials = True,
)

# Register routes
app.include_router(query.router,     prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(graphs.router,     prefix="/api")


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

@app.get("/api/health")
def health():
    # Vector index stats
    vector_status  = "not found"
    total_vectors  = 0
    if FAISS_INDEX.exists():
        idx           = faiss.read_index(str(FAISS_INDEX))
        total_vectors = idx.ntotal
        vector_status = "ready"

    # Graph stats
    graph_status = "not found"
    total_nodes  = 0
    total_edges  = 0
    if GRAPH_DB.exists():
        con         = sqlite3.connect(GRAPH_DB)
        total_nodes = con.execute(
            "SELECT COUNT(*) FROM nodes"
        ).fetchone()[0]
        total_edges = con.execute(
            "SELECT COUNT(*) FROM edges"
        ).fetchone()[0]
        con.close()
        graph_status = "ready"

    # LLM connection
    llm = check_llm_connection()

    return {
        "status"       : "ok",
        "project"      : "Lexis",
        "llm_status"   : llm["status"],
        "llm_model"    : llm["model"],
        "vector_index" : vector_status,
        "graph_db"     : graph_status,
        "total_vectors": total_vectors,
        "total_nodes"  : total_nodes,
        "total_edges"  : total_edges,
    }


# ─────────────────────────────────────────────
# Reload index
# ─────────────────────────────────────────────

@app.post("/api/reload")
def reload_index():
    from retrieval import vector_search
    importlib.reload(vector_search)
    return {"status": "index reloaded"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host   = "0.0.0.0",
        port   = 8000,
        reload = True
    )