# Usage (kullanım ölçümü) servisi
#
# Plan v9 referansı: Bölüm 1.9.2, 1.15.3

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.usage_counter import UsageCounter


class UsageService:
    """Kullanıcı kullanım sayacı yönetimi."""

    async def get_current_period(
        self, db: AsyncSession, user_id: str
    ) -> UsageCounter | None:
        """Bu ayki kullanım sayacını döndür (yoksa None)."""
        today = date.today()
        period_start = today.replace(day=1)
        result = await db.execute(
            select(UsageCounter).where(
                UsageCounter.user_id == user_id,
                UsageCounter.period_start == period_start,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_period(
        self, db: AsyncSession, user_id: str
    ) -> UsageCounter:
        """Bu ayki sayacı döndür, yoksa oluştur."""
        counter = await self.get_current_period(db, user_id)
        if counter is None:
            counter = UsageCounter(
                user_id=user_id,
                period_start=date.today().replace(day=1),
            )
            db.add(counter)
            await db.flush()
        return counter

    async def increment(
        self, db: AsyncSession, user_id: str, char_count: int
    ) -> UsageCounter:
        """Kullanım sayacını artır."""
        counter = await self.get_or_create_period(db, user_id)
        counter.characters_processed = UsageCounter.characters_processed + char_count
        counter.request_count = UsageCounter.request_count + 1
        counter.updated_at = datetime.now(UTC)
        return counter

    async def get_monthly_total(
        self, db: AsyncSession, user_id: str
    ) -> tuple[int, int]:
        """Bu ayki toplam karakter ve istek sayısı."""
        counter = await self.get_current_period(db, user_id)
        if counter is None:
            return (0, 0)
        return (counter.characters_processed, counter.request_count)


usage_service = UsageService()
