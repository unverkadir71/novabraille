# LegalDocument model — yönetilebilir hukuki belgeler
#
# Plan v9 referansı: Bölüm 1.11.2 (KVKK ve diğer yükümlülükler)
# Plan v10 görev listesi: F3.10 (hukuki belge yönetimi API), F3.11 (admin editörü)
#
# Hukuki metinler (Gizlilik, KVKK, Kullanım Koşulları, İade/İptal,
# Erişilebilirlik Bildirimi) admin panelinden düzenlenebilir.
# İçerik Markdown olarak saklanır; public sitede render edilir.
# Hem hosted hem self-hosted modda admin tarafından yönetilebilir (ADR-012).

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LegalDocument(Base):
    """Yönetilebilir hukuki belge (gizlilik, KVKK, koşullar vb.)."""

    __tablename__ = "legal_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    # Sabit tanımlayıcı: privacy | terms | kvkk | refund | accessibility
    slug: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    title_tr: Mapped[str] = mapped_column(String(200), nullable=False)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    # draft: yayınlanmadı, published: public sitede görünür
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<LegalDocument(slug={self.slug!r}, status={self.status!r})>"
