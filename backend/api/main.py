import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import faiss
import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import importlib
import logging

from api.routes  import query, documents, graphs, auth
from config      import FAISS_INDEX, GRAPH_DB
from llm.client  import check_llm_connection

app = FastAPI(
    title       = "Lexis — Legal SAT Graph RAG",
    description = "AI-powered Indian legal document search and Q&A",
    version     = "0.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins     = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://lexis-puce.vercel.app",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers     = ["*"],
    allow_credentials = True,
)

# Register routes
app.include_router(query.router,     prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(graphs.router,     prefix="/api")
app.include_router(auth.router, prefix="/api")


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

@app.get("/api/health")
@app.head("/api/health")
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

@app.get("/api/debug-env")
def debug_env():
    import os
    return {
        "JWT_SECRET_SET"    : bool(os.getenv("JWT_SECRET")),
        "JWT_SECRET_LENGTH" : len(os.getenv("JWT_SECRET", "")),
        "GROQ_KEY_SET"      : bool(os.getenv("GROQ_API_KEY")),
        "GOOGLE_ID_SET"     : bool(os.getenv("GOOGLE_CLIENT_ID")),
        "REDIRECT_URI"      : os.getenv("GOOGLE_REDIRECT_URI"),
        "FRONTEND_URL"      : os.getenv("FRONTEND_URL"),
    }

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)