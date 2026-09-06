# /api/v1 router — auth endpoints
#
# Plan v9 referansı: Bölüm 1.7.1 — Adım 7: onboarding/aktivasyon öncesi kayıt.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...schemas.user import UserCreate, UserRead
from ...services.audit import audit_log
from ...services.auth import auth_service
from ...services.user import user_service
from ..errors import conflict
from .account import router as account_router
from .admin import router as admin_router
from .auth import router as auth_router
from .files import router as files_router
from .history import router as history_router
from .legal import admin_router as legal_admin_router
from .legal import public_router as legal_router
from .output import router as output_router
from .plans import router as plans_router
from .profiles import router as profiles_router
from .smtp_admin import router as smtp_admin_router
from .translation import contraction_router, translate_router
from .translation import router as tables_router

router = APIRouter(prefix="/api/v1")
router.include_router(account_router)
router.include_router(auth_router)
router.include_router(files_router)
router.include_router(profiles_router)
router.include_router(history_router)
router.include_router(output_router)
router.include_router(plans_router)
router.include_router(admin_router)
router.include_router(legal_router)
router.include_router(legal_admin_router)
router.include_router(smtp_admin_router)
router.include_router(tables_router)
router.include_router(contraction_router)
router.include_router(translate_router)

# Tip alias — FastAPI dependency injection için
DbSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# POST /api/v1/register
# ---------------------------------------------------------------------------
# Ödeme webhook'u tarafından tetiklenir (billing provider adapter).
# Doğrudan kullanıcıya açık değildir. Account pending durumunda oluşturulur,
# aktivasyon e-postası ile parola belirlenir.
#
# Faz 1 billing ertelendiği için şimdilik direkt register olarak çalışır.


@router.post(
    "/register",
    response_model=UserRead,
    status_code=201,
    summary="Yeni kullanıcı kaydı",
    responses={
        201: {"description": "Kullanıcı oluşturuldu"},
        409: {"description": "Bu e-posta zaten kayıtlı"},
    },
)
async def register(body: UserCreate, db: DbSession) -> UserRead:
    from sqlalchemy import func, select

    # Self-hosted kayıt politikası kontrolü
    if settings.is_self_hosted and settings.self_hosted_registration == "closed":
        from sqlalchemy import func, select

        from ...models.user import User as UserModel
        result = await db.execute(select(func.count()).select_from(UserModel))
        user_count = result.scalar()
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "REGISTRATION_CLOSED",
                    "message": "Yeni kullanıcı kaydı yönetici tarafından kapatılmış.",
                },
            )

    # Duplicate kontrolü
    existing = await user_service.get_by_email(db, body.email)
    if existing:
        raise conflict(
            code="EMAIL_ALREADY_EXISTS",
            message="Bu e-posta adresi zaten kayıtlı.",
        )

    # Zayıf parola kontrolü
    if auth_service.is_weak_password(body.password):

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "WEAK_PASSWORD",
                "message": "Parola en az 8 karakter olmalıdır.",
            },
        )

    # Parola hash'le
    password_hash = auth_service.hash_password(body.password)

    # İlk kullanıcı mı? (self-hosted bootstrap — direkt active)
    from sqlalchemy import func, select

    from ...models.user import User as UserModel
    user_count = await db.execute(select(func.count()).select_from(UserModel))
    is_first_user = user_count.scalar() == 0

    # Kullanıcı oluştur (ilk kullanıcı bootstrap → direkt active)
    user = await user_service.create(
        db=db,
        email=body.email,
        password_hash=password_hash,
        display_name=body.display_name,
    )
    await db.commit()

    # Self-hosted ilk kullanıcı → direkt etkinleştir (bootstrap)
    if is_first_user and settings.is_self_hosted:
        await user_service.activate(db, user)
        await db.commit()
        audit_log.account_activated(user.id)

    audit_log.account_created(user.id, user.email)

    # Sunucu varsayılanlarını (updated_at, role, created_at) yüklemek için refresh
    await db.refresh(user)

    return UserRead.model_validate(user)