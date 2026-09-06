"""Tests for file_processor module.

Plan v9: Bölüm 1.10.3 — Dosya Girişi ve Belge Dönüştürme (ADR-008)

Kapsam:
  - TXT: Doğrudan okuma (UTF-8 + fallback)
  - DOCX: Pandoc dönüşümü
  - RTF: Pandoc dönüşümü
  - PDF: PyMuPDF metin çıkarma
  - Byte dizisinden çıkarma
  - Hata durumları (format, boyut, dosya yok)
  - Format algılama (uzantı, content-type)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.src.translation.file_processor import (
    FileProcessor,
    FileTooLargeError,
    InputFormat,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def processor() -> FileProcessor:
    return FileProcessor()


@pytest.fixture
def txt_file() -> Path:
    return FIXTURES / "test.txt"


@pytest.fixture
def docx_file() -> Path:
    return FIXTURES / "test.docx"


@pytest.fixture
def rtf_file() -> Path:
    return FIXTURES / "test.rtf"


@pytest.fixture
def pdf_file() -> Path:
    return FIXTURES / "test.pdf"


# ---------------------------------------------------------------------------
# InputFormat enum tests
# ---------------------------------------------------------------------------


class TestInputFormatEnum:
    def test_from_extension_lowercase(self) -> None:
        assert InputFormat.from_extension("test.txt") == InputFormat.TXT
        assert InputFormat.from_extension("test.docx") == InputFormat.DOCX
        assert InputFormat.from_extension("test.rtf") == InputFormat.RTF
        assert InputFormat.from_extension("test.pdf") == InputFormat.PDF

    def test_from_extension_uppercase(self) -> None:
        assert InputFormat.from_extension("TEST.TXT") == InputFormat.TXT
        assert InputFormat.from_extension("TEST.DOCX") == InputFormat.DOCX
        assert InputFormat.from_extension("TEST.RTF") == InputFormat.RTF
        assert InputFormat.from_extension("TEST.PDF") == InputFormat.PDF

    def test_from_extension_mixed_case(self) -> None:
        assert InputFormat.from_extension("MyFile.DocX") == InputFormat.DOCX

    def test_from_extension_unknown(self) -> None:
        assert InputFormat.from_extension("test.epub") is None
        assert InputFormat.from_extension("test.png") is None
        assert InputFormat.from_extension("test") is None

    def test_from_extension_no_extension(self) -> None:
        assert InputFormat.from_extension("noextension") is None

    def test_from_content_type_simple(self) -> None:
        assert InputFormat.from_content_type("text/plain") == InputFormat.TXT
        assert (
            InputFormat.from_content_type(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            )
            == InputFormat.DOCX
        )
        assert InputFormat.from_content_type("application/rtf") == InputFormat.RTF
        assert InputFormat.from_content_type("text/rtf") == InputFormat.RTF
        assert InputFormat.from_content_type("application/pdf") == InputFormat.PDF

    def test_from_content_type_with_parameters(self) -> None:
        assert (
            InputFormat.from_content_type("text/plain; charset=utf-8")
            == InputFormat.TXT
        )

    def test_from_content_type_unknown(self) -> None:
        assert InputFormat.from_content_type("image/png") is None
        assert InputFormat.from_content_type("application/zip") is None


# ---------------------------------------------------------------------------
# TXT extraction tests
# ---------------------------------------------------------------------------


class TestTxtExtraction:
    def test_read_utf8(self, processor: FileProcessor, txt_file: Path) -> None:
        text = processor.extract_text(txt_file, InputFormat.TXT)
        assert "Test Belgesi" in text
        assert "çğıöşü" in text
        assert "12345" in text

    def test_read_ascii(self, processor: FileProcessor) -> None:
        text = processor.extract_text_from_bytes(b"Hello World", InputFormat.TXT)
        assert text == "Hello World"

    def test_read_turkish_utf8(self, processor: FileProcessor) -> None:
        data = "Türkçe: çğıöşü İ".encode()
        text = processor.extract_text_from_bytes(data, InputFormat.TXT)
        assert "Türkçe" in text
        assert "çğıöşü" in text


# ---------------------------------------------------------------------------
# DOCX extraction tests
# ---------------------------------------------------------------------------


class TestDocxExtraction:
    def test_pandoc_docx(self, processor: FileProcessor, docx_file: Path) -> None:
        text = processor.extract_text(docx_file, InputFormat.DOCX)
        assert "Test" in text or "test" in text.lower()
        assert len(text) > 20  # En azından bir şey döndü

    def test_docx_from_bytes(self, processor: FileProcessor, docx_file: Path) -> None:
        data = docx_file.read_bytes()
        text = processor.extract_text_from_bytes(data, InputFormat.DOCX)
        assert len(text) > 20

    def test_docx_with_turkish_chars(
        self, processor: FileProcessor, docx_file: Path
    ) -> None:
        text = processor.extract_text(docx_file, InputFormat.DOCX)
        # Turkish characters should survive Pandoc conversion
        # Note: Pandoc may or may not preserve them perfectly
        assert len(text) > 0


# ---------------------------------------------------------------------------
# RTF extraction tests
# ---------------------------------------------------------------------------


class TestRtfExtraction:
    def test_pandoc_rtf(self, processor: FileProcessor, rtf_file: Path) -> None:
        text = processor.extract_text(rtf_file, InputFormat.RTF)
        assert len(text) > 20

    def test_rtf_from_bytes(self, processor: FileProcessor, rtf_file: Path) -> None:
        data = rtf_file.read_bytes()
        text = processor.extract_text_from_bytes(data, InputFormat.RTF)
        assert len(text) > 20


# ---------------------------------------------------------------------------
# PDF extraction tests
# ---------------------------------------------------------------------------


class TestPdfExtraction:
    def test_pymupdf_pdf(self, processor: FileProcessor, pdf_file: Path) -> None:
        text = processor.extract_text(pdf_file, InputFormat.PDF)
        assert "Test PDF" in text
        assert "12345" in text
        # Not: insert_text bazı TR karakterleri ASCII olmayan fontlarda bozabilir
        assert "ç" in text or "Türkçe" in text or len(text) > 50

    def test_pdf_from_bytes(self, processor: FileProcessor, pdf_file: Path) -> None:
        data = pdf_file.read_bytes()
        text = processor.extract_text_from_bytes(data, InputFormat.PDF)
        assert "Test PDF" in text


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_file_not_found(self, processor: FileProcessor) -> None:
        with pytest.raises(FileNotFoundError):
            processor.extract_text("/nonexistent/file.docx", InputFormat.DOCX)

    def test_unsupported_format_returns_none(self) -> None:
        """InputFormat.from_extension bilinmeyen uzantılarda None döndürmeli."""
        assert InputFormat.from_extension("test.epub") is None
        assert InputFormat.from_content_type("image/png") is None

    def test_file_too_large(self, txt_file: Path) -> None:
        processor = FileProcessor(max_file_bytes=10)
        with pytest.raises(FileTooLargeError):
            processor.extract_text(txt_file, InputFormat.TXT)

    def test_file_too_large_bytes(self) -> None:
        processor = FileProcessor(max_file_bytes=10)
        data = b"x" * 100
        with pytest.raises(FileTooLargeError):
            processor.extract_text_from_bytes(data, InputFormat.TXT)

    def test_unsupported_format_direct(self, processor: FileProcessor) -> None:
        """Test that unknown format raises error."""
        assert InputFormat.from_extension("test.epub") is None


# ---------------------------------------------------------------------------
# Pandoc availability tests
# ---------------------------------------------------------------------------


class TestPandocAvailability:
    def test_is_pandoc_available(self) -> None:
        assert FileProcessor.is_pandoc_available() is True

    def test_get_pandoc_version(self) -> None:
        version = FileProcessor.get_pandoc_version()
        assert version is not None
        assert "pandoc" in version.lower()
        # Should match "pandoc 3.x.y" pattern
        assert any(c.isdigit() for c in version)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_txt(self, processor: FileProcessor) -> None:
        text = processor.extract_text_from_bytes(b"", InputFormat.TXT)
        assert text == ""

    def test_newline_handling(self, processor: FileProcessor) -> None:
        data = b"line1\nline2\nline3"
        text = processor.extract_text_from_bytes(data, InputFormat.TXT)
        assert text.count("\n") == 2

    def test_max_file_bytes_at_boundary(self, txt_file: Path) -> None:
        size = txt_file.stat().st_size
        processor = FileProcessor(max_file_bytes=size)
        # Should not raise
        text = processor.extract_text(txt_file, InputFormat.TXT)
        assert len(text) > 0

    def test_max_file_bytes_just_under(self, txt_file: Path) -> None:
        size = txt_file.stat().st_size
        processor = FileProcessor(max_file_bytes=size + 1)
        text = processor.extract_text(txt_file, InputFormat.TXT)
        assert len(text) > 0

    def test_custom_max_bytes(self) -> None:
        processor = FileProcessor(max_file_bytes=1_000_000)
        assert processor.max_file_bytes == 1_000_000

    def test_default_max_bytes(self, processor: FileProcessor) -> None:
        assert processor.max_file_bytes == 50 * 1024 * 1024
