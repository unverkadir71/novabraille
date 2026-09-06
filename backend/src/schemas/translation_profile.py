# TranslationProfile Pydantic schemas
#
# Plan v10 referansı: Faz 5.1-5.2.

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TranslationProfileCreate(BaseModel):
    """Yeni profil oluşturma."""

    name: str = Field(..., min_length=1, max_length=100)
    locale: str = Field(..., min_length=2, max_length=10)
    table_id: str = Field(..., min_length=1, max_length=50)
    mode: str = Field(..., pattern="^(display|embosser|notetaker)$")
    layout: str | None = Field(None, max_length=50)
    grade: str = Field("grade2", pattern="^(grade0|grade1|grade2)$")
    contraction_categories: list[str] | None = None
    page_settings: dict | None = None
    output_format: str | None = Field(None, pattern="^(txt|brf|brl|)$")  # Dosya formatı
    is_default: bool = False


class TranslationProfileUpdate(BaseModel):
    """Mevcut profili güncelleme. Tüm alanlar opsiyonel."""

    name: str | None = Field(None, min_length=1, max_length=100)
    locale: str | None = Field(None, min_length=2, max_length=10)
    table_id: str | None = Field(None, min_length=1, max_length=50)
    mode: str | None = Field(None, pattern="^(display|embosser|notetaker)$")
    layout: str | None = Field(None, max_length=50)
    grade: str | None = Field(None, pattern="^(grade0|grade1|grade2)$")
    contraction_categories: list[str] | None = None
    page_settings: dict | None = None
    output_format: str | None = Field(None, pattern="^(txt|brf|brl|)$")  # Dosya formatı
    is_default: bool | None = None


class TranslationProfileRead(BaseModel):
    """API yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    locale: str
    table_id: str
    mode: str
    layout: str | None = None
    grade: str = "grade2"
    contraction_categories: str | None = None
    page_settings: str | None = None
    output_format: str | None = None  # txt, brf, brl veya None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
