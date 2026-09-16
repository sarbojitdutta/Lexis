from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from db.graph.conversations import (
    create_chat,
    chat_history,
    get_users_chat,
    get_chat,
    delete_chat
)

from auth.middleware import get_current_user

router = APIRouter(
    prefix="/chats",
    tags=["chats"]
)

class CreateChatRequest(BaseModel):
    title: Optional[str] = None

def get_user_id(current_user: dict) -> str:

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in authentication token"
        )

    return str(user_id)

@router.post("")
def create_new_chat(request: CreateChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = get_user_id(current_user)

    chat = create_chat(
        user_id=user_id,
        title=request.title
    )

    return {
        "success": True,
        "chat": chat
    }

@router.get("")
def get_all_chats(current_user: dict = Depends(get_current_user)):
    user_id = get_user_id(current_user)

    chats = get_users_chat(user_id)

    return {
        "success": True,
        "chats": chats
    }

@router.get("/{chat_id}")
def get_single_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user)
):

    user_id = get_user_id(current_user)

    chat = get_chat(
        chat_id=chat_id,
        user_id=user_id
    )

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )
    messages = chat_history(
        chat_id=chat_id,
        limit=100
    )

    return {
        "success": True,
        "chat": chat,
        "messages": messages
    }

@router.delete("/{chat_id}")
def remove_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user)
):

    user_id = get_user_id(current_user)

    deleted = delete_chat(
        chat_id=chat_id,
        user_id=user_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    return {
        "success": True,
        "message": "Chat deleted successfully"
    }