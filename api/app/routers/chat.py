from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.logger import log_query
from app.models import User
from app.schemas import ChatRequest
from app.services.chat_service import answer_llm, build_chain_input, build_history_str
from app.services.conversation_service import get_conversation_for_user, list_messages, save_message

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = get_conversation_for_user(
        db=db,
        conversation_id=payload.conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    history = list_messages(db=db, conversation_id=conversation.id)
    history_str = build_history_str(
        [{"role": message.role, "content": message.content} for message in history]
    )

    save_message(db=db, conversation_id=conversation.id, role="user", content=payload.question)
    chain_input, sources = build_chain_input(question=payload.question, history_str=history_str)

    async def stream():
        full_answer = ""
        async for chunk in answer_llm.astream(chain_input):
            if chunk.content:
                full_answer += chunk.content
                yield chunk.content

        save_message(db=db, conversation_id=conversation.id, role="assistant", content=full_answer)
        log_query(payload.question, sources, full_answer)

    return StreamingResponse(stream(), media_type="text/plain")
