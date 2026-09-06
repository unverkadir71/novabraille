# CSRF protection — Double Submit Cookie pattern
#
# Oturum cookie'si HttpOnly olduğu için JS tarafından okunamaz.
# Ayrı bir okunabilir CSRF cookie + header karşılaştırması kullanılır.
# Plan v9 referansı: Bölüm 1.8.1

from __future__ import annotations

import hashlib
from secrets import token_urlsafe

from fastapi import Cookie, Header, HTTPException, Request, status

CSRF_COOKIE = "nova_csrf"
CSRF_HEADER = "X-CSRF-Token"
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def generate_csrf_token() -> str:
    """32 byte rastgele CSRF token üretir (43 chars URL-safe)."""
    return token_urlsafe(32)


def hash_csrf_token(token: str) -> str:
    """CSRF token'ı SHA-256 ile hash'ler."""
    return hashlib.sha256(token.encode()).hexdigest()


async def csrf_protect(
    request: Request,
    nova_csrf: str | None = Cookie(None, alias=CSRF_COOKIE),
    x_csrf_token: str | None = Header(None, alias=CSRF_HEADER),
) -> None:
    """State-changing isteklerde CSRF token doğrulaması yapar.

    GET/HEAD/OPTIONS isteklerini atlar.
    Cookie'deki token ile header'daki token eşleşmelidir.
    """
    # Safe methods — doğrulama gerekmez
    if request.method in CSRF_SAFE_METHODS:
        return

    # Cookie veya header yok → reddet
    if not nova_csrf or not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "CSRF_MISSING",
                "message": "CSRF token gerekli.",
            },
        )

    # Sabit zamanlı karşılaştırma
    cookie_hash = hash_csrf_token(nova_csrf)
    header_hash = hash_csrf_token(x_csrf_token)

    if cookie_hash != header_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "CSRF_MISMATCH",
                "message": "CSRF token eşleşmedi.",
            },
        )


def set_csrf_cookie(response, csrf_token: str, is_development: bool = True) -> None:
    """Login sırasında CSRF cookie'sini ayarlar.

    HttpOnly=False — JS tarafından okunabilir (X-CSRF-Token header için).
    """
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,  # JS okumalı
        secure=not is_development,
        samesite="lax",
        max_age=28800,  # Oturumla aynı süre
        path="/",
    )