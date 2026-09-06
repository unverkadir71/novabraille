# Usage counter SQLAlchemy model
#
# Plan v9 referansı: Bölüm 1.9.2, 1.15.3 — Kullanım Ölçümü

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UsageCounter(Base):
    """Kullanıcı bazında aylık kullanım sayacı.

    Hosted modda karakter ve istek takibi için kullanılır.
    Self-hosted modda sınırsızdır.
    """

    __tablename__ = "usage_counters"

    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: uuid.uuid4().hex
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    characters_processed: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    request_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
