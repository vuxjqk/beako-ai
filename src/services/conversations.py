"""Storing questions and answers in qa_conversations / qa_messages."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.models import Conversation, Message, MessageRole
from src.services.qa import Answer

TITLE_LENGTH = 120


class ConversationNotFound(Exception):
    pass


def start_turn(db: Session, user_id: uuid.UUID, question: str, max_volume: int | None,
               conversation_id: uuid.UUID | None) -> Conversation:
    """The conversation to store this question in (a new one unless conversation_id is given),
    with the user's message already saved."""
    if conversation_id is not None:
        conv = db.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user_id:
            raise ConversationNotFound()
        conv.updated_at = datetime.now(timezone.utc)
    else:
        title = question if len(question) <= TITLE_LENGTH else question[: TITLE_LENGTH - 1] + "…"
        conv = Conversation(user_id=user_id, title=title)
        db.add(conv)
        db.flush()
    db.add(Message(conversation_id=conv.id, role=MessageRole.USER, content=question, max_volume=max_volume))
    db.commit()
    return conv


def save_answer(db: Session, conv: Conversation, a: Answer, max_volume: int | None) -> Message:
    msg = Message(
        conversation_id=conv.id, role=MessageRole.ASSISTANT, content=a.answer, max_volume=max_volume,
        found=a.found, mode=a.mode, model=a.model, sources=a.sources, trace=a.trace, usage=a.usage,
        timings_ms=a.timings_ms,
    )
    db.add(msg)
    db.commit()
    return msg


def save_error(db: Session, conv: Conversation, error: str, max_volume: int | None) -> Message:
    msg = Message(conversation_id=conv.id, role=MessageRole.ASSISTANT, content="", max_volume=max_volume,
                  error=error[:2000])
    db.add(msg)
    db.commit()
    return msg


def own_answer(db: Session, user_id: uuid.UUID, message_id: uuid.UUID) -> Message | None:
    """An assistant message in one of this user's conversations."""
    return db.execute(
        select(Message).join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.id == message_id, Message.role == MessageRole.ASSISTANT, Conversation.user_id == user_id)
    ).scalar_one_or_none()


def chunk_was_shown(db: Session, user_id: uuid.UUID, chunk_id: int) -> bool:
    """Whether this chunk was a source of one of the user's answers: source text is only served
    for passages the user was actually shown, so a spoiler limit cannot be bypassed by asking
    for arbitrary chunk ids."""
    return db.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM qa_messages m JOIN qa_conversations c ON c.id = m.conversation_id
            WHERE c.user_id = :u AND m.sources @> CAST(:probe AS jsonb)
        )
    """), {"u": user_id, "probe": f'[{{"chunk_id": {int(chunk_id)}}}]'}).scalar()
