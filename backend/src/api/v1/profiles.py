# TranslationProfile API router
#
# Plan v10 referansı: Faz 5.1.
# Authenticated kullanıcılar kendi profillerini yönetebilir.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...schemas.translation_profile import (
    TranslationProfileCreate,
    TranslationProfileRead,
    TranslationProfileUpdate,
)
from ...services.entitlement import entitlement_service
from ...services.profile import ProfileLimitError, profile_service
from ..errors import not_found
from .csrf import csrf_protect
from .deps import CurrentUser

router = APIRouter(prefix="/profiles", tags=["profiles"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# GET /api/v1/profiles
# ---------------------------------------------------------------------------


@router.get("", response_model=list[TranslationProfileRead])
async def list_profiles(
    current_user: CurrentUser,
    db: DbSession,
) -> list[TranslationProfileRead]:
    """Kullanıcının tüm çeviri profillerini listeler."""
    profiles = await profile_service.list_for_user(db, current_user.id)
    return [TranslationProfileRead.model_validate(p) for p in profiles]


# ---------------------------------------------------------------------------
# POST /api/v1/profiles
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=TranslationProfileRead,
    status_code=201,
    dependencies=[Depends(csrf_protect)],
)
async def create_profile(
    body: TranslationProfileCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> TranslationProfileRead:
    """Yeni çeviri profili oluşturur."""
    # Profil limiti kontrolü
    max_profiles = await entitlement_service.get_profile_limit(db, current_user)
    await profile_service.check_limit(db, current_user, max_profiles)

    try:
        profile = await profile_service.create(
            db=db,
            user=current_user,
            name=body.name,
            locale=body.locale,
            table_id=body.table_id,
            mode=body.mode,
            grade=body.grade,
            layout=body.layout,
            contraction_categories=body.contraction_categories,
            page_settings=body.page_settings,
            output_format=body.output_format,
            is_default=body.is_default,
        )
    except ProfileLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PROFILE_LIMIT_REACHED",
                "message": (
                    f"Profil limitinize ulaştınız ({e.current}/{e.maximum}). "
                    f"Yeni profil oluşturmak için mevcut bir profili silin veya planınızı yükseltin."
                ),
            },
        )

    await db.commit()
    await db.refresh(profile)
    return TranslationProfileRead.model_validate(profile)


# ---------------------------------------------------------------------------
# GET /api/v1/profiles/{profile_id}
# ---------------------------------------------------------------------------


@router.get("/{profile_id}", response_model=TranslationProfileRead)
async def get_profile(
    profile_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> TranslationProfileRead:
    """Tek bir profilin detayını döndürür."""
    profile = await profile_service.get_by_id(db, current_user.id, profile_id)
    if not profile:
        raise not_found(
            code="PROFILE_NOT_FOUND",
            message="Profil bulunamadı.",
        )
    return TranslationProfileRead.model_validate(profile)


# ---------------------------------------------------------------------------
# PUT /api/v1/profiles/{profile_id}
# ---------------------------------------------------------------------------


@router.put(
    "/{profile_id}",
    response_model=TranslationProfileRead,
    dependencies=[Depends(csrf_protect)],
)
async def update_profile(
    profile_id: str,
    body: TranslationProfileUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> TranslationProfileRead:
    """Mevcut profili günceller. Tüm alanlar opsiyonel."""
    profile = await profile_service.get_by_id(db, current_user.id, profile_id)
    if not profile:
        raise not_found(
            code="PROFILE_NOT_FOUND",
            message="Profil bulunamadı.",
        )

    # Sadece gönderilen alanları uygula
    update_kwargs = body.model_dump(exclude_unset=True)
    if update_kwargs:
        await profile_service.update(db, profile, **update_kwargs)

    await db.commit()
    await db.refresh(profile)
    return TranslationProfileRead.model_validate(profile)


# ---------------------------------------------------------------------------
# DELETE /api/v1/profiles/{profile_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{profile_id}",
    status_code=200,
    dependencies=[Depends(csrf_protect)],
)
async def delete_profile(
    profile_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    """Profili siler. Son profil silinemez (en az bir profil zorunlu)."""
    profile = await profile_service.get_by_id(db, current_user.id, profile_id)
    if not profile:
        raise not_found(
            code="PROFILE_NOT_FOUND",
            message="Profil bulunamadı.",
        )

    # Son profil silinemez
    count = await profile_service.get_count(db, current_user.id)
    if count <= 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "LAST_PROFILE",
                "message": "En az bir profil bulunmalıdır. Son profili silemezsiniz.",
            },
        )

    await profile_service.delete(db, profile)
    await db.commit()

    return {"message": "Profil silindi."}
