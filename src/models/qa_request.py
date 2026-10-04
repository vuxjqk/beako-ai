"""One row per question sent to /qa: admitted or refused by the guardrails, what it cost and how
it ended. Per-user limits and the daily budget are counted from here, and the admin usage
report is built from it. Rows outlive the conversations (and accounts) they belong to, so a
deleted conversation does not give its spending back."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database import Base


class QaRequest(Base):
    __tablename__ = "qa_requests"
    __table_args__ = (
        Index("ix_qa_requests_user_created", "user_id", "created_at"),
        Index("ix_qa_requests_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # The stored answer (for its 👍/👎); null when refused or failed before answering
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("qa_messages.id", ondelete="SET NULL"))

    # running | answered | not_found | error | rejected
    status: Mapped[str] = mapped_column(String(16))
    # rejected: why (rate_limited, user_quota, budget, input_rejected, ...); error: the LLM error kind
    error_kind: Mapped[str | None] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text)
    question_chars: Mapped[int] = mapped_column(Integer)

    mode: Mapped[str | None] = mapped_column(String(32))  # simple | agent | simple+agent
    # The budget was nearly spent, so the agent was switched off for this question
    degraded: Mapped[bool] = mapped_column(server_default=text("false"))
    # The answer repeated the system prompt and was replaced by a refusal
    output_blocked: Mapped[bool] = mapped_column(server_default=text("false"))
    model: Mapped[str | None] = mapped_column(String(128))
    llm_calls: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    tools: Mapped[list | None] = mapped_column(JSONB)  # agent tool names, in call order
    prompt_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    completion_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), server_default=text("0"))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    found: Mapped[bool | None]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
