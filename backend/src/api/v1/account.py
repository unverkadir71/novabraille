# Account API router — veri dışa aktarma, hesap kapatma ve hesap düzenleme
#
# Plan v10 referansı: Faz 5.5, 5.6, 6.9 (ADR-021).

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...models.translation_history import TranslationHistory
from ...schemas.account import AccountUpdate
from ...services.audit import audit_log
from ...services.auth import auth_service
from ...services.user import user_service
from ...services.profile import profile_service
from .csrf import csrf_protect
from .deps import CurrentUser

router = APIRouter(prefix="/account", tags=["account"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# PATCH /api/v1/account
# ---------------------------------------------------------------------------


@router.patch(
    "",
    response_model=dict,
    status_code=200,
    dependencies=[Depends(csrf_protect)],
)
async def update_account(
    body: AccountUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Hesap bilgilerini kısmi olarak günceller (ADR-021).

    Değiştirilebilir alanlar:
    - display_name: görünen ad
    - email: e-posta adresi (hosted'de aktivasyon token'ı ile doğrulanır)
    - new_password: yeni parola

    Tüm değişiklikler için current_password doğrulaması zorunludur.
    """
    # 1. Mevcut parola doğrulaması (sabit zamanlı)
    if not auth_service.verify_password(
        body.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "WRONG_PASSWORD",
                "message": "Mevcut parola yanlış.",
            },
        )

    changes = []

    # 2. display_name güncelleme
    if body.display_name is not None:
        current_user.display_name = body.display_name
        changes.append("display_name")

    # 3. E-posta güncelleme
    if body.email is not None:
        new_email = body.email.strip().lower()

        # E-posta gerçekten değişiyor mu?
        if new_email != current_user.email_normalized:
            # Duplicate kontrolü
            existing = await user_service.get_by_email(db, new_email)
            if existing and existing.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "EMAIL_ALREADY_EXISTS",
                        "message": "Bu e-posta adresi zaten kullanılıyor.",
                    },
                )

            if settings.is_hosted:
                # Hosted: e-posta değişikliği aktivasyon token'ı ile doğrulanır
                # Yeni e-posta henüz doğrulanmadı — pending_email alanına yaz, token gönder
                current_user.pending_email = new_email
                from ...services.token import TokenPurpose, token_service

                change_token = await token_service.create(
                    db, current_user.id, TokenPurpose.EMAIL_CHANGE
                )
                change_url = (
                    f"{settings.app_url}/dashboard/confirm-email-change.html"
                    f"?token={change_token}"
                )
                # E-posta gönderimi — hosted SMTP üzerinden
                try:
                    from ...services.email import email_service as es

                    await es._send_template(  # noqa: SLF001
                        to=new_email,
                        template="email_change.txt.jinja2",
                        subject="Nova Braille — E-posta Değişikliği Onayı",
                        confirm_url=change_url,
                        display_name=current_user.display_name,
                    )
                except Exception:
                    # E-posta gönderilemezse pending_email'i geri al
                    current_user.pending_email = None
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail={
                            "code": "EMAIL_SEND_FAILED",
                            "message": "Onay e-postası gönderilemedi. Lütfen daha sonra tekrar deneyin.",
                        },
                    )

                changes.append("pending_email")
            else:
                # Self-hosted: doğrudan e-posta değişikliği (SMTP zorunlu değil)
                current_user.email = new_email
                current_user.email_normalized = new_email
                current_user.email_verified_at = None  # Yeni e-posta doğrulanmamış
                changes.append("email")

    # 4. Parola güncelleme
    if body.new_password is not None:
        if auth_service.is_weak_password(body.new_password):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "WEAK_PASSWORD",
                    "message": "Parola en az 8 karakter olmalıdır.",
                },
            )

        current_user.password_hash = auth_service.hash_password(body.new_password)
        changes.append("password")

    await db.commit()
    await db.refresh(current_user)

    audit_log.account_updated(current_user.id, ", ".join(changes))

    return {
        "message": "Hesap bilgileriniz güncellendi.",
        "changes": changes,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "status": current_user.status,
        },
    }


# ---------------------------------------------------------------------------
# Account Close Request Schema
# ---------------------------------------------------------------------------


class AccountCloseRequest(BaseModel):
    """Hesap kapatma isteği — parola doğrulaması gerektirir."""

    password: str = Field(..., min_length=1, description="Mevcut parola ile onay")
    confirmation: str = Field(
        ...,
        pattern="^HESABIMI KAPAT$",
        description='Tam olarak "HESABIMI KAPAT" yazılmalı',
    )


# ---------------------------------------------------------------------------
# GET /api/v1/account/export
# ---------------------------------------------------------------------------


@router.get("/export")
async def export_account_data(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """GDPR uyumlu kişisel veri dışa aktarımı.

    Kullanıcının tüm verilerini JSON formatında döndürür:
    - Hesap bilgileri
    - Çeviri profilleri
    - Çeviri geçmişi metadata (şifreli içerik dahil DEĞİL)
    - Kullanım istatistikleri

    Şifreli çeviri geçmişi içeriği (ciphertext) sunucu tarafından
    okunamadığı için payload'a dahil EDİLMEZ. Client-side export için
    kullanıcının kendi şifreleme anahtarıyla ayrı bir işlem yapması gerekir.
    """

    # Profiller
    profiles = await profile_service.list_for_user(db, current_user.id)
    profiles_data = []
    for p in profiles:
        profiles_data.append(
            {
                "id": p.id,
                "name": p.name,
                "locale": p.locale,
                "table_id": p.table_id,
                "mode": p.mode,
                "layout": p.layout,
                "grade": p.grade,
                "is_default": p.is_default,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
        )

    # Çeviri geçmişi metadata (şifreli içerik yok)
    result = await db.execute(
        select(TranslationHistory)
        .where(TranslationHistory.user_id == current_user.id)
        .order_by(TranslationHistory.created_at.desc())
    )
    history_entries = result.scalars().all()
    history_data = []
    for h in history_entries:
        history_data.append(
            {
                "id": h.id,
                "source_locale": h.source_locale,
                "table_id": h.table_id,
                "direction": h.direction,
                "input_format": h.input_format,
                "char_count": h.char_count,
                "word_count": h.word_count,
                "created_at": h.created_at.isoformat() if h.created_at else None,
                "expires_at": h.expires_at.isoformat() if h.expires_at else None,
            }
        )

    # Kullanım istatistikleri
    result = await db.execute(
        select(
            func.count(TranslationHistory.id),
            func.sum(TranslationHistory.char_count),
        ).where(TranslationHistory.user_id == current_user.id)
    )
    total_entries, total_chars = result.one()

    export = {
        "exported_at": None,  # Aşağıda datetime ile doldurulacak
        "account": {
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "locale": current_user.locale,
            "status": current_user.status,
            "role": current_user.role,
            "plan_code": current_user.plan_code,
            "email_verified_at": (
                current_user.email_verified_at.isoformat()
                if current_user.email_verified_at
                else None
            ),
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
            "last_login_at": (
                current_user.last_login_at.isoformat()
                if current_user.last_login_at
                else None
            ),
        },
        "profiles": profiles_data,
        "translation_history": history_data,
        "usage_stats": {
            "total_entries": total_entries or 0,
            "total_characters": total_chars or 0,
        },
    }

    from datetime import UTC, datetime

    export["exported_at"] = datetime.now(UTC).isoformat()

    audit_log.data_exported(current_user.id)
    return export


# ---------------------------------------------------------------------------
# POST /api/v1/account/close
# ---------------------------------------------------------------------------


@router.post(
    "/close",
    status_code=200,
    dependencies=[Depends(csrf_protect)],
)
async def close_account(
    body: AccountCloseRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    """Hesabı kapatır (soft delete).

    Güvenlik önlemleri:
    - Mevcut parola ile doğrulama
    - "HESABIMI KAPAT" aynen yazılmalı
    - Hesap zaten kapalıysa hata döner
    - Admin (super_admin) hesaplar kapatılamaz — önce rol düşürülmeli
    """

    # Zaten kapalı mı?
    if current_user.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "ALREADY_CLOSED",
                "message": "Bu hesap zaten kapatılmış.",
            },
        )

    # Admin hesaplar kapatılamaz
    from ...services.rbac import Role, normalize_role

    role = normalize_role(current_user.role)
    if role in (Role.SUPER_ADMIN, Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "ADMIN_ACCOUNT",
                "message": (
                    "Yönetici hesapları bu yöntemle kapatılamaz. "
                    "Önce rolünüzü düşürün veya sistem yöneticisiyle iletişime geçin."
                ),
            },
        )

    # Parola doğrulaması — sabit zamanlı
    if not auth_service.verify_password(body.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "WRONG_PASSWORD",
                "message": "Parola yanlış. Hesap kapatma işlemi iptal edildi.",
            },
        )

    # Soft delete: status → closed
    current_user.status = "closed"
    await db.commit()

    audit_log.account_closed(current_user.id)
    return {"message": "Hesabınız kapatıldı. Verileriniz 30 gün içinde kalıcı olarak silinecektir."}
