# Admin SMTP API router — SMTP ayarları yönetimi (ADR-023)
#
# GET  /api/v1/admin/smtp  — mevcut ayarları görüntüle (şifre maskeli)
# PUT  /api/v1/admin/smtp  — ayarları güncelle
# POST /api/v1/admin/smtp/test — test e-postası gönder

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...services.audit import audit_log
from ...services.rbac import Permission
from ...services.smtp_config import smtp_config_service
from .csrf import csrf_protect
from .deps import CurrentUser, require_permission

router = APIRouter(prefix="/admin/smtp", tags=["admin", "smtp"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SmtpConfigUpdate(BaseModel):
    """SMTP ayarları güncelleme isteği. Tüm alanlar isteğe bağlı."""

    enabled: bool | None = None
    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    username: str | None = Field(None, max_length=255)
    password: str | None = Field(None, max_length=255)
    from_name: str | None = Field(None, min_length=1, max_length=100)
    from_email: str | None = Field(None, max_length=254)
    use_tls: bool | None = None


# ---------------------------------------------------------------------------
# GET /api/v1/admin/smtp
# ---------------------------------------------------------------------------


@router.get(
    "",
    dependencies=[
        Depends(require_permission(Permission.MANAGE_EMAIL)),
    ],
)
async def get_smtp_config(
    db: DbSession,
) -> dict:
    """Mevcut SMTP yapılandırmasını döndürür (şifre maskeli)."""
    config = await smtp_config_service.get_or_create(db)
    return smtp_config_service.to_api_response(config)


# ---------------------------------------------------------------------------
# PUT /api/v1/admin/smtp
# ---------------------------------------------------------------------------


@router.put(
    "",
    dependencies=[
        Depends(require_permission(Permission.MANAGE_EMAIL)),
        Depends(csrf_protect),
    ],
)
async def update_smtp_config(
    body: SmtpConfigUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """SMTP ayarlarını günceller.

    Şifre alanı boş gönderilirse mevcut şifre korunur.
    Hosted modda SMTP devre dışı bırakılamaz.
    """
    # Hosted modda SMTP zorunlu — devre dışı bırakılamaz
    if settings.is_hosted and body.enabled is False:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "SMTP_REQUIRED",
                "message": "Hosted modda SMTP devre dışı bırakılamaz.",
            },
        )

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "NO_CHANGES",
                "message": "Güncellenecek alan belirtilmedi.",
            },
        )

    config = await smtp_config_service.update_config(db, update_data)
    await db.commit()

    audit_log.smtp_updated(current_user.id, list(update_data.keys()))
    return smtp_config_service.to_api_response(config)


# ---------------------------------------------------------------------------
# POST /api/v1/admin/smtp/test
# ---------------------------------------------------------------------------


@router.post(
    "/test",
    dependencies=[
        Depends(require_permission(Permission.MANAGE_EMAIL)),
        Depends(csrf_protect),
    ],
)
async def test_smtp_config(
    db: DbSession,
) -> dict:
    """Mevcut SMTP ayarlarıyla test e-postası gönderir."""
    config = await smtp_config_service.get_config(db)
    if config is None or not config.enabled:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "SMTP_DISABLED",
                "message": "SMTP etkin değil. Önce SMTP'yi etkinleştirin.",
            },
        )

    result = await smtp_config_service.send_test_email(config)
    return result
