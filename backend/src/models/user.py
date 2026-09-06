# User model
#
# Plan v9 referansı: Bölüm 1.15.1 — Account ve Auth

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    email_normalized: Mapped[str] = mapped_column(
        String(254), unique=True, nullable=False, index=True
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_email: Mapped[str | None] = mapped_column(
        String(254), nullable=True
    )  # E-posta değişikliği onay bekleyen adres (hosted only, ADR-021)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    locale: Mapped[str] = mapped_column(String(10), default="tr", server_default="tr")
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )  # pending | active | suspended | closed
    role: Mapped[str] = mapped_column(
        String(20), default="user", server_default="user", nullable=False
    )  # super_admin | admin | billing | support | user (ADR-010)
    plan_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # starter | professional | enterprise | None (self-hosted) (ADR-013)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<User(id={self.id!r}, email={self.email!r}, status={self.status!r})>"