from sqlalchemy.orm import Session

from app.models import Conversation, Message


def summarize_conversation_title(question: str, max_length: int = 72) -> str:
    normalized = " ".join(question.strip().split())
    if not normalized:
        return "Nova conversa"

    if len(normalized) <= max_length:
        return normalized

    return normalized[: max_length - 3].rstrip() + "..."


def create_conversation(db: Session, user_id: str, title: str | None = None) -> Conversation:
    conversation = Conversation(user_id=user_id, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_conversations(db: Session, user_id: str) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


def get_conversation_for_user(db: Session, conversation_id: str, user_id: str) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )


def delete_conversation(db: Session, conversation: Conversation) -> None:
    db.delete(conversation)
    db.commit()


def update_conversation_title(db: Session, conversation: Conversation, title: str) -> Conversation:
    conversation.title = title
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_messages(db: Session, conversation_id: str) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def save_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
