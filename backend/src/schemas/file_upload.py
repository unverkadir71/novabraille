# File upload Pydantic schemas
#
# Request/response models for the file upload endpoints.
# Plan v9 referansı: Faz 2.3 — Dosya İşleme (ADR-008)

from __future__ import annotations

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Dosya yükleme ve metin çıkarma API yanıtı."""

    text: str = Field(..., description="Çıkarılan düz metin")
    char_count: int = Field(..., description="Metin karakter sayısı")
    input_format: str = Field(..., description="Tespit edilen dosya formatı (txt/docx/rtf/pdf)")
    original_filename: str = Field(..., description="Orijinal dosya adı")
    file_size_bytes: int = Field(..., description="Dosya boyutu (bayt)")


class FileFormatInfo(BaseModel):
    """Desteklenen dosya formatı bilgisi."""

    format: str = Field(..., description="Format tanımlayıcısı (txt, docx, rtf, pdf)")
    label_tr: str = Field(..., description="Türkçe etiket")
    label_en: str = Field(..., description="İngilizce etiket")
    extensions: list[str] = Field(..., description="Desteklenen uzantılar")
    mime_types: list[str] = Field(..., description="Desteklenen MIME türleri")
    requires_pandoc: bool = Field(False, description="Pandoc gerektirir mi?")
    requires_pymupdf: bool = Field(False, description="PyMuPDF gerektirir mi?")


class FileUploadError(BaseModel):
    """Dosya yükleme hatası detayı."""

    code: str = Field(..., description="Hata kodu")
    message: str = Field(..., description="Kullanıcıya uygun hata mesajı")
    detail: str | None = Field(None, description="Teknik detay (opsiyonel)")