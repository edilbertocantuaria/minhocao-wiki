from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import ConversationCreateRequest, ConversationResponse, MessageResponse
from app.services.conversation_service import (
    create_conversation,
    delete_conversation,
    get_conversation_for_user,
    list_conversations,
    list_messages,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation_endpoint(
    payload: ConversationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    conversation = create_conversation(db=db, user_id=current_user.id, title=payload.title)
    return ConversationResponse(id=conversation.id, title=conversation.title, created_at=conversation.created_at)


@router.get("", response_model=list[ConversationResponse])
def list_conversations_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationResponse]:
    conversations = list_conversations(db=db, user_id=current_user.id)
    return [
        ConversationResponse(id=item.id, title=item.title, created_at=item.created_at)
        for item in conversations
    ]


@router.get("/{conversation_id}", response_model=list[MessageResponse])
def get_conversation_messages_endpoint(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageResponse]:
    conversation = get_conversation_for_user(db=db, conversation_id=conversation_id, user_id=current_user.id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = list_messages(db=db, conversation_id=conversation.id)
    return [
        MessageResponse(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation_endpoint(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    conversation = get_conversation_for_user(db=db, conversation_id=conversation_id, user_id=current_user.id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    delete_conversation(db=db, conversation=conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
