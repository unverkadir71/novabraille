# Dosya İşleme Modülü (v3 — 9 format)
#
# Plan v10: Mantık hatası düzeltmesi (2026-08-31)
# Braille formatları (MegaDots, EDGAR) girdiden çıkarıldı — zaten Braille içeriyorlar.
# ICADD (ölü format), WPD (gereksiz LibreOffice), LaTeX (MathCAT ile geri dönecek) çıkarıldı.
#
# Desteklenen formatlar (9):
#   TXT        → Doğrudan okuma
#   DOCX       → Pandoc (subprocess)
#   RTF        → Pandoc (subprocess)
#   PDF        → PyMuPDF (dijital), Tesseract OCR (taranmış fallback)
#   ODT        → Pandoc (subprocess)
#   HTML       → Pandoc veya lxml (subprocess/Python)
#   DOC        → LibreOffice headless (subprocess)
#   XLSX       → openpyxl (Python)
#   DAISY/NIMAS→ lxml DTBook parser (DAISY Pipeline kullanılmaz)
#
# Tüm araçlar ücretsiz/açık kaynak, AGPL-3.0 uyumlu.

from __future__ import annotations

import re
import subprocess
import tempfile
from enum import StrEnum
from pathlib import Path


class InputFormat(StrEnum):
    """Desteklenen dosya giriş formatları."""

    TXT = "txt"
    DOCX = "docx"
    RTF = "rtf"
    PDF = "pdf"
    ODT = "odt"
    HTML = "html"
    DOC = "doc"
    XLSX = "xlsx"
    DAISY = "daisy"        # DAISY/NIMAS (DTBook XML) — lxml parser, Pipeline YOK

    @classmethod
    def from_extension(cls, filename: str) -> InputFormat | None:
        """Dosya adı uzantısından formatı belirle."""
        suffix = Path(filename).suffix.lower().lstrip(".")
        try:
            return cls(suffix)
        except ValueError:
            # Özel eşleştirmeler
            special = {
                "htm": cls.HTML,
                "xls": cls.XLSX,
            }
            return special.get(suffix)

    @classmethod
    def from_content_type(cls, content_type: str) -> InputFormat | None:
        """Content-Type başlığından formatı belirle."""
        mapping: dict[str, InputFormat] = {
            "text/plain": cls.TXT,
            "text/html": cls.HTML,
            "application/xhtml+xml": cls.HTML,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": cls.DOCX,
            "application/rtf": cls.RTF,
            "text/rtf": cls.RTF,
            "application/pdf": cls.PDF,
            "application/vnd.oasis.opendocument.text": cls.ODT,
            "application/msword": cls.DOC,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": cls.XLSX,
            "application/x-dtbook+xml": cls.DAISY,
            "application/x-daisy-nimas": cls.DAISY,
        }
        clean_type = content_type.split(";")[0].strip().lower()
        return mapping.get(clean_type)


# ---------------------------------------------------------------------------
# Hata sınıfları
# ---------------------------------------------------------------------------


class FileProcessingError(Exception):
    """Dosya işleme hatalarının taban sınıfı."""


class UnsupportedFormatError(FileProcessingError):
    def __init__(self, format_hint: str) -> None:
        self.format_hint = format_hint
        super().__init__(
            f"Unsupported file format: {format_hint!r}. "
            f"Supported: {[f.value for f in InputFormat]}"
        )


class PandocNotFoundError(FileProcessingError):
    def __init__(self) -> None:
        super().__init__("Pandoc is not installed.")


class PandocConversionError(FileProcessingError):
    def __init__(self, input_format: str, stderr: str) -> None:
        self.input_format = input_format
        self.stderr = stderr
        super().__init__(f"Pandoc conversion failed for {input_format}: {stderr.strip()}")


class PDFExtractionError(FileProcessingError):
    def __init__(self, original_error: Exception) -> None:
        self.original_error = original_error
        super().__init__(f"PDF text extraction failed: {original_error}")


class FileTooLargeError(FileProcessingError):
    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        super().__init__(f"File size {size_bytes} exceeds maximum {max_bytes} bytes")


class LibreOfficeError(FileProcessingError):
    def __init__(self, stderr: str) -> None:
        self.stderr = stderr
        super().__init__(f"LibreOffice conversion failed: {stderr.strip()}")


class OCRError(FileProcessingError):
    def __init__(self, original_error: Exception) -> None:
        super().__init__(f"OCR failed: {original_error}")


# ---------------------------------------------------------------------------
# FileProcessor
# ---------------------------------------------------------------------------


class FileProcessor:
    """Belge dosyalarını düz metine dönüştüren işlemci (15 format)."""

    PANDOC_WRITER = "plain"
    DEFAULT_MAX_FILE_BYTES = 50 * 1024 * 1024
    PANDOC_TIMEOUT = 30
    LIBREOFFICE_TIMEOUT = 60
    TESSERACT_TIMEOUT = 120

    def __init__(self, max_file_bytes: int | None = None) -> None:
        self.max_file_bytes = max_file_bytes or self.DEFAULT_MAX_FILE_BYTES

    def extract_text(self, file_path: str | Path, input_format: InputFormat) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        size = path.stat().st_size
        if size > self.max_file_bytes:
            raise FileTooLargeError(size, self.max_file_bytes)

        # Routing
        if input_format == InputFormat.TXT:
            return self._extract_txt(path)
        if input_format in (InputFormat.DOCX, InputFormat.RTF, InputFormat.ODT):
            return self._extract_via_pandoc(path, input_format)
        if input_format == InputFormat.HTML:
            return self._extract_html(path)
        if input_format == InputFormat.PDF:
            return self._extract_pdf_with_ocr_fallback(path)
        if input_format == InputFormat.DOC:
            return self._extract_via_libreoffice(path, input_format)
        if input_format == InputFormat.XLSX:
            return self._extract_xlsx(path)
        if input_format == InputFormat.DAISY:
            return self._extract_daisy(path)

        raise UnsupportedFormatError(input_format.value)

    def extract_text_from_bytes(self, data: bytes, input_format: InputFormat) -> str:
        if len(data) > self.max_file_bytes:
            raise FileTooLargeError(len(data), self.max_file_bytes)
        if input_format == InputFormat.TXT:
            return data.decode("utf-8", errors="replace")
        suffix = f".{input_format.value}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            return self.extract_text(tmp_path, input_format)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # ── TXT ───────────────────────────────────────────────────

    def _extract_txt(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")

    # ── Pandoc (DOCX, RTF, ODT) ──────────────────────────────

    def _extract_via_pandoc(self, path: Path, input_format: InputFormat) -> str:
        self._ensure_pandoc_available()
        # Pandoc: docx/rtf için format adı, odt için "odt"
        fmt = input_format.value
        cmd = ["pandoc", str(path), "--from", fmt, "--to", self.PANDOC_WRITER, "--wrap=none"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.PANDOC_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise PandocConversionError(input_format.value, f"Pandoc timed out after {self.PANDOC_TIMEOUT}s") from None
        except FileNotFoundError:
            raise PandocNotFoundError() from None
        if result.returncode != 0:
            raise PandocConversionError(input_format.value, result.stderr)
        return result.stdout

    # ── HTML ───────────────────────────────────────────────────

    def _extract_html(self, path: Path) -> str:
        """HTML'den metin çıkar. Önce Pandoc dener, yoksa lxml'e düşer."""
        if self._is_pandoc_available():
            try:
                return self._extract_via_pandoc(path, InputFormat("html"))
            except PandocConversionError:
                pass
        return self._extract_html_via_lxml(path)

    def _extract_html_via_lxml(self, path: Path) -> str:
        try:
            from lxml import html as lxml_html  # noqa: F811
        except ImportError:
            raise FileProcessingError("lxml is not installed for HTML processing.") from None
        doc = lxml_html.parse(str(path))
        # Remove script/style tags
        for bad in doc.xpath("//script|//style"):
            bad.getparent().remove(bad)  # type: ignore[union-attr]
        text = doc.xpath("//body")[0].text_content() if doc.xpath("//body") else doc.text_content()
        # Collapse whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()

    # ── LibreOffice (DOC) ─────────────────────────────────

    def _extract_via_libreoffice(self, path: Path, input_format: InputFormat) -> str:
        self._ensure_libreoffice_available()
        out_dir = tempfile.mkdtemp(prefix="lo-out-")
        try:
            cmd = [
                "libreoffice", "--headless", "--norestore",
                "--convert-to", "txt:Text",
                "--outdir", out_dir,
                str(path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.LIBREOFFICE_TIMEOUT)
            if result.returncode != 0:
                raise LibreOfficeError(result.stderr)
            # Find output file
            out_files = list(Path(out_dir).glob("*.txt"))
            if not out_files:
                raise LibreOfficeError("No output file produced")
            return out_files[0].read_text(encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            raise LibreOfficeError(f"LibreOffice timed out after {self.LIBREOFFICE_TIMEOUT}s") from None
        except FileNotFoundError:
            raise FileProcessingError("LibreOffice is not installed.") from None
        finally:
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)

    # ── XLSX ──────────────────────────────────────────────────

    def _extract_xlsx(self, path: Path) -> str:
        try:
            import openpyxl  # noqa: F811
        except ImportError:
            raise FileProcessingError("openpyxl is not installed.") from None
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        parts: list[str] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            parts.append(f"[{sheet_name}]")
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(cells):
                    parts.append("\t".join(cells))
            parts.append("")
        wb.close()
        return "\n".join(parts).strip()

    # ── PDF (PyMuPDF + Tesseract OCR fallback) ────────────────

    def _extract_pdf_with_ocr_fallback(self, path: Path) -> str:
        try:
            return self._extract_pdf_pymupdf(path)
        except (PDFExtractionError, FileProcessingError):
            pass
        # Dijital PDF'ten metin gelmediyse OCR dene
        try:
            return self._extract_pdf_ocr(path)
        except FileProcessingError:
            raise PDFExtractionError(Exception("PDF'ten metin çıkarılamadı. OCR da başarısız oldu."))

    def _extract_pdf_pymupdf(self, path: Path) -> str:
        try:
            import pymupdf  # noqa: F811
        except ImportError:
            raise FileProcessingError("PyMuPDF not installed.") from None
        try:
            doc = pymupdf.open(str(path))
        except Exception as e:
            raise PDFExtractionError(e) from e
        try:
            pages = []
            for page in doc:  # type: ignore[attr-defined]
                text = page.get_text()  # type: ignore[attr-defined]
                if text:
                    pages.append(text)
            result = "\n".join(pages).strip()
            if not result:
                raise PDFExtractionError(Exception("No text found in PDF"))
            return result
        except Exception as e:
            raise PDFExtractionError(e) from e
        finally:
            doc.close()

    def _extract_pdf_ocr(self, path: Path) -> str:
        self._ensure_tesseract_available()
        # Convert PDF pages to images then OCR
        try:
            import pymupdf  # noqa: F811
        except ImportError:
            raise OCRError(Exception("PyMuPDF not installed for OCR")) from None
        try:
            doc = pymupdf.open(str(path))
        except Exception as e:
            raise OCRError(e) from e
        texts = []
        # 8 öncelikli dil kodu — tessdata_best kullan (en yüksek doğruluk)
        ocr_langs = "tur+eng+deu+fra+spa+ara+rus+por"
        tessdata_dir = "/usr/share/tesseract-ocr/5/tessdata_best"
        # Eğer tessdata_best yoksa fallback
        if not Path(tessdata_dir, "eng.traineddata").exists():
            tessdata_dir = "/usr/share/tesseract-ocr/5/tessdata"
        try:
            for i, page in enumerate(doc):  # type: ignore[attr-defined]
                pix = page.get_pixmap(dpi=300)
                img_path = Path(tempfile.gettempdir()) / f"nova-ocr-page-{i}.png"
                pix.save(str(img_path))
                try:
                    result = subprocess.run(
                        ["tesseract", str(img_path), "stdout",
                         "-l", ocr_langs, "--psm", "6",
                         "--tessdata-dir", tessdata_dir, "--oem", "1"],
                        capture_output=True, text=True, timeout=self.TESSERACT_TIMEOUT,
                    )
                    if result.stdout.strip():
                        texts.append(result.stdout.strip())
                finally:
                    img_path.unlink(missing_ok=True)
        finally:
            doc.close()
        text = "\n".join(texts).strip()
        if not text:
            raise OCRError(Exception("Tesseract produced no text"))
        return text

    # ── DAISY/NIMAS ───────────────────────────────────────────

    def _extract_daisy(self, path: Path) -> str:
        """DAISY/NIMAS DTBook XML'den metin çıkar.

        lxml ile doğrudan parse eder. DAISY Pipeline kullanılmaz.
        Başarısız olursa Pandoc dener.
        """
        try:
            return self._extract_daisy_via_lxml(path)
        except Exception:
            if self._is_pandoc_available():
                try:
                    return self._extract_via_pandoc(path, InputFormat("html"))
                except PandocConversionError:
                    pass
            raise FileProcessingError("DAISY/NIMAS dosyası işlenemedi.")

    def _extract_daisy_via_lxml(self, path: Path) -> str:
        try:
            from lxml import etree
        except ImportError:
            raise FileProcessingError("lxml not installed.") from None
        content = path.read_bytes()
        # Try parsing as XML
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError:
            raise FileProcessingError("Invalid DAISY/NIMAS XML")
        # Extract all text nodes
        texts = root.xpath("//text()")
        # Filter out whitespace-only
        lines = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
        return "\n".join(lines)

    # ── Yardımcı metotlar ─────────────────────────────────────

    @staticmethod
    def _ensure_pandoc_available() -> None:
        try:
            subprocess.run(["pandoc", "--version"], capture_output=True, timeout=5, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise PandocNotFoundError() from None

    @classmethod
    def is_pandoc_available(cls) -> bool:
        """Pandoc'un sistemde kurulu olup olmadığını kontrol et."""
        return cls._is_pandoc_available()

    @classmethod
    def _is_pandoc_available(cls) -> bool:
        try:
            cls._ensure_pandoc_available()
            return True
        except PandocNotFoundError:
            return False

    @staticmethod
    def _ensure_libreoffice_available() -> None:
        try:
            subprocess.run(["libreoffice", "--version"], capture_output=True, timeout=10, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise FileProcessingError("LibreOffice is not installed.") from None

    @staticmethod
    def _ensure_tesseract_available() -> None:
        try:
            subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise FileProcessingError("Tesseract OCR is not installed.") from None

    @classmethod
    def get_pandoc_version(cls) -> str | None:
        try:
            result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, timeout=5, check=False)
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
