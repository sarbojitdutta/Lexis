import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException, Depends
from api.schemas import QueryRequest, QueryResponse, Citation
from retrieval.merger import build_context, build_citations
from llm.client import answer_legal_question
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
    Conversational legal RAG endpoint.

    Flow:
    1. Resolve/create the authenticated user's chat.
    2. Load recent conversation history.
    3. Retrieve legal context using the current question.
    4. Generate an answer using legal context + conversation history.
    5. Persist both user and assistant messages.
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in authentication token")

    chat_id = request.chat_id

    try:
        # Create a chat automatically when this is the first message.
        if chat_id:
            chat = get_chat(chat_id=chat_id, user_id=str(user_id))
            if not chat:
                raise HTTPException(status_code=404, detail="Chat not found")
        else:
            chat = create_chat(user_id=str(user_id), title=request.question[:80])
            chat_id = chat["id"]

        # Load previous turns before saving the current question.
        history = chat_history(chat_id=chat_id, limit=20)

        # Retrieve legal evidence using the current question.
        context, used_results = build_context(
            query=request.question,
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

        # Convert stored turns into a compact chronological transcript.
        history_text = "\n".join(
            f"{item['role'].upper()}: {item['content']}"
            for item in history
        )

        # The existing LLM function remains responsible for the legal answer;
        # conversation history is added to the prompt as additional context.
        conversational_question = request.question
        if history_text:
            conversational_question = (
                "Conversation history:\n"
                f"{history_text}\n\n"
                "Current user question:\n"
                f"{request.question}"
            )

        answer = answer_legal_question(
            question=conversational_question,
            context=context,
        )

        # Persist only after successful retrieval + generation.
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
        logger.exception(f"Query failed for question: {request.question}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
