"""Question-answering conversations: what users asked, what the system answered (with its
sources and agent trace), and the users' right/wrong feedback, which becomes real evaluation
data alongside the golden set."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database import Base


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Conversation(Base):
    __tablename__ = "qa_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))  # the first question, shortened
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "qa_messages"
    __table_args__ = (
        CheckConstraint("feedback IN (-1, 1)", name="ck_qa_messages_feedback"),
        Index("ix_qa_messages_conversation_created", "conversation_id", "created_at"),
        # Rated answers are the evaluation data; find them without scanning every message
        Index("ix_qa_messages_feedback", "feedback", postgresql_where=text("feedback IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("qa_conversations.id", ondelete="CASCADE")
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="qa_message_role", values_callable=lambda e: [m.value for m in e])
    )
    content: Mapped[str] = mapped_column(Text)
    # The reader's spoiler limit when the question was asked: only main volumes <= this were searched
    max_volume: Mapped[int | None] = mapped_column(Integer)

    # Assistant messages only
    found: Mapped[bool | None]
    mode: Mapped[str | None] = mapped_column(String(32))  # simple | agent | simple+agent
    model: Mapped[str | None] = mapped_column(String(128))
    sources: Mapped[list | None] = mapped_column(JSONB)
    trace: Mapped[list | None] = mapped_column(JSONB)
    usage: Mapped[dict | None] = mapped_column(JSONB)
    timings_ms: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)  # set when answering failed

    # The asker's judgement of an assistant answer: 1 = right, -1 = wrong
    feedback: Mapped[int | None] = mapped_column(SmallInteger)
    feedback_comment: Mapped[str | None] = mapped_column(Text)
    feedback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
