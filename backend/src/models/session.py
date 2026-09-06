# Session model — server-side session backed by HttpOnly cookie
#
# Plan v9 referansı: Bölüm 1.8.1, 1.15.1

from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(45))  # IPv6 max length
    user_agent_hash: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User] = relationship("User", lazy="selectin")  # noqa: F821

    @staticmethod
    def generate_token() -> str:
        """64 bytes → 86 chars URL-safe random token."""
        return token_urlsafe(64)

    @property
    def is_expired(self) -> bool:
        now_utc = datetime.now(UTC)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return now_utc > expires

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_revoked

    def __repr__(self) -> str:
        return f"<Session(id={self.id!r}, user_id={self.user_id!r}, valid={self.is_valid})>"