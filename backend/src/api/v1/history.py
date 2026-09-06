# Translation history router — client-side encrypted blob storage
#
# Plan v9 referansı: ADR-004.
# Sunucu sadece ciphertext depolar, veriye erişemez.
# Şifreleme/çözme tamamen client tarafında (Web Crypto API).

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.translation_history import TranslationHistory
from ...schemas.translation_history import (
    TranslationHistoryCreate,
    TranslationHistoryListItem,
    TranslationHistoryRead,
)
from ..errors import not_found
from .csrf import csrf_protect
from .deps import CurrentUser

router = APIRouter(prefix="/history", tags=["history"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    response_model=TranslationHistoryRead,
    status_code=201,
    dependencies=[Depends(csrf_protect)],
)
async def save_entry(
    body: TranslationHistoryCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> TranslationHistoryRead:
    """Şifreli çeviri kaydı oluşturur. Ciphertext sunucu tarafından okunamaz."""
    entry = TranslationHistory(
        id=str(uuid4()),
        user_id=current_user.id,
        ciphertext=body.ciphertext,
        iv=body.iv,
        salt=body.salt,
        source_locale=body.source_locale,
        table_id=body.table_id,
        direction=body.direction,
        input_format=body.input_format,
        char_count=body.char_count,
        word_count=body.word_count,
        expires_at=body.expires_at,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return TranslationHistoryRead.model_validate(entry)


@router.get("", response_model=list[TranslationHistoryListItem])
async def list_entries(
    current_user: CurrentUser,
    db: DbSession,
    locale: str | None = Query(None, description="Dil filtresi"),
    direction: str | None = Query(None, description="Çeviri yönü filtresi"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[TranslationHistoryListItem]:
    """Kullanıcının çeviri geçmişini listeler (şifreli veri olmadan)."""
    stmt = (
        select(TranslationHistory)
        .where(TranslationHistory.user_id == current_user.id)
        .order_by(TranslationHistory.created_at.desc())
    )

    if locale:
        stmt = stmt.where(TranslationHistory.source_locale == locale)
    if direction:
        stmt = stmt.where(TranslationHistory.direction == direction)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    return [TranslationHistoryListItem.model_validate(e) for e in entries]


@router.get("/{entry_id}", response_model=TranslationHistoryRead)
async def get_entry(
    entry_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> TranslationHistoryRead:
    """Tek bir şifreli çeviri kaydını döndürür (ciphertext dahil)."""
    result = await db.execute(
        select(TranslationHistory).where(
            TranslationHistory.id == entry_id,
            TranslationHistory.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise not_found(code="ENTRY_NOT_FOUND", message="Çeviri kaydı bulunamadı.")

    return TranslationHistoryRead.model_validate(entry)


@router.delete("/{entry_id}", status_code=200, dependencies=[Depends(csrf_protect)])
async def delete_entry(
    entry_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    """Şifreli çeviri kaydını siler."""
    result = await db.execute(
        select(TranslationHistory).where(
            TranslationHistory.id == entry_id,
            TranslationHistory.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise not_found(code="ENTRY_NOT_FOUND", message="Çeviri kaydı bulunamadı.")

    await db.delete(entry)
    await db.commit()

    return {"message": "Çeviri kaydı silindi."}


@router.get("/stats/count", response_model=dict)
async def entry_count(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Kullanıcının toplam kayıt ve karakter sayısı."""
    result = await db.execute(
        select(
            func.count(TranslationHistory.id),
            func.sum(TranslationHistory.char_count),
        ).where(TranslationHistory.user_id == current_user.id)
    )
    total_rows, total_chars = result.one()

    return {
        "total_entries": total_rows or 0,
        "total_characters": total_chars or 0,
    }