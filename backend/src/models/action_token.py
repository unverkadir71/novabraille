# ActionToken model — one-time tokens for account activation and password reset
#
# Plan v9 referansı: Bölüm 1.8.3, 1.15.1

from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ActionToken(Base):
    __tablename__ = "action_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # activate_account | reset_password
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

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
    def is_used(self) -> bool:
        return self.used_at is not None

    def __repr__(self) -> str:
        return (
            f"<ActionToken(id={self.id!r}, purpose={self.purpose!r}, "
            f"used={self.is_used}, expired={self.is_expired})>"
        )