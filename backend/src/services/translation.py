# Translation service — business logic layer for Braille translation
#
# Orchestrates table validation, character limits, and Liblouis calls.
# Plan v9 referansı: Faz 2.2 — Çeviri Motoru

from __future__ import annotations

from dataclasses import dataclass

import structlog

from ..config import settings
from ..translation import (
    TranslationMode,
    get_allowlist,
    get_manifest,
    liblouis_wrapper,
)
from ..translation.exceptions import (
    EmptyInputError,
    TableNotFoundError,
    TranslationFailedError,
)
from ..translation.table_manifest import TableAllowlist

logger = structlog.get_logger("nova_braille.translation")

# ── Sonuç veri sınıfı ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TranslateOutput:
    """Çeviri sonucu (servis katmanı)."""

    text: str
    """Çevrilmiş metin."""

    table_id: str
    """Kullanılan tablo kimliği."""

    char_count: int
    """Çıktı karakter sayısı."""

    direction: str
    """'text_to_braille' | 'braille_to_text'."""


# ── Limit kontrolü ──────────────────────────────────────────────────────


@dataclass
class CharLimit:
    """Çeviri karakter sınır kontrolü.

    Hosted modda abonelik planına bağlı; self-hosted'da sınırsız.
    """

    max_per_request: int = settings.max_translation_chars
    """Tek istekte izin verilen maksimum karakter sayısı."""

    def check(self, text: str) -> None:
        """Metin boyutunu kontrol eder.

        Args:
            text: Girdi metni.

        Raises:
            ValueError: Sınır aşıldıysa.
        """
        char_count = len(text)
        if char_count > self.max_per_request:
            raise ValueError(
                f"Text too long: {char_count} characters (max {self.max_per_request})"
            )

        if char_count == 0:
            raise ValueError("Text is empty")


# ── TranslationService ────────────────────────────────────────────────────


class TranslationService:
    """Çeviri iş mantığı servisi.

    Liblouis çağrılarını izole eder; güvenlik (allowlist), limit kontrolü
    ve hata yönetimi sağlar.

    Kullanım:
        svc = TranslationService()
        result = await svc.translate("Merhaba dünya", "tr-g2.tbl")
    """

    def __init__(self) -> None:
        self._allowlist: TableAllowlist = get_allowlist()
        self._limit = CharLimit()

    # ── Public API ─────────────────────────────────────────────────────

    async def translate(
        self,
        text: str,
        table_id: str,
        *,
        grade: str | None = None,
    ) -> TranslateOutput:
        """Metni Braille'e çevirir.

        Args:
            text: Çevrilecek metin.
            table_id: Braille tablo kimliği.
            grade: İsteğe bağlı kısaltma düzeyi (grade0/grade1/grade2).

        Returns:
            TranslateOutput.

        Raises:
            ValueError: Girdi çok uzun, boş veya tablo izin verilmiyorsa.
            EmptyInputError: Girdi boşsa.
            TranslationFailedError: Liblouis çeviri hatası.
        """
        # Limit kontrolü
        self._limit.check(text)

        # Güvenlik: tablo allowlist doğrulaması
        self._allowlist.validate(table_id)

        # Kısaltma düzeyine göre mod seçimi
        mode = TranslationMode.NONE
        if grade == "grade1":
            mode = TranslationMode.NO_CONTRACTIONS
        elif grade == "grade0":
            mode = TranslationMode.COMPUTER_BRAILLE

        logger.info(
            "translate_start",
            table_id=table_id,
            char_count=len(text),
            grade=grade,
        )

        try:
            result = liblouis_wrapper.translate(
                text,
                table_id,
                mode=mode,
            )
        except EmptyInputError:
            raise
        except (TableNotFoundError, TranslationFailedError) as e:
            logger.error("translate_failed", table_id=table_id, error=str(e))
            raise

        logger.info(
            "translate_done",
            table_id=table_id,
            input_chars=len(text),
            output_chars=result.char_count,
        )

        return TranslateOutput(
            text=result.text,
            table_id=result.table_id,
            char_count=result.char_count,
            direction="text_to_braille",
        )

    async def back_translate(
        self,
        braille: str,
        table_id: str,
    ) -> TranslateOutput:
        """Braille'i düz metne geri çevirir.

        Args:
            braille: Braille Unicode metni.
            table_id: Braille tablo kimliği.

        Returns:
            TranslateOutput.

        Raises:
            ValueError: Girdi çok uzun, boş veya tablo izin verilmiyorsa.
            EmptyInputError: Girdi boşsa.
            TranslationFailedError: Liblouis geri çeviri hatası.
        """
        # Limit kontrolü
        self._limit.check(braille)

        # Güvenlik: tablo allowlist doğrulaması
        self._allowlist.validate(table_id)

        logger.info(
            "back_translate_start",
            table_id=table_id,
            char_count=len(braille),
        )

        try:
            result = liblouis_wrapper.back_translate(braille, table_id)
        except EmptyInputError:
            raise
        except (TableNotFoundError, TranslationFailedError) as e:
            logger.error("back_translate_failed", table_id=table_id, error=str(e))
            raise

        logger.info(
            "back_translate_done",
            table_id=table_id,
            input_chars=len(braille),
            output_chars=result.char_count,
        )

        return TranslateOutput(
            text=result.text,
            table_id=result.table_id,
            char_count=result.char_count,
            direction="braille_to_text",
        )

    # ── Yardımcı metotlar ─────────────────────────────────────────────

    def get_tables_for_language(self, language: str) -> list[str]:
        """Bir dile ait tablo ID'lerini döner."""
        manifest = get_manifest()
        entries = manifest.filter(language=language, priority_languages_only=True)
        return [e.id for e in entries]

    def validate_table(self, table_id: str) -> None:
        """Tablo ID'sini doğrular ya da ValueError fırlatır."""
        self._allowlist.validate(table_id)

    def get_back_translation_tables(self, language: str | None = None) -> list[str]:
        """Geri çeviri (back-translation) destekleyen tabloları listeler."""
        manifest = get_manifest()
        entries = manifest.filter(
            language=language,
            back_translation=True,
            priority_languages_only=language is not None,
        )
        return [e.id for e in entries]


# ── Singleton ──────────────────────────────────────────────────────────────

translation_service = TranslationService()