# Plan ve entitlement Pydantic schemas
#
# Plan v10 referansı: ADR-013 — Son kullanıcı plan yapısı

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlanRead(BaseModel):
    """API yanıtında plan bilgisi."""

    model_config = ConfigDict(from_attributes=True)

    plan_code: str
    name_tr: str
    name_en: str
    description_tr: str | None = None
    description_en: str | None = None
    price_monthly: int
    price_annual: int
    is_active: bool = True
    sort_order: int = 0


class PlanDetailRead(PlanRead):
    """Detaylı plan bilgisi — entitlement'ları içerir."""

    entitlements: dict[str, int] = Field(default_factory=dict)


class PlanCreate(BaseModel):
    """Plan oluşturma (admin)."""

    plan_code: str = Field(..., max_length=50, pattern=r"^[a-z0-9_]+$")
    name_tr: str = Field(..., max_length=100)
    name_en: str = Field(..., max_length=100)
    description_tr: str | None = Field(None, max_length=2000)
    description_en: str | None = Field(None, max_length=2000)
    price_monthly: int = Field(..., ge=0)
    price_annual: int = Field(..., ge=0)
    sort_order: int = Field(0, ge=0)
    entitlements: dict[str, int] = Field(default_factory=dict)


class PlanUpdate(BaseModel):
    """Plan güncelleme (admin)."""

    name_tr: str | None = Field(None, max_length=100)
    name_en: str | None = Field(None, max_length=100)
    description_tr: str | None = Field(None, max_length=2000)
    description_en: str | None = Field(None, max_length=2000)
    price_monthly: int | None = Field(None, ge=0)
    price_annual: int | None = Field(None, ge=0)
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)
    entitlements: dict[str, int] | None = None
