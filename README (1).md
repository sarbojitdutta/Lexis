# Lexis — Legal SAT Graph RAG

> AI-powered Indian legal document search and question answering, built on Structured Argument Tree (SAT) Graph Retrieval-Augmented Generation.

[![Regression Tests](https://github.com/sarbojitdutta/Lexis/actions/workflows/test.yml/badge.svg)](https://github.com/sarbojitdutta/Lexis/actions)
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://lexis-puce.vercel.app)

---

## What is Lexis

Most legal RAG systems do plain vector search — find sections that *sound similar* to your question. Lexis goes further by building a **Structured Argument Tree** on top of Indian legal documents, explicitly modeling how sections relate to each other — which ones override, qualify, define, or amend others.

When you ask a legal question, Lexis does not just find similar paragraphs. It follows the legal reasoning chain — main provision → conditions → exceptions → definitions — and gives you an answer that reflects how the law actually works.

---

## Live Demo

Frontend → [lexis-puce.vercel.app](https://lexis-puce.vercel.app)  


> Note: Backend is hosted on Render free tier and may take 30-60 seconds to wake up on first request.

---

## The Problem

Indian laws are publicly available on India Code but practically inaccessible. Finding a specific answer requires knowing which act, which section, and which clause is relevant. A layperson dealing with a contract dispute or tenant rights issue has no way to navigate this efficiently.

Existing legal search tools return sections that contain your search words. But legal reasoning does not work that way. A section means something different when read alongside the exception that overrides it, the definition that constrains it, and the amendment that modified it.

---

## How SAT Graph RAG Works

```
PDF Documents
      ↓
   Parser         →  extracts sections with metadata
      ↓
   Chunker        →  splits long sections into overlapping chunks
      ↓
   Embedder       →  generates 384-dim vectors → FAISS index
      ↓
   Extractor      →  LLM extracts SAT triples (claims, evidence, relations)
      ↓
   Graph Builder  →  builds NetworkX graph → persists to SQLite
```

**On every user query:**

```
Question
   ↓
Vector Search   →  finds semantically similar chunks (FAISS)
   ↓
Graph Search    →  follows edges to find exceptions, definitions, citations
   ↓
Merger          →  combines + deduplicates both result sets
   ↓
LLM             →  synthesizes answer with section citations (Groq API)
   ↓
Answer + Citations
```

---

## What Makes This Different from Plain RAG

| Capability | Plain RAG | Lexis SAT Graph RAG |
|---|---|---|
| Find similar sections | ✓ | ✓ |
| Find exception clauses | ✗ | ✓ via OVERRIDES edge |
| Find related definitions | ✗ | ✓ via DEFINES edge |
| Cross-section reasoning | ✗ | ✓ via graph traversal |
| Amendment awareness | ✗ | ✓ via AMENDS edge |
| Citation accuracy | sometimes | always grounded in source |

---

## Tech Stack

**Backend**

| Component | Technology |
|---|---|
| API framework | FastAPI |
| Vector store | FAISS (CPU) |
| Graph database | SQLite + NetworkX |
| Embeddings | all-MiniLM-L6-v2 |
| LLM | Groq API (Llama 3) |
| PDF parsing | pdfplumber |
| Authentication | Google OAuth 2.0 + JWT |

**Frontend**

| Component | Technology |
|---|---|
| Framework | React + Vite + TypeScript |
| UI components | shadcn/ui |
| Styling | Tailwind CSS v4 |
| HTTP client | Axios |
| Markdown | react-markdown |

**Infrastructure**

| Service | Platform |
|---|---|
| Frontend hosting | Vercel |
| Backend hosting | Render |
| Uptime monitoring | UptimeRobot |
| CI/CD | GitHub Actions |

---

## Project Structure

```
Lexis/
├── backend/
│   ├── ingestion/
│   │   ├── parser.py          # PDF → structured sections
│   │   ├── chunker.py         # sections → overlapping chunks
│   │   ├── embedder.py        # chunks → FAISS vectors
│   │   └── run_ingestion.py   # full offline pipeline entry point
│   ├── graph/
│   │   ├── schema.py          # node/edge type definitions
│   │   ├── extractor.py       # LLM → SAT triples
│   │   ├── builder.py         # triples → SQLite graph
│   │   └── retriever.py       # graph traversal queries
│   ├── retrieval/
│   │   ├── vector_search.py   # FAISS similarity search
│   │   ├── graph_search.py    # graph-based retrieval
│   │   └── merger.py          # combine + rank results
│   ├── llm/
│   │   ├── client.py          # Groq API wrapper
│   │   └── prompts.py         # prompt templates
│   ├── auth/
│   │   ├── oauth.py           # Google OAuth flow
│   │   ├── jwt.py             # JWT creation + verification
│   │   └── middleware.py      # route protection
│   ├── api/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── schemas.py         # Pydantic request/response models
│   │   └── routes/
│   │       ├── query.py       # POST /api/query
│   │       ├── documents.py   # document management
│   │       ├── graph.py       # graph inspection
│   │       └── auth.py        # authentication
│   ├── tests/
│   │   ├── conftest.py        # shared fixtures
│   │   ├── test_parser.py     # unit tests
│   │   ├── test_embedder.py   # unit tests
│   │   ├── test_retrieval.py  # integration tests
│   │   ├── test_api.py        # API endpoint tests
│   │   └── test_rag_quality.py # gold standard RAG tests
│   ├── config.py              # all paths and settings
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── Navbar.tsx
    │   │   ├── Sidebar.tsx
    │   │   ├── SearchBox.tsx
    │   │   ├── MessageList.tsx
    │   │   ├── MessageBubble.tsx
    │   │   └── Citations.tsx
    │   ├── lib/
    │   │   ├── api.ts          # backend API calls
    │   │   └── auth.ts         # OAuth + JWT handling
    │   └── App.tsx
    └── package.json
```

---

## Getting Started

### Prerequisites

```
Python 3.12+
Node.js 18+
Git
```

### 1 — Clone the repository

```bash
git clone https://github.com/sarbojitdutta/Lexis.git
cd Lexis
```

### 2 — Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate

pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback
JWT_SECRET=your_random_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080
FRONTEND_URL=http://localhost:5173
```

### 3 — Ingest legal documents

Drop PDF files into `backend/data/raw/` then run:

```bash
python3 ingestion/run_ingestion.py
```

This runs the full offline pipeline — parse, chunk, embed, extract SAT triples, build graph. Takes 3-5 minutes per document.

### 4 — Start the backend

```bash
uvicorn api.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

### 5 — Frontend setup

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

```bash
npm run dev
```

Visit `http://localhost:5173`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | System status and stats |
| POST | `/api/query` | Ask a legal question |
| GET | `/api/documents` | List ingested documents |
| POST | `/api/ingest` | Ingest a new PDF |
| GET | `/api/graph/node/{id}` | Get graph node and neighbours |
| GET | `/api/graph/stats` | Graph statistics |
| GET | `/api/auth/google` | Initiate Google OAuth |
| GET | `/api/auth/callback` | OAuth callback |
| GET | `/api/auth/me` | Current user info |

### Example query

```bash
curl -X POST https://lexis-1.onrender.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Can a minor enter into a contract?"}'
```

```json
{
  "question": "Can a minor enter into a contract?",
  "answer": "According to Section 11 of the Indian Contract Act, every person is competent to contract who is of the age of majority...",
  "citations": [
    {
      "section_id": "11",
      "title": "Who are competent to contract",
      "source": "A187209.pdf",
      "score": 0.92
    }
  ],
  "context_used": 6
}
```

---

## Testing

```bash
cd backend
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=html

# Run only unit tests (fast)
pytest tests/test_parser.py tests/test_embedder.py -v

# Run only API tests
pytest tests/test_api.py -v

# Run RAG quality tests
pytest tests/test_rag_quality.py -v
```

### Testing strategy

| Type | Files | What it catches |
|---|---|---|
| Unit | `test_parser.py`, `test_embedder.py` | Individual function bugs |
| Integration | `test_retrieval.py` | Pipeline connection failures |
| Black box | `test_api.py` | Broken API endpoints |
| Gold standard | `test_rag_quality.py` | Wrong legal answers from LLM |
| Regression | GitHub Actions (CI) | Breakage on every push |

---

## Adding New Laws

Drop a new PDF into `backend/data/raw/` and run:

```bash
python3 ingestion/run_ingestion.py
```

Already ingested documents are automatically skipped. The FAISS index and graph grow incrementally without rebuilding from scratch.

**Recommended acts to add:**
- Indian Penal Code 1860
- Constitution of India
- Code of Criminal Procedure 1973
- Information Technology Act 2000
- Consumer Protection Act 2019
- Right to Information Act 2005

All available free at [indiacode.nic.in](https://indiacode.nic.in)

---

## Audience

| User | Value |
|---|---|
| Citizens | Understand rights without a lawyer |
| Law students | Faster research with cross-section connections |
| Junior lawyers | Cut manual research time |
| Legal aid NGOs | Handle more cases with limited staff |

---

## Roadmap

- [ ] Add Constitution of India and IPC
- [ ] Graph visualisation in frontend (react-force-graph)
- [ ] Multi-language support (Hindi)
- [ ] User chat history persistence (database)
- [ ] Section comparison across multiple acts
- [ ] Mobile app (React Native)

---

## Author

**Sarbojit Dutta**  
Pre-final year B.Tech IT student at Asansol Engineering College  
[sarbojitd48@gmail.com](mailto:sarbojitd48@gmail.com) · [LinkedIn](https://linkedin.com/in/sarbojitdutta) · [GitHub](https://github.com/sarbojitdutta)

---


---

> Built as a portfolio project demonstrating SAT Graph RAG architecture for Indian legal document intelligence.
