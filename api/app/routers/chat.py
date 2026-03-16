from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_optional_current_user
from app.logger import log_query
from app.models import User
from app.schemas import ChatRequest
from app.services.chat_service import answer_llm, build_chain_input, build_history_str, generate_conversation_title
from app.services.conversation_service import (
    get_conversation_for_user,
    list_messages,
    save_message,
    update_conversation_title,
)

router = APIRouter(tags=["chat"])


def _format_sources_block(sources: list[str]) -> str:
    unique_sources: list[str] = []
    for source in sources:
        normalized = source.strip()
        if normalized and normalized not in unique_sources:
            unique_sources.append(normalized)

    if not unique_sources:
        return ""

    lines = ["", "", "Fonte:"]
    lines.extend(f"- {source}" for source in unique_sources)
    return "\n".join(lines)


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    conversation = None
    history_str = ""

    if current_user is not None:
        if not payload.conversation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="conversation_id is required for authenticated requests",
            )

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

        current_title = (conversation.title or "").strip().lower()
        if current_title in {"", "conversa sem titulo", "conversa sem título", "untitled conversation"}:
            update_conversation_title(
                db=db,
                conversation=conversation,
                title=generate_conversation_title(payload.question),
            )

        save_message(db=db, conversation_id=conversation.id, role="user", content=payload.question)
    else:
        history_str = build_history_str(
            [{"role": item.role, "content": item.content} for item in payload.history]
        )

    chain_input, sources = build_chain_input(question=payload.question, history_str=history_str)

    async def stream():
        full_answer = ""
        async for chunk in answer_llm.astream(chain_input):
            if chunk.content:
                full_answer += chunk.content
                yield chunk.content

        sources_block = _format_sources_block(sources)
        if sources_block:
            full_answer += sources_block
            yield sources_block

        if conversation is not None:
            save_message(db=db, conversation_id=conversation.id, role="assistant", content=full_answer)

        log_query(payload.question, sources, full_answer)

    return StreamingResponse(stream(), media_type="text/plain")
