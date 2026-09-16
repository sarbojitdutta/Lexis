import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException, Depends
from api.schemas import QueryRequest, QueryResponse, Citation
from retrieval.merger import build_context, build_citations
from llm.client import answer_legal_question, rewrite_conversational_query
from db.graph.conversations import create_chat, get_chat, chat_history, save_message
from auth.middleware import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Conversational legal Graph-RAG endpoint.

    Flow:
        question + history
              ↓
        query rewriting
              ↓
        FAISS + graph retrieval
              ↓
        legal context + history + original question
              ↓
        grounded LLM answer
              ↓
        save user + assistant messages
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token",
        )

    chat_id = request.chat_id

    try:
        # The backend owns chat IDs. A missing chat_id starts a new conversation.
        if chat_id:
            chat = get_chat(chat_id=chat_id, user_id=str(user_id))
            if not chat:
                raise HTTPException(status_code=404, detail="Chat not found")
        else:
            chat = create_chat(
                user_id=str(user_id),
                title=request.question[:80],
            )
            chat_id = chat["id"]

        # Do not include the current question yet: it is not persisted until
        # retrieval and generation succeed.
        history = chat_history(chat_id=chat_id, limit=20)

        history_text = "\n".join(
            f"{item['role'].upper()}: {item['content']}"
            for item in history[-10:]
        )

        # Resolve conversational references before retrieval.
        search_query = rewrite_conversational_query(
            question=request.question,
            history=history,
        )

        logger.info(
            "RAG query | chat_id=%s | original=%r | retrieval=%r",
            chat_id,
            request.question,
            search_query,
        )

        # Retrieval now receives the standalone query rather than the raw
        # follow-up, allowing both FAISS and SAT graph traversal to find the
        # correct legal sections.
        context, used_results = build_context(
            query=search_query,
            k_vector=request.k_vector,
            k_graph=request.k_graph,
        )

        if not used_results:
            raise HTTPException(
                status_code=404,
                detail="No relevant legal context found for this question.",
            )

        raw_citations = build_citations(used_results)
        citations = [Citation(**c) for c in raw_citations]

        # The original user question is used for the answer so the response
        # remains natural, while history resolves conversational references.
        answer = answer_legal_question(
            question=request.question,
            context=context,
            history=history_text,
        )

        # Persist only after successful retrieval and generation.
        save_message(
            chat_id=chat_id,
            role="user",
            content=request.question,
        )
        save_message(
            chat_id=chat_id,
            role="assistant",
            content=answer,
            citations=raw_citations,
        )

        return QueryResponse(
            question=request.question,
            answer=answer,
            chat_id=chat_id,
            citations=citations,
            context_used=len(used_results),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Query failed for question: %s", request.question)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
