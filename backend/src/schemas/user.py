# User Pydantic schemas
#
# Plan v9 referansı: Bölüm 1.15.1. ORM modeli models/user.py ile eşleşir.
# Pydantic v2 BaseModel kullanır.

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# HTML tag temizleme (defense-in-depth — frontend textContent kullaniyor olsa da)
_HTML_RE = re.compile(r'<[^>]*>', re.IGNORECASE)

def _strip_html(v: str | None) -> str | None:
    if v is None:
        return None
    cleaned = _HTML_RE.sub('', v).strip()
    return cleaned if cleaned else None


class UserCreate(BaseModel):
    """Yeni kullanıcı oluşturma — onboarding/ödeme sonrası."""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=100)

    _strip_html = field_validator('display_name')(_strip_html)


class UserRead(BaseModel):
    """API yanıtlarında dönen kullanıcı bilgisi. Hassas alanlar hariç."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    email_verified_at: datetime | None = None
    display_name: str | None = None
    locale: str = "tr"
    status: str
    role: str = "user"
    plan_code: str | None = None
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class UserUpdate(BaseModel):
    """Profil güncelleme. E-posta ve parola değişikliği burada olmaz."""

    model_config = ConfigDict(from_attributes=True)

    display_name: str | None = Field(None, max_length=100)
    locale: str | None = Field(None, max_length=10)

    _strip_html = field_validator('display_name')(_strip_html)


class UserOnboarding(BaseModel):
    """Hesap etkinleştirme — onboarding sayfasından gelen istek."""

    token: str = Field(..., description="E-posta ile gönderilen aktivasyon token'ı")
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=100)

    _strip_html = field_validator('display_name')(_strip_html)


class PasswordResetRequest(BaseModel):
    """Parola sıfırlama talebi."""

    email: EmailStr = Field(..., max_length=254)


class PasswordResetConfirm(BaseModel):
    """Parola sıfırlama onayı."""

    token: str
    password: str = Field(..., min_length=8, max_length=128)