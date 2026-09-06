# Translation Pydantic schemas
#
# Request/response models for the translation engine endpoints.
# Plan v9 referansı: Faz 2 — Çeviri Çekirdeği

from __future__ import annotations

from pydantic import BaseModel, Field


class TableItem(BaseModel):
    """API yanıtında tek bir tablo."""

    id: str
    language: str | None = None
    grade: str | None = None
    type: str | None = None
    dots: int | None = None
    contraction: str | None = None
    supports_back_translation: bool = False
    name_tr: str | None = None
    name_en: str | None = None


class TableLanguageItem(BaseModel):
    """API yanıtında tek bir dil."""

    code: str
    name: str


class TranslateRequest(BaseModel):
    """Metin → Braille çeviri isteği."""

    text: str = Field(..., min_length=1, max_length=500_000)
    table_id: str = Field(..., max_length=50)
    grade: str | None = Field(
        None, pattern=r"^(grade[012])$"
    )  # grade0/grade1/grade2


class TranslateResponse(BaseModel):
    """Çeviri API yanıtı."""

    braille: str
    table_id: str
    char_count: int
    direction: str = "text_to_braille"


class BackTranslateRequest(BaseModel):
    """Braille → metin geri çeviri isteği."""

    braille: str = Field(..., min_length=1, max_length=500_000)
    table_id: str = Field(..., max_length=50)


class BackTranslateResponse(BaseModel):
    """Geri çeviri API yanıtı."""

    text: str
    table_id: str
    char_count: int
    direction: str = "braille_to_text"