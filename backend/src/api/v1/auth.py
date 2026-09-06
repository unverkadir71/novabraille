# Auth router — account activation, password reset, login/logout
#
# Plan v9 referansı: Bölüm 1.7.1 (Müşteri Akışı), 1.8 (Kimlik Doğrulama)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...schemas.action_token import ActionTokenCreate
from ...schemas.user import PasswordResetConfirm, PasswordResetRequest, UserOnboarding, UserRead
from ...services.audit import audit_log
from ...services.auth import auth_service
from ...services.email import email_service
from ...services.rate_limit import rate_limiter
from ...services.session import SESSION_COOKIE, session_service
from ...services.token import token_service
from ...services.user import user_service
from ..errors import conflict, not_found
from .csrf import CSRF_COOKIE, csrf_protect, generate_csrf_token, set_csrf_cookie
from .deps import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# POST /api/v1/auth/send-activation
# ---------------------------------------------------------------------------


@router.post(
    "/send-activation",
    status_code=202,
    summary="Aktivasyon e-postası gönder",
)
async def send_activation(body: ActionTokenCreate, db: DbSession) -> dict[str, str]:
    user = await user_service.get_by_email(db, body.email)
    if user is None or user.status != "pending":
        return {"message": "Eğer hesabınız varsa aktivasyon e-postası gönderildi."}

    await token_service.invalidate_user_tokens(db, user.id, purpose="activate_account")
    raw_token = await token_service.create_token(db, user.id, purpose="activate_account")
    await db.commit()
    await email_service.send_activation_email(
        email=user.email, token=raw_token, display_name=user.display_name
    )
    return {"message": "Eğer hesabınız varsa aktivasyon e-postası gönderildi."}


# ---------------------------------------------------------------------------
# POST /api/v1/auth/activate
# ---------------------------------------------------------------------------


@router.post(
    "/activate",
    status_code=200,
    summary="Hesabı etkinleştir",
)
async def activate_account(body: UserOnboarding, db: DbSession) -> dict[str, str]:
    action_token = await token_service.verify_token(db, body.token, purpose="activate_account")
    if action_token is None:
        raise not_found(
            code="INVALID_TOKEN",
            message="Geçersiz veya süresi dolmuş aktivasyon bağlantısı.",
        )

    user = await user_service.get_by_id(db, action_token.user_id)
    if user is None:
        raise not_found(code="USER_NOT_FOUND", message="Kullanıcı bulunamadı.")

    if user.status == "active":
        await token_service.consume_token(db, action_token)
        await db.commit()
        raise conflict(code="ALREADY_ACTIVATED", message="Bu hesap zaten etkinleştirilmiş.")

    user.password_hash = auth_service.hash_password(body.password)
    if body.display_name:
        user.display_name = body.display_name

    await user_service.activate(db, user)
    audit_log.account_activated(user.id)
    audit_log.password_changed(user.id)
    await token_service.consume_token(db, action_token)
    audit_log.token_consumed(user.id, "activate_account")
    await token_service.invalidate_user_tokens(db, user.id, purpose="activate_account")
    await db.commit()

    return {"message": "Hesabınız başarıyla etkinleştirildi. Giriş yapabilirsiniz."}


# ---------------------------------------------------------------------------
# POST /api/v1/auth/send-password-reset
# ---------------------------------------------------------------------------


@router.post(
    "/send-password-reset",
    status_code=202,
    summary="Parola sıfırlama e-postası gönder",
)
async def send_password_reset(body: PasswordResetRequest, db: DbSession) -> dict[str, str]:
    user = await user_service.get_by_email(db, body.email)
    if user is None or user.status != "active":
        return {"message": "Eğer hesabınız varsa sıfırlama e-postası gönderildi."}

    await token_service.invalidate_user_tokens(db, user.id, purpose="reset_password")
    raw_token = await token_service.create_token(db, user.id, purpose="reset_password")
    await db.commit()
    await email_service.send_password_reset_email(email=user.email, token=raw_token)

    return {"message": "Eğer hesabınız varsa sıfırlama e-postası gönderildi."}


# ---------------------------------------------------------------------------
# POST /api/v1/auth/reset-password
# ---------------------------------------------------------------------------


@router.post(
    "/reset-password",
    status_code=200,
    summary="Parola sıfırla",
)
async def reset_password(body: PasswordResetConfirm, db: DbSession) -> dict[str, str]:
    if auth_service.is_weak_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "WEAK_PASSWORD", "message": "Parola en az 8 karakter olmalıdır."},
        )

    action_token = await token_service.verify_token(db, body.token, purpose="reset_password")
    if action_token is None:
        raise not_found(
            code="INVALID_TOKEN",
            message="Geçersiz veya süresi dolmuş sıfırlama bağlantısı.",
        )

    user = await user_service.get_by_id(db, action_token.user_id)
    if user is None:
        raise not_found(code="USER_NOT_FOUND", message="Kullanıcı bulunamadı.")

    user.password_hash = auth_service.hash_password(body.password)
    audit_log.password_changed(user.id)
    await token_service.consume_token(db, action_token)
    audit_log.token_consumed(user.id, "reset_password")
    await token_service.invalidate_user_tokens(db, user.id, purpose="reset_password")
    await db.commit()

    return {"message": "Parolanız başarıyla sıfırlandı."}


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


@router.post("/login", status_code=200, summary="Giriş yap")
async def login(
    request: Request,
    response: Response,
    db: DbSession,
    email: str = Form(),
    password: str = Form(),
) -> dict[str, str]:
    # Rate limit kontrolü
    client_ip = request.client.host if request.client else None
    normalized = user_service.normalize_email(email)

    if rate_limiter.is_locked(normalized, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "Çok fazla başarısız giriş denemesi. 15 dakika sonra tekrar deneyin.",
            },
        )

    user = await user_service.get_by_email(db, email)

    # Timing attack önleme: kullanıcı yoksa dummy hash ile karşılaştır
    if user is None or user.status != "active":
        rate_limiter.record_failure(normalized, client_ip)
        audit_log.login_failure(email, client_ip, "unknown_user")
        auth_service.verify_password(password, "$argon2id$v=19$m=65536,t=3,p=4$dummy_hash_value")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Geçersiz e-posta veya parola."},
        )

    if not auth_service.verify_password(password, user.password_hash):
        rate_limiter.record_failure(normalized, client_ip)
        audit_log.login_failure(email, client_ip, "wrong_password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Geçersiz e-posta veya parola."},
        )

    # Başarılı giriş — sayaçları sıfırla
    rate_limiter.record_success(normalized, client_ip)

    session, raw_token = await session_service.create(db, user, ip_address=client_ip)
    await user_service.update_last_login(db, user)
    await db.commit()
    audit_log.login_success(user.id, client_ip)

    response.set_cookie(
        key=SESSION_COOKIE,
        value=raw_token,
        httponly=True,
        secure=settings.app_url.startswith("https://"),
        samesite="lax",
        max_age=28800,
        path="/",
    )

    # CSRF cookie — HttpOnly=False, JS tarafından okunabilir
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token, not settings.app_url.startswith("https://"))

    return {"message": "Giriş başarılı."}


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=200, summary="Çıkış yap", dependencies=[Depends(csrf_protect)])
async def logout(
    response: Response,
    db: DbSession,
    nova_session: str | None = Cookie(None, alias=SESSION_COOKIE),
) -> dict[str, str]:
    if nova_session:
        session, _ = await session_service.verify(db, nova_session)
        if session:
            await session_service.revoke(db, session)
            audit_log.session_revoked(session.user_id, "logout")
            await db.commit()

    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=settings.app_url.startswith("https://"),
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key=CSRF_COOKIE,
        path="/",
        secure=settings.app_url.startswith("https://"),
        httponly=False,
        samesite="lax",
    )

    return {"message": "Başarıyla çıkış yapıldı."}


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserRead, summary="Geçerli kullanıcı bilgisi")
async def get_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)