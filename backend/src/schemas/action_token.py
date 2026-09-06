# ActionToken Pydantic schemas
#
# Plan v9 referansı: Bölüm 1.8.3, 1.15.1.
# Token'lar e-posta ile gönderilir, API'de URL parametresi olarak alınır.

from __future__ import annotations

from pydantic import BaseModel, Field


class ActionTokenCreate(BaseModel):
    """Yeni token oluşturma isteği — e-posta ile tetiklenir."""

    email: str = Field(..., max_length=254, description="Token gönderilecek e-posta adresi")
    purpose: str = Field(..., pattern="^(activate_account|reset_password)$")


class ActionTokenVerify(BaseModel):
    """Token doğrulama — kullanıcı e-posta linkine tıklar."""

    token: str = Field(..., description="E-posta ile gönderilen ham token")