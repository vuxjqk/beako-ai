"""Password login attempts, for limiting guesses per account (src/services/login_limit.py) and
as an audit trail of failed logins."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_email_created", "email", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # As typed (lowercased), whether or not an account has it
    email: Mapped[str] = mapped_column(String(320))
    success: Mapped[bool]
    # Informational only: behind the frontend proxy it can be spoofed, so limits never use it
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
