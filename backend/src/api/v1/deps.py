# Auth dependency — FastAPI dependency injection for session-based auth
#
# Plan v9 referansı: Bölüm 1.8.1 (Tarayıcı Oturumu), 1.9 (Yetkilendirme)

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.user import User
from ...services.rbac import Permission, Role, has_permission, normalize_role
from ...services.session import SESSION_COOKIE, session_service

# Module-level: FastAPI B008 uyarısını önler
_get_db = get_db


async def get_current_user(
    db: Annotated[AsyncSession, Depends(_get_db)],
    nova_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    """Oturum cookie'sinden geçerli kullanıcıyı döndürür.

    Raises 401: Cookie yok, geçersiz veya süresi dolmuş.
    """
    if not nova_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Kimlik doğrulaması gerekli."},
        )

    session, user = await session_service.verify(db, nova_session)

    if session is None or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "SESSION_EXPIRED", "message": "Oturumunuz sona ermiş. Giriş yapın."},
        )

    await session_service.refresh(db, session)
    await db.commit()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission: Permission):
    """Role bazlı izin kontrolü yapan FastAPI dependency üreticisi.

    Kullanım:
        @router.get("/admin/...")
        async def endpoint(
            user: Annotated[User, Depends(require_permission(Permission.MANAGE_USERS))],
        ): ...

    Raises 403: Kullanıcının rolü ilgili izne sahip değilse.
    """
    from ...config import settings

    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        role = normalize_role(current_user.role)
        is_self_hosted = settings.is_self_hosted

        if not has_permission(role, permission, is_self_hosted):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSION",
                    "message": (
                        f"Bu işlem için '{permission.value}' izni gerekli."
                    ),
                },
            )
        return current_user

    return _check


def require_admin():
    """Herhangi bir admin düzeyinde erişim gerektiren dependency.

    Kullanıcının rolü user değilse (yani admin paneline erişebilen bir rol) geçer.
    """
    from ...config import settings

    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        role = normalize_role(current_user.role)
        is_self_hosted = settings.is_self_hosted

        # user rolü admin paneline erişemez
        if role == Role.USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ADMIN_ONLY",
                    "message": "Bu alana yalnızca yöneticiler erişebilir.",
                },
            )

        # Self-hosted modda admin dışı roller geçersiz
        from ...services.rbac import is_valid_role_for_mode
        if not is_valid_role_for_mode(role, is_self_hosted):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INVALID_ROLE_FOR_MODE",
                    "message": "Bu rol geçerli uygulama modunda desteklenmiyor.",
                },
            )

        return current_user

    return _check