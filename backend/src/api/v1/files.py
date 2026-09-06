# File upload router — /api/v1/files
#
# Plan v10: 9 format (mantık hatası düzeltmesi sonrası)
#
# Endpoint'ler:
#   GET  /api/v1/files/formats   — desteklenen formatları listele
#   POST /api/v1/files/upload    — dosya yükle, metin çıkar
#   POST /api/v1/files/translate — dosya yükle + Braille'e çevir (birleşik)

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from ...config import settings
from ...schemas.file_upload import FileFormatInfo, FileUploadResponse
from ...schemas.translation import TranslateResponse
from ...services.audit import audit_log
from ...services.translation import translation_service
from ...translation import FileProcessor, InputFormat
from ...translation.file_processor import (
    FileProcessingError,
    FileTooLargeError,
    PandocConversionError,
    PandocNotFoundError,
    PDFExtractionError,
    UnsupportedFormatError,
)
from .deps import CurrentUser

router = APIRouter(prefix="/files", tags=["files"])

# ── Desteklenen format tanımları ────────────────────────────────────────

_SUPPORTED_FORMATS: list[FileFormatInfo] = [
    FileFormatInfo(
        format="txt", label_tr="Düz Metin", label_en="Plain Text",
        extensions=[".txt"], mime_types=["text/plain"],
        requires_pandoc=False, requires_pymupdf=False,
    ),
    FileFormatInfo(
        format="docx", label_tr="Microsoft Word", label_en="Microsoft Word",
        extensions=[".docx"],
        mime_types=["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        requires_pandoc=True, requires_pymupdf=False,
    ),
    FileFormatInfo(
        format="doc", label_tr="Microsoft Word (eski)", label_en="Microsoft Word (legacy)",
        extensions=[".doc"], mime_types=["application/msword"],
        requires_pandoc=False, requires_pymupdf=False,
    ),
    FileFormatInfo(
        format="odt", label_tr="OpenDocument Metin", label_en="OpenDocument Text",
        extensions=[".odt"], mime_types=["application/vnd.oasis.opendocument.text"],
        requires_pandoc=True, requires_pymupdf=False,
    ),
    FileFormatInfo(
        format="rtf", label_tr="Zengin Metin (RTF)", label_en="Rich Text Format",
        extensions=[".rtf"], mime_types=["application/rtf", "text/rtf"],
        requires_pandoc=True, requires_pymupdf=False,
    ),
    FileFormatInfo(
        format="xlsx", label_tr="Microsoft Excel", label_en="Microsoft Excel",
        extensions=[".xlsx", ".xls"],
        mime_types=["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
        requires_pandoc=False, requires_pymupdf=False,
    ),
    FileFormatInfo(
        format="html", label_tr="HTML / Web Sayfası", label_en="HTML / Web Page",
        extensions=[".html", ".htm"], mime_types=["text/html", "application/xhtml+xml"],
        requires_pandoc=False, requires_pymupdf=False,
    ),
    FileFormatInfo(
        format="pdf", label_tr="PDF Belgesi", label_en="PDF Document",
        extensions=[".pdf"], mime_types=["application/pdf"],
        requires_pandoc=False, requires_pymupdf=True,
    ),
    FileFormatInfo(
        format="daisy", label_tr="DAISY/NIMAS Kitap", label_en="DAISY/NIMAS Book",
        extensions=[".xml"],
        mime_types=["application/x-dtbook+xml", "application/x-daisy-nimas"],
        requires_pandoc=False, requires_pymupdf=False,
    ),
]


# ── İç yardımcı ─────────────────────────────────────────────────────────


@dataclass
class _ExtractedContent:
    """Dosyadan çıkarılan içerik metadata'sı."""

    text: str
    input_format: InputFormat
    original_filename: str
    file_size_bytes: int


async def _extract_text_from_upload(file: UploadFile) -> _ExtractedContent:
    """Dosyayı doğrula ve metin çıkar.

    Bu fonksiyon upload ve translate endpoint'leri tarafından ortak kullanılır.
    Kimlik doğrulama çağıran fonksiyonun sorumluluğundadır.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "MISSING_FILENAME",
                "message": "Dosya adı gerekli.",
            },
        )

    # Format tespiti (Content-Type öncelikli, sonra uzantı)
    content_type = file.content_type or ""
    input_format = InputFormat.from_content_type(content_type)
    if input_format is None:
        input_format = InputFormat.from_extension(file.filename)
    if input_format is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "UNSUPPORTED_FORMAT",
                "message": (
                    f"Dosya formatı desteklenmiyor: {file.filename!r}. "
                    "Desteklenen: txt, docx, doc, odt, rtf, xlsx, html, pdf, daisy/nimas."
                ),
            },
        )

    max_bytes = settings.max_file_upload_bytes

    # Dosyayı belleğe oku
    try:
        data = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={"code": "FILE_READ_ERROR", "message": f"Dosya okunamadı: {e}"},
        ) from e

    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": (
                    f"Dosya boyutu ({len(data):,} bayt) maksimum "
                    f"dosya boyutunu ({max_bytes:,} bayt) aşıyor."
                ),
            },
        )

    # TXT — doğrudan bellekte
    if input_format == InputFormat.TXT:
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.decode("latin-1", errors="replace")
        _validate_extracted_text(text)
        return _ExtractedContent(
            text=text,
            input_format=input_format,
            original_filename=file.filename,
            file_size_bytes=len(data),
        )

    # TXT dışındaki tüm formatlar — geçici dosya
    suffix = f".{input_format.value}"
    tmp_path = Path(gettempdir()) / f"nova-braille-upload-{uuid.uuid4().hex[:12]}{suffix}"
    try:
        tmp_path.write_bytes(data)
        processor = FileProcessor(max_file_bytes=max_bytes)
        text = processor.extract_text(tmp_path, input_format)
    except FileTooLargeError as e:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": str(e)},
        ) from e
    except PandocNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"code": "PANDOC_NOT_AVAILABLE", "message": str(e)},
        ) from e
    except PandocConversionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CONVERSION_FAILED",
                "message": f"{input_format.value.upper()} dönüşümü başarısız: {e}",
            },
        ) from e
    except PDFExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PDF_EXTRACTION_FAILED",
                "message": f"PDF metin çıkarma başarısız: {e}",
            },
        ) from e
    except (FileProcessingError, UnsupportedFormatError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "PROCESSING_ERROR", "message": str(e)},
        ) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    _validate_extracted_text(text)
    return _ExtractedContent(
        text=text,
        input_format=input_format,
        original_filename=file.filename,
        file_size_bytes=len(data),
    )


def _validate_extracted_text(text: str) -> None:
    """Çıkarılan metni doğrula — boş değil ve karakter sınırı içinde."""
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "EMPTY_CONTENT",
                "message": (
                    "Dosyadan metin çıkarılamadı. "
                    "Dosya boş, taranmış PDF veya desteklenmeyen biçimde olabilir."
                ),
            },
        )

    if len(text) > settings.max_translation_chars:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "TEXT_TOO_LONG",
                "message": (
                    f"Çıkarılan metin ({len(text):,} karakter) "
                    f"maksimum çeviri boyutunu "
                    f"({settings.max_translation_chars:,}) aşıyor."
                ),
            },
        )


# ── Endpoint'ler ────────────────────────────────────────────────────────


@router.get("/formats", summary="Desteklenen dosya formatlarını listele")
async def list_formats() -> list[FileFormatInfo]:
    """Dosya yükleme için desteklenen formatları ve gereksinimlerini döner."""
    return _SUPPORTED_FORMATS


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=200,
    summary="Dosya yükle ve metin çıkar",
)
async def upload_file(
    file: UploadFile,
    current_user: CurrentUser,  # noqa: ARG001
) -> FileUploadResponse:
    """Desteklenen herhangi bir formatta dosya yükle ve düz metin çıkar.

    9 format desteklenir: txt, docx, doc, odt, rtf, xlsx, html, pdf, daisy/nimas.

    Kimlik doğrulama gerektirir. Maksimum dosya boyutu: 50 MB.
    """
    content = await _extract_text_from_upload(file)

    audit_log.file_uploaded(
        current_user.id,
        content.original_filename,
        content.input_format.value,
        content.file_size_bytes,
    )

    return FileUploadResponse(
        text=content.text,
        char_count=len(content.text),
        input_format=content.input_format.value,
        original_filename=content.original_filename,
        file_size_bytes=content.file_size_bytes,
    )


@router.post(
    "/translate",
    response_model=TranslateResponse,
    status_code=200,
    summary="Dosya yükle ve Braille'e çevir",
)
async def upload_and_translate(
    file: UploadFile,
    table_id: Annotated[str, Query(description="Braille tablosu kimliği")],
    grade: Annotated[str | None, Query(description="Kısaltma düzeyi (grade0/1/2)")] = None,
    current_user: CurrentUser = None,  # noqa: ARG001
) -> TranslateResponse:
    """Dosya yükle, metin çıkar ve doğrudan Braille'e çevir.

    upload + translate işlemlerini tek adımda birleştirir.
    """
    # Dosyadan metin çıkar
    content = await _extract_text_from_upload(file)

    # Braille'e çevir
    try:
        result = await translation_service.translate(
            content.text,
            table_id,
            grade=grade,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_INPUT", "message": str(e)},
        ) from e

    # Audit
    audit_log.file_uploaded(
        current_user.id,
        content.original_filename,
        content.input_format.value,
        content.file_size_bytes,
    )
    audit_log.translation_completed(
        current_user.id, table_id, result.char_count
    )

    return TranslateResponse(
        braille=result.text,
        table_id=result.table_id,
        char_count=result.char_count,
    )
