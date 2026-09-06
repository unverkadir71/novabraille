# Output format API schemas
#
# Plan v9 referansı: Bölüm 1.10.4-1.10.6 — Combo Box, Çıktı Formatları (ADR-008)
# v2: OutputFileFormat eklendi — her mod için desteklenen dosya formatları

from __future__ import annotations

from pydantic import BaseModel, Field


class PageLayoutItem(BaseModel):
    """API yanıtında sayfa düzeni."""

    id: str = Field(..., description="Hazır düzen adı (a4, a4_landscape, letter)")
    label_tr: str = Field(..., description="Türkçe etiket")
    label_en: str = Field(..., description="İngilizce etiket")
    chars_per_line: int = Field(..., description="Satır başına karakter (hücre)")
    lines_per_page: int = Field(..., description="Sayfa başına satır")


class OutputFileFormat(BaseModel):
    """Bir çıktı modu için desteklenen dosya formatı."""

    id: str = Field(..., description="Format tanımlayıcısı (txt, brf, brl)")
    label_tr: str = Field(..., description="Türkçe etiket")
    label_en: str = Field(..., description="İngilizce etiket")
    extension: str = Field(..., description="Dosya uzantısı (.txt, .brf, .brl)")
    description_tr: str = Field(..., description="Türkçe açıklama")
    description_en: str = Field(..., description="İngilizce açıklama")
    recommended: bool = Field(False, description="Bu mod için önerilen format")


class OutputModeItem(BaseModel):
    """API yanıtında çıktı modu seçeneği."""

    id: str = Field(..., description="Mod tanımlayıcısı (display, embosser, notetaker)")
    label_tr: str = Field(..., description="Türkçe etiket")
    label_en: str = Field(..., description="İngilizce etiket")
    file_formats: list[OutputFileFormat] = Field(
        default_factory=list,
        description="Bu mod için desteklenen dosya formatları",
    )


class FileDownloadResponse(BaseModel):
    """Dosya indirme yanıtı — base64 kodlu dosya içeriği."""

    content_base64: str = Field(..., description="Base64 kodlu dosya içeriği")
    filename: str = Field(..., description="Önerilen dosya adı")
    mime_type: str = Field(..., description="MIME türü")
    byte_size: int = Field(..., description="Dosya boyutu (bayt)")
    output_format: str = Field(..., description="brf, brl veya txt")