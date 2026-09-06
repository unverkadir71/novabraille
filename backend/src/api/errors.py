# API error handling — consistent error responses
#
# Plan v9 referansı: Bölüm 1.16 (API Sınırları ve Hata Modeli)

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Uygulama seviyesi HTTP hatası — correlation ID otomatik eklenir."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid.uuid4())
        content: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "correlation_id": self.correlation_id,
        }
        if self.details:
            content["details"] = self.details
        super().__init__(status_code=status_code, detail=content)


# Yaygın hata üreticileri

def conflict(code: str, message: str, **details: Any) -> AppError:
    """409 Conflict — örn. duplicate email."""
    return AppError(status.HTTP_409_CONFLICT, code, message, details)


def not_found(code: str, message: str) -> AppError:
    """404 Not Found."""
    return AppError(status.HTTP_404_NOT_FOUND, code, message)


def unauthorized(message: str = "Kimlik doğrulaması gerekli") -> AppError:
    """401 Unauthorized."""
    return AppError(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)


def forbidden(message: str = "Bu işlem için yetkiniz yok") -> AppError:
    """403 Forbidden."""
    return AppError(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


def rate_limited(message: str = "Çok fazla istek") -> AppError:
    """429 Too Many Requests."""
    return AppError(status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMITED", message)


def service_unavailable(message: str = "Servis geçici olarak kullanılamıyor") -> AppError:
    """503 Service Unavailable."""
    return AppError(status.HTTP_503_SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE", message)