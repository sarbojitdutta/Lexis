import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi          import APIRouter, HTTPException
from api.schemas      import QueryRequest, QueryResponse, Citation
from retrieval.merger import build_context, build_citations
from llm.client       import answer_legal_question
import logging
logger = logging.getLogger(__name__)

router = APIRouter()


# ─────────────────────────────────────────────
# POST /api/query
# ─────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    Main endpoint — takes a legal question and
    returns an AI-generated answer with citations.

    Flow:
    1. Build context via vector + graph retrieval
    2. Send context + question to LLM
    3. Return answer with citations
    """
    try:
        # Step 1 — retrieve and merge context
        context, used_results = build_context(
            query    = request.question,
            k_vector = request.k_vector,
            k_graph  = request.k_graph,
        )

        if not used_results:
            raise HTTPException(
                status_code = 404,
                detail      = "No relevant legal context found "
                              "for this question."
            )

        # Step 2 — get answer from LLM
        answer = answer_legal_question(
            question = request.question,
            context  = context,
        )

        # Step 3 — build citations
        raw_citations = build_citations(used_results)
        citations     = [
            Citation(**c) for c in raw_citations
        ]

        return QueryResponse(
            question     = request.question,
            answer       = answer,
            citations    = citations,
            context_used = len(used_results),
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Query failed for question: {request.question}")
        raise HTTPException(
            status_code = 500,
            detail      = f"Query failed: {str(e)}"
        )