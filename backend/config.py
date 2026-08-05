import os
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.3-70b-versatile"
BASE_DIR = Path(__file__).parent
DATA_RAW = BASE_DIR / "data/raw"
DATA_PROCESSED = BASE_DIR / "data/processed"
FAISS_INDEX = BASE_DIR / "db/faiss/legal.index"
FAISS_META = BASE_DIR / "db/faiss/legal_meta.json"
GRAPH_DB = BASE_DIR / "db/graph/graph.db"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K_VECTOR = 4
TOP_K_GRAPH = 6
MAX_VECTOR = 3000
MAX_CONTEXT = 1200