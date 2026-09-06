# TranslationHistory model — client-side encrypted translation history
#
# Plan v9 referansı: Bölüm 1.11.1, ADR-004.
# Sunucu sadece ciphertext, iv ve salt depolar — anahtara erişemez.
# Şifreleme: PBKDF2 (key derivation) + AES-256-GCM (encryption) tarayıcıda.

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TranslationHistory(Base):
    __tablename__ = "translation_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # AES-256-GCM şifreli çeviri verisi (JSON: {source, braille, metadata})
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)

    # IV (initialization vector) — base64 encoded, 12 bytes for GCM
    iv: Mapped[str] = mapped_column(String(24), nullable=False)

    # PBKDF2 salt — base64 encoded, 16 bytes
    salt: Mapped[str] = mapped_column(String(24), nullable=False)

    # Metadata (unencrypted — indexing/search için minimal)
    source_locale: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    table_id: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # text_to_braille | braille_to_text
    input_format: Mapped[str | None] = mapped_column(String(10))  # txt | docx | rtf | pdf
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int | None] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship("User", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<TranslationHistory(id={self.id!r}, user_id={self.user_id!r}, "
            f"locale={self.source_locale!r}, chars={self.char_count})>"
        )