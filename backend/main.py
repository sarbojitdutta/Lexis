# backend/api/main.py
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title       = "Lexis — Legal SAT Graph RAG",
    description = "AI-powered Indian legal document search and Q&A",
    version     = "0.1.0"
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins     = [
        FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_methods     = ["*"],
    allow_headers     = ["*"],
    allow_credentials = True,
)


@app.get("/api/health")
def health():
    return {"status": "ok", "project": "Lexis"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)