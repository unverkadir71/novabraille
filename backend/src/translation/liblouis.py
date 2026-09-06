# Liblouis Python binding wrapper
#
# Provides a type-safe, error-handling interface to the louis module.
# All Liblouis interaction goes through this module — nowhere else in the codebase.
#
# Plan v9 referansı: Faz 2.1.1 — Liblouis Python Binding Wrapper
# Liblouis sürümü: 3.38.0 (sistem kurulumu, /usr/local/share/liblouis/tables)
# Compatibility: Falls back for liblouis < 3.34 (Debian apt package)

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Literal, overload

import louis  # type: ignore[import-untyped]

from .exceptions import (
    EmptyInputError,
    TableCompileError,
    TableNotFoundError,
    TranslationFailedError,
)
from .types import (
    LANGUAGE_TABLE_MAP,
    BrailleGrade,
    TranslationDirection,
    TranslationMode,
)

logger = logging.getLogger(__name__)

# ── Tablo adı doğrulama deseni ───────────────────────────────────────────────
# Liblouis tablo adları: dil-kodu[-varyant].uzantı
# Örnek: tr-g2.tbl, en-ueb-g2.ctb, de-g1.ctb
_TABLE_NAME_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]+)*\.(?:ctb|utb|tbl|cti|uti|dis)$")

# Bilinen güvenli ek: listTables() dışındaki ama disk üzerinde mevcut tablolar
_KNOWN_TABLES_EXTRA: set[str] = {
    "tr-g2.ctb",
    "tr.ctb",
}


@dataclass(frozen=True, slots=True)
class TableInfo:
    """Bir Braille tablosu hakkında metadata."""

    id: str
    """Tablo kimliği (dosya adı, örn. 'tr-g2.tbl')."""

    file_name: str
    """Tam dosya adı."""

    language: str | None
    """ISO 639-1 dil kodu (örn. 'tr', 'en')."""

    grade: BrailleGrade | None
    """Braille kısaltma düzeyi (grade0/1/2)."""

    is_contracted: bool
    """Kısaltmalı mı?"""


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """Çeviri sonucu."""

    text: str
    """Çevrilmiş metin (Braille Unicode veya düz metin)."""

    table_id: str
    """Kullanılan tablo kimliği."""

    direction: TranslationDirection
    """Çeviri yönü."""

    char_count: int
    """Çıktı karakter sayısı."""


class LiblouisWrapper:
    """Liblouis Python binding'i için tip-güvenli wrapper.

    Tüm Liblouis çağrıları bu sınıf üzerinden yapılır.
    Hata yönetimi, tablo doğrulama ve mod yönetimi sağlar.

    Kullanım:
        wrapper = LiblouisWrapper()
        result = wrapper.translate("Merhaba dünya", "tr-g2.tbl")
        tables = wrapper.list_tables()
    """

    def __init__(self) -> None:
        """Wrapper'ı başlatır. Liblouis sürümünü log'lar."""
        self._version: str = louis.version()
        logger.info("Liblouis wrapper initialized, version=%s", self._version)

    # ── Temel özellikler ────────────────────────────────────────────────────

    @property
    def version(self) -> str:
        """Liblouis kütüphane sürümü."""
        return self._version

    @property
    def char_size(self) -> int:
        """Liblouis'te bir karakterin bayt cinsinden boyutu (genelde 4)."""
        return louis.charSize()  # type: ignore[no-any-return]

    # ── Tablo yönetimi ──────────────────────────────────────────────────────

    def list_tables(self) -> list[str]:
        """Mevcut tüm tabloları listeler.

        Returns:
            Tablo dosya adları listesi (örn. ['tr-g2.tbl', 'en-ueb-g1.ctb', ...]).
            Tam yol DEĞİL, yalnızca dosya adı.
        """
        if hasattr(louis, "listTables"):
            raw = louis.listTables()  # type: ignore[attr-defined]
        else:
            # Fallback for liblouis < 3.34
            import glob
            tables: list[str] = []
            for ext in (".ctb", ".utb", ".tbl"):
                tables.extend(glob.glob(os.path.join(
                    "/usr/share/liblouis/tables", f"*{ext}"
                )))
            raw = sorted(tables)
        return sorted({os.path.basename(p) for p in raw} | _KNOWN_TABLES_EXTRA)

    def list_tables_by_language(self, language: str) -> list[str]:
        """Belirli bir dilin tüm tablolarını listeler.

        Args:
            language: ISO 639-1 dil kodu (örn. 'tr', 'en').

        Returns:
            O dile ait tablo adları listesi.
        """
        prefix = language.lower()
        return [t for t in self.list_tables() if t.startswith(prefix)]

    def check_table(self, table_id: str) -> None:
        """Tablonun geçerli ve derlenebilir olduğunu doğrular.

        Args:
            table_id: Tablo kimliği (örn. 'tr-g2.tbl').

        Raises:
            TableNotFoundError: Tablo bulunamadıysa.
            TableCompileError: Tablo derlenemediyse.
        """
        self._validate_table_id(table_id)
        try:
            louis.checkTable([table_id])
        except RuntimeError as e:
            msg = str(e)
            if "not found" in msg.lower():
                raise TableNotFoundError(table_id) from e
            raise TableCompileError(table_id, msg) from e

    def get_table_info(self, table_id: str, key: str) -> str | None:
        """Tablo metadata'sını getirir.

        Args:
            table_id: Tablo kimliği.
            key: Metadata anahtarı. Yaygın değerler:
                - 'language': ISO 639-1 dil kodu
                - 'type': Tablo türü ('literary', 'computer', 'math', vb.)
                - 'dots': Nokta sayısı ('6' veya '8')
                - 'contraction': Kısaltma düzeyi ('full', 'none', 'partial')

        Returns:
            Metadata değeri veya bilinmiyorsa None.
        """
        self._validate_table_id(table_id)
        if hasattr(louis, "getTableInfo"):
            return louis.getTableInfo(table_id, key)  # type: ignore[no-any-return,attr-defined]
        # Fallback for liblouis < 3.34 — parse table file metadata
        from .table_manifest import _get_table_info
        return _get_table_info(table_id, key)

    def get_table_language(self, table_id: str) -> str | None:
        """Tablonun dil kodunu getirir."""
        return self.get_table_info(table_id, "language")

    def get_table_grade(self, table_id: str) -> BrailleGrade | None:
        """Tablodan kısaltma düzeyini tespit eder.

        Önce 'contraction' metadata'sına bakar,
        yoksa tablo adından çıkarım yapar.
        """
        contraction = self.get_table_info(table_id, "contraction")
        if contraction == "none":
            return BrailleGrade.GRADE_1
        if contraction == "full":
            return BrailleGrade.GRADE_2

        # Tablo adından çıkarım
        base = table_id.lower()
        if "comp8" in base or "comp6" in base or "-g0" in base:
            return BrailleGrade.GRADE_0
        if "-g2" in base:
            return BrailleGrade.GRADE_2
        if "-g1" in base:
            return BrailleGrade.GRADE_1
        return None

    def get_table_for_language(
        self,
        language: str,
        grade: BrailleGrade = BrailleGrade.GRADE_2,
    ) -> str | None:
        """Dil ve kısaltma düzeyine göre önerilen tabloyu getirir.

        Args:
            language: ISO 639-1 dil kodu.
            grade: İstenen kısaltma düzeyi.

        Returns:
            Tablo kimliği veya dil desteklenmiyorsa None.
        """
        lang_map = LANGUAGE_TABLE_MAP.get(language.lower())
        if lang_map is None:
            return None
        return lang_map.get(grade)

    # ── Çeviri ──────────────────────────────────────────────────────────────

    @overload
    def translate(
        self,
        text: str,
        table_id: str,
        *,
        mode: TranslationMode = TranslationMode.NONE,
        typeform: list[int] | None = None,
        detailed: Literal[False] = False,
    ) -> TranslationResult: ...

    @overload
    def translate(
        self,
        text: str,
        table_id: str,
        *,
        mode: TranslationMode = TranslationMode.NONE,
        typeform: list[int] | None = None,
        detailed: Literal[True],
    ) -> tuple[TranslationResult, dict[str, Any]]: ...

    def translate(
        self,
        text: str,
        table_id: str,
        *,
        mode: TranslationMode = TranslationMode.NONE,
        typeform: list[int] | None = None,
        detailed: bool = False,
    ) -> TranslationResult | tuple[TranslationResult, dict[str, Any]]:
        """Metni Braille'e çevirir.

        Args:
            text: Çevrilecek metin.
            table_id: Braille tablo kimliği (örn. 'tr-g2.tbl').
            mode: Çeviri modu bitmask'ı (TranslationMode enum veya int).
            typeform: Karakter vurgu dizisi (Typeform enum değerleri listesi).
            detailed: True ise detaylı sonuç (cursorPos, typeform vb.) döner.

        Returns:
            TranslationResult; detailed=True ise (TranslationResult, dict) tuple'ı.

        Raises:
            EmptyInputError: Girdi boşsa.
            TableNotFoundError: Tablo bulunamadıysa.
            TableCompileError: Tablo derlenemediyse.
            TranslationFailedError: Çeviri başarısız olduysa.
        """
        if not text.strip():
            raise EmptyInputError()

        self._validate_table_id(table_id)

        try:
            result_text = louis.translateString(
                [table_id],
                text,
                typeform=typeform,
                mode=int(mode),
            )
        except RuntimeError as e:
            raise TranslationFailedError(
                direction=TranslationDirection.TEXT_TO_BRAILLE.value,
                table_id=table_id,
                original_error=e,
            ) from e

        translation = TranslationResult(
            text=result_text,
            table_id=table_id,
            direction=TranslationDirection.TEXT_TO_BRAILLE,
            char_count=len(result_text),
        )

        if detailed:
            details: dict[str, Any] = {
                "input_char_count": len(text),
                "mode": int(mode),
                "mode_flags": self._describe_mode(int(mode)),
            }
            return translation, details

        return translation

    @overload
    def back_translate(
        self,
        braille: str,
        table_id: str,
        *,
        mode: TranslationMode = TranslationMode.NONE,
        detailed: Literal[False] = False,
    ) -> TranslationResult: ...

    @overload
    def back_translate(
        self,
        braille: str,
        table_id: str,
        *,
        mode: TranslationMode = TranslationMode.NONE,
        detailed: Literal[True],
    ) -> tuple[TranslationResult, dict[str, Any]]: ...

    def back_translate(
        self,
        braille: str,
        table_id: str,
        *,
        mode: TranslationMode = TranslationMode.NONE,
        detailed: bool = False,
    ) -> TranslationResult | tuple[TranslationResult, dict[str, Any]]:
        """Braille'i düz metne geri çevirir.

        Args:
            braille: Braille Unicode metni.
            table_id: Braille tablo kimliği.
            mode: Çeviri modu bitmask'ı.
            detailed: True ise detaylı sonuç döner.

        Returns:
            TranslationResult; detailed=True ise (TranslationResult, dict) tuple'ı.

        Raises:
            EmptyInputError: Girdi boşsa.
            TableNotFoundError: Tablo bulunamadıysa.
            TableCompileError: Tablo derlenemediyse.
            TranslationFailedError: Geri çeviri başarısız olduysa.
        """
        if not braille.strip():
            raise EmptyInputError()

        self._validate_table_id(table_id)

        try:
            result_text = louis.backTranslateString(
                [table_id],
                braille,
                typeform=None,
                mode=int(mode),
            )
        except RuntimeError as e:
            raise TranslationFailedError(
                direction=TranslationDirection.BRAILLE_TO_TEXT.value,
                table_id=table_id,
                original_error=e,
            ) from e

        translation = TranslationResult(
            text=result_text,
            table_id=table_id,
            direction=TranslationDirection.BRAILLE_TO_TEXT,
            char_count=len(result_text),
        )

        if detailed:
            details: dict[str, Any] = {
                "input_char_count": len(braille),
                "mode": int(mode),
                "mode_flags": self._describe_mode(int(mode)),
            }
            return translation, details

        return translation

    # ── Yardımcı fonksiyonlar ───────────────────────────────────────────────

    def hyphenate(
        self,
        text: str,
        table_id: str,
        mode: TranslationMode = TranslationMode.NONE,
    ) -> str:
        """Metni Liblouis heceleme kurallarına göre heceler.

        Args:
            text: Hecelenecek metin.
            table_id: Braille tablo kimliği.
            mode: Mod bitmask'ı.

        Returns:
            Yumuşak tire (soft hyphen, \\xad) ile hecelenmiş metin.
        """
        if not text.strip():
            raise EmptyInputError()

        self._validate_table_id(table_id)

        try:
            return louis.hyphenate([table_id], text, mode=int(mode))  # type: ignore[no-any-return]
        except RuntimeError as e:
            raise TranslationFailedError(
                direction="hyphenate",
                table_id=table_id,
                original_error=e,
            ) from e

    def char_to_dots(self, char: str) -> str:
        """Unicode Braille karakterini nokta desenine çevirir.

        Örneğin '⠡' (U+2821) → '1,6'.

        Unicode Braille bloğu (U+2800–U+28FF) kullanılarak doğrudan
        hesaplanır. Liblouis tablo bağımlılığı yoktur.

        Args:
            char: Tek bir Unicode Braille karakteri.

        Returns:
            Virgülle ayrılmış nokta numaraları (örn. '1,6').
            Karakter Braille bloğunda değilse boş string döner.

        Raises:
            ValueError: char birden fazla karakter ise.
        """
        if len(char) != 1:
            raise ValueError(f"Expected a single character, got {len(char)}")

        cp = ord(char)
        if not 0x2800 <= cp <= 0x28FF:
            return ""

        dots_val = cp - 0x2800
        if dots_val == 0:
            return "0"

        dot_numbers: list[str] = []
        for dot_num in range(1, 9):
            bit = 1 << (dot_num - 1)
            if dots_val & bit:
                dot_numbers.append(str(dot_num))

        return ",".join(dot_numbers)

    def dots_to_char(self, dots: str) -> str:
        """Nokta desenini Unicode Braille karakterine çevirir.

        Örneğin '1,6' → '⠡', '16' → '⠡'.

        Unicode Braille bloğu (U+2800–U+28FF) kullanılarak doğrudan
        hesaplanır. Liblouis tablo bağımlılığı yoktur.

        Args:
            dots: Nokta deseni. Virgülle veya bitişik yazılabilir
                  (örn. '1,6', '16', '1-6'). '0' = boş hücre.

        Returns:
            Unicode Braille karakteri (örn. '⠡').
            Geçersiz nokta numarası içeriyorsa boş string döner.
        """
        if not dots or not dots.strip():
            return ""

        # '0' → boş hücre (U+2800)
        if dots.strip() == "0":
            return "\u2800"

        # Virgül, tire, nokta veya boşluk karakterlerini temizle
        # Ayrıca bitişik sayılar için: "16" → [1, 6], "126" → [1, 2, 6]
        import re

        # Önce ayırıcılara göre böl
        split = re.split(r"[,;\-\s.]+", dots)

        # Bitişik yazılmış sayıları ayır: "16" → "1 6"
        expanded: list[str] = []
        for part in split:
            if not part:
                continue
            if part.isdigit() and len(part) > 1:
                # "16" → ["1", "6"]
                expanded.extend(part)
            else:
                expanded.append(part)

        parts = expanded

        if not parts:
            return ""

        dot_bits = 0
        for part in parts:
            try:
                dot_num = int(part)
            except ValueError:
                return ""

            if not 1 <= dot_num <= 8:
                return ""

            dot_bits |= 1 << (dot_num - 1)

        return chr(0x2800 + dot_bits)

    def set_log_level(self, level: str = "warn") -> None:
        """Liblouis log seviyesini ayarlar.

        Args:
            level: 'off', 'fatal', 'error', 'warn', 'info', 'debug', 'all'.
        """
        from .types import LOG_LEVELS

        numeric = LOG_LEVELS.get(level.lower())
        if numeric is not None:
            louis.setLogLevel(numeric)
            logger.debug("Liblouis log level set to %s (%d)", level, numeric)

    # ── İç yardımcılar ──────────────────────────────────────────────────────

    @staticmethod
    def _validate_table_id(table_id: str) -> None:
        """Tablo kimliğini allowlist modeline göre doğrular.

        Injection saldırılarına (path traversal, vb.) karşı koruma sağlar.
        """
        if not table_id or not table_id.strip():
            raise TableNotFoundError("(empty table id)")

        # Dosya adı deseni kontrolü
        if not _TABLE_NAME_RE.match(table_id):
            raise TableNotFoundError(
                f"Invalid table id format: {table_id!r}. "
                f"Expected pattern: ll-xxx.ext"
            )

    @staticmethod
    def _describe_mode(mode: int) -> list[str]:
        """Sayısal mod değerini insan-okunur bayrak listesine çevirir."""
        flags = []
        for flag in TranslationMode:
            if flag.value and (mode & flag.value):
                flags.append(flag.name)
        return flags  # type: ignore[return-value]


# ── Singleton ────────────────────────────────────────────────────────────────
# Servis katmanında doğrudan import edilebilir.

liblouis_wrapper = LiblouisWrapper()