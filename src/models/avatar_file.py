"""Avatar images kept in the database, for hosts without a persistent disk (STORAGE_BACKEND=db)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database import Base


class AvatarFile(Base):
    __tablename__ = "avatar_files"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    content_type: Mapped[str] = mapped_column(String(32))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
