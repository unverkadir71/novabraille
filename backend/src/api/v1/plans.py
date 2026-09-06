# Plans router — /api/v1/plans (herkese açık)
#
# Plan v10 referansı: ADR-013 — Son kullanıcı plan yapısı
# Fiyatlandırma sayfası için herkese açık plan listesi.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.plan import Plan
from ...schemas.plan import PlanRead

router = APIRouter(prefix="/plans", tags=["plans"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[PlanRead], summary="Aktif planları listele")
async def list_plans(db: DbSession) -> list[PlanRead]:
    """Fiyatlandırma sayfası için aktif planları sıralı döndürür.

    Self-hosted modda boş liste döner (plan yok).
    """
    result = await db.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.sort_order)  # noqa: E712
    )
    plans = result.scalars().all()
    return [PlanRead.model_validate(p) for p in plans]
