# TranslationHistory Pydantic schemas
#
# Plan v9 referansı: ADR-004.
# Sunucu sadece şifreli blob depolar — içeriğe erişemez.

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TranslationHistoryCreate(BaseModel):
    """Yeni şifreli çeviri kaydı — client tarafından gönderilir."""

    ciphertext: str  # AES-256-GCM şifreli JSON
    iv: str = Field(..., max_length=24)
    salt: str = Field(..., max_length=24)
    source_locale: str = Field(..., max_length=10)
    table_id: str = Field(..., max_length=50)
    direction: str = Field(..., pattern="^(text_to_braille|braille_to_text)$")
    input_format: str | None = Field(None, max_length=10)
    char_count: int = Field(..., ge=0)
    word_count: int | None = Field(None, ge=0)
    expires_at: datetime | None = None


class TranslationHistoryRead(BaseModel):
    """API yanıtı — şifreli veri + metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    ciphertext: str  # Şifreli — sadece client çözebilir
    iv: str
    salt: str
    source_locale: str
    table_id: str
    direction: str
    input_format: str | None = None
    char_count: int
    word_count: int | None = None
    created_at: datetime
    expires_at: datetime | None = None


class TranslationHistoryListItem(BaseModel):
    """Liste görünümü — şifreli veri OLMADAN (daha hafif)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source_locale: str
    table_id: str
    direction: str
    input_format: str | None = None
    char_count: int
    created_at: datetime