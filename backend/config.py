import os
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.3-70b-versatile"

IS_RENDER = os.getenv("RENDER", False)


BASE_DIR = Path(__file__).resolve().parent
PERSIST_DIR = BASE_DIR
DATA_RAW = PERSIST_DIR / "data/raw"
DATA_PROCESSED = PERSIST_DIR / "data/processed"
FAISS_INDEX = PERSIST_DIR / "db/faiss/legal.index"
FAISS_META = PERSIST_DIR / "db/faiss/legal_meta.json"
GRAPH_DB = PERSIST_DIR / "db/graph/graph.db"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K_VECTOR = 4
TOP_K_GRAPH = 6
MAX_VECTOR = 3000
MAX_CONTEXT = 1200

#Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI")

#jwt
JWT_SECRET         = os.getenv("JWT_SECRET")
JWT_ALGORITHM      = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))