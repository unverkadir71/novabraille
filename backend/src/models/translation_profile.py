# TranslationProfile model — kullanıcı çeviri profili
#
# Plan v10 referansı: Faz 5.1-5.2.
# Kullanıcıların tekrar kullanmak üzere kaydettiği çeviri tercihleri.
# Dil, tablo, mod, düzen ve kısaltma kategorilerini saklar.

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TranslationProfile(Base):
    __tablename__ = "translation_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)  # tr, en, de, vb.
    table_id: Mapped[str] = mapped_column(String(50), nullable=False)  # Liblouis tablo yolu
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # display | embosser | notetaker
    layout: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Sadece embosser/notetaker modu için: a4, letter, vb.
    grade: Mapped[str] = mapped_column(
        String(20), default="grade2", server_default="grade2", nullable=False
    )  # grade0 | grade1 | grade2
    contraction_categories: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array: ["single_letter", "two_letter", ...]
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    # Sayfa düzeni ayarları (JSON blob)
    # {"paper_size": "a4"|"letter"|"11.5x11", "chars_per_line": 30,
    #  "lines_per_page": 28, "top_margin": 0, "binding_margin": 0,
    #  "interpoint": false}
    page_settings: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    # Dosya formatı tercihi (txt, brf, brl — seçili moda göre)
    output_format: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # İlişkiler
    user: Mapped[User] = relationship("User", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<TranslationProfile(id={self.id!r}, user_id={self.user_id!r}, "
            f"name={self.name!r}, locale={self.locale!r})>"
        )
