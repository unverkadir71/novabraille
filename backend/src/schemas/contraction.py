# Contraction (kısaltma) API schemas
#
# Plan v9 referansı: Bölüm 1.10.5 — Kısaltma Sistemi (ADR-008)

from __future__ import annotations

from pydantic import BaseModel, Field


class ContractionLevelItem(BaseModel):
    """API yanıtında tek bir kısaltma düzeyi."""

    id: str = Field(..., description="Benzersiz tanımlayıcı (örn. full_write, contracted)")
    label_tr: str = Field(..., description="Türkçe etiket")
    label_en: str = Field(..., description="İngilizce etiket")
    description_tr: str = Field(..., description="Türkçe açıklama")
    description_en: str = Field(..., description="İngilizce açıklama")


class ContractionProfileItem(BaseModel):
    """API yanıtında bir dilin kısaltma profili."""

    language_code: str = Field(..., description="ISO 639-1 dil kodu")
    language_name_tr: str = Field(..., description="Türkçe dil adı")
    language_name_en: str = Field(..., description="İngilizce dil adı")
    supports_contraction: bool = Field(..., description="Dilde kısaltma sistemi var mı?")
    default_level_id: str = Field(..., description="Varsayılan kısaltma düzeyi ID'si")
    levels: list[ContractionLevelItem] = Field(..., description="Mevcut kısaltma düzeyleri")
    info_message_tr: str | None = Field(None, description="Türkçe özel bilgi mesajı")
    info_message_en: str | None = Field(None, description="İngilizce özel bilgi mesajı")


class ContractionCategoryItem(BaseModel):
    """API yanıtında tek bir kısaltma kategorisi (checkbox seçimi için)."""

    id: str = Field(..., description="Benzersiz tanımlayıcı (örn. single_letter, word_stem)")
    label_tr: str = Field(..., description="Türkçe etiket")
    label_en: str = Field(..., description="İngilizce etiket")
    description_tr: str = Field(..., description="Türkçe açıklama")
    description_en: str = Field(..., description="İngilizce açıklama")
    sort_order: int = Field(0, description="Sıralama")