# Plan and Entitlement models
#
# Plan v10 referansı: ADR-013 — Son kullanıcı plan yapısı
#
# 3 plan: starter, professional, enterprise
# Entitlement: plan → feature → limit değeri (örn. plan=starter, feature=max_chars, limit=50000)
#
# Önemli: Bu modeller hosted SaaS için geçerlidir. Self-hosted modda
# tüm çeviri özellikleri sınırsızdır ve entitlement kontrolü uygulanmaz.

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Plan(Base):
    """Son kullanıcı abonelik planı tanımı."""

    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    plan_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )  # starter | professional | enterprise
    name_tr: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    description_tr: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)
    price_monthly: Mapped[int] = mapped_column(Integer, nullable=False)  # kuruş cinsinden
    price_annual: Mapped[int] = mapped_column(Integer, nullable=False)  # kuruş cinsinden
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )
    # Sıralama (fiyatlandırma sayfasında gösterim sırası)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Plan(plan_code={self.plan_code!r}, price_monthly={self.price_monthly})>"


class Entitlement(Base):
    """Plan → özellik eşleştirmesi ve limit değeri."""

    __tablename__ = "entitlements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    plan_code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # Plan.plan_code ile ilişkili (FK değil, string referans)
    feature_code: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # max_chars, max_profiles, file_upload, history, brf_download, api_access
    # limit_value: sayısal limit (ör. karakter kotası) veya -1 (sınırsız)
    # boolean özellikler için: 1 (var) / 0 (yok)
    limit_value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Entitlement(plan={self.plan_code!r}, "
            f"feature={self.feature_code!r}, limit={self.limit_value})>"
        )
