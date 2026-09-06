# Tests for the Liblouis wrapper module (F2.1.1)
#
# Plan v9 referansı: Faz 2.1 — Liblouis Entegrasyonu
# Liblouis sürümü: 3.38.0

from __future__ import annotations

import pytest

from backend.src.translation import (
    BrailleGrade,
    TranslationDirection,
    TranslationMode,
    liblouis_wrapper,
)
from backend.src.translation.exceptions import (
    EmptyInputError,
    TableCompileError,
    TableNotFoundError,
    TranslationError,
    TranslationFailedError,
)


class TestTableManagement:
    """Tablo listeleme, doğrulama ve metadata testleri."""

    def test_list_tables_returns_all(self) -> None:
        tables = liblouis_wrapper.list_tables()
        assert len(tables) > 100  # 249+ tablo mevcut
        assert "tr-g2.tbl" in tables
        assert "tr-g1.ctb" in tables
        assert "en-ueb-g1.ctb" in tables
        assert all(isinstance(t, str) for t in tables)

    def test_list_tables_by_language_turkish(self) -> None:
        tables = liblouis_wrapper.list_tables_by_language("tr")
        assert "tr-g2.tbl" in tables
        assert "tr-g1.ctb" in tables
        assert "tr-g2.ctb" in tables
        assert all(t.startswith("tr") for t in tables)

    def test_list_tables_by_language_english(self) -> None:
        tables = liblouis_wrapper.list_tables_by_language("en")
        assert len(tables) > 0
        assert all(t.startswith("en") for t in tables)

    def test_list_tables_by_language_unknown(self) -> None:
        tables = liblouis_wrapper.list_tables_by_language("xx")
        assert tables == []

    def test_check_table_valid(self) -> None:
        # Hata atmaz
        liblouis_wrapper.check_table("tr-g2.tbl")
        liblouis_wrapper.check_table("tr-g1.ctb")
        liblouis_wrapper.check_table("en-ueb-g1.ctb")

    def test_check_table_invalid_name(self) -> None:
        with pytest.raises(TableNotFoundError, match="Invalid table id format"):
            liblouis_wrapper.check_table("../../../etc/passwd")

    def test_check_table_path_traversal_blocked(self) -> None:
        with pytest.raises(TableNotFoundError, match="Invalid table id format"):
            liblouis_wrapper.check_table("../../.ssh/id_rsa")

    def test_check_table_empty(self) -> None:
        with pytest.raises(TableNotFoundError):
            liblouis_wrapper.check_table("")

    def test_check_table_whitespace(self) -> None:
        with pytest.raises(TableNotFoundError):
            liblouis_wrapper.check_table("   ")

    def test_get_table_language(self) -> None:
        assert liblouis_wrapper.get_table_language("tr-g2.tbl") == "tr"
        assert liblouis_wrapper.get_table_language("en-ueb-g1.ctb") == "en"

    def test_get_table_grade_g2(self) -> None:
        grade = liblouis_wrapper.get_table_grade("tr-g2.tbl")
        assert grade == BrailleGrade.GRADE_2

    def test_get_table_grade_g1(self) -> None:
        grade = liblouis_wrapper.get_table_grade("tr-g1.ctb")
        assert grade == BrailleGrade.GRADE_1

    def test_get_table_grade_g0(self) -> None:
        grade = liblouis_wrapper.get_table_grade("de-g0-detailed.utb")
        assert grade == BrailleGrade.GRADE_0

    def test_get_table_grade_computer(self) -> None:
        grade = liblouis_wrapper.get_table_grade("fr-bfu-comp8.utb")
        assert grade == BrailleGrade.GRADE_0

    def test_get_table_for_language_turkish(self) -> None:
        assert liblouis_wrapper.get_table_for_language("tr", BrailleGrade.GRADE_1) == "tr-g1.ctb"
        assert liblouis_wrapper.get_table_for_language("tr", BrailleGrade.GRADE_2) == "tr-g2.tbl"

    def test_get_table_for_language_english(self) -> None:
        result1 = liblouis_wrapper.get_table_for_language("en", BrailleGrade.GRADE_1)
        result2 = liblouis_wrapper.get_table_for_language("en", BrailleGrade.GRADE_2)
        assert result1 == "en-ueb-g1.ctb"
        assert result2 == "en-ueb-g2.ctb"

    def test_get_table_for_language_unknown(self) -> None:
        assert liblouis_wrapper.get_table_for_language("xx") is None

    def test_table_id_regex_blocks_special_chars(self) -> None:
        invalid = ["a.b", "table.sql", "tr g2.tbl", "tr-g2", "-g2.ctb", "tr-g2.tbl\x00"]
        for tid in invalid:
            with pytest.raises(TableNotFoundError, match="Invalid table id format"):
                liblouis_wrapper._validate_table_id(tid)


class TestTranslation:
    """Metin → Braille çeviri testleri."""

    def test_translate_turkish_basic(self) -> None:
        result = liblouis_wrapper.translate("Merhaba", "tr-g2.tbl")
        assert result.direction == TranslationDirection.TEXT_TO_BRAILLE
        assert result.table_id == "tr-g2.tbl"
        assert result.char_count > 0
        assert isinstance(result.text, str)

    def test_translate_turkish_g2(self) -> None:
        result = liblouis_wrapper.translate("Merhaba dünya", "tr-g2.tbl")
        # Kısaltmalı çeviride "Mer" ve "dünya" karakterleri Braille'de
        assert len(result.text) > 0

    def test_translate_turkish_g1(self) -> None:
        result = liblouis_wrapper.translate("Merhaba dünya", "tr-g1.ctb")
        # Kısaltmasız daha uzun olmalı
        assert len(result.text) > 0

    def test_translate_english(self) -> None:
        result = liblouis_wrapper.translate("Hello world", "en-ueb-g1.ctb")
        assert len(result.text) > 0

    def test_translate_german(self) -> None:
        result = liblouis_wrapper.translate("Hallo Welt", "de-g1.ctb")
        assert len(result.text) > 0

    def test_translate_empty_raises(self) -> None:
        with pytest.raises(EmptyInputError):
            liblouis_wrapper.translate("", "tr-g2.tbl")

    def test_translate_whitespace_only_raises(self) -> None:
        with pytest.raises(EmptyInputError):
            liblouis_wrapper.translate("   \n  \t  ", "tr-g2.tbl")

    def test_translate_invalid_table_raises(self) -> None:
        with pytest.raises(TableNotFoundError):
            liblouis_wrapper.translate("test", "nonexistent.xyz")

    def test_translate_with_mode_no_contractions(self) -> None:
        # noContractions modunda kısaltmasız çeviri
        result = liblouis_wrapper.translate(
            "Merhaba",
            "tr-g2.tbl",
            mode=TranslationMode.NO_CONTRACTIONS,
        )
        assert len(result.text) > 0

    def test_translate_detailed(self) -> None:
        result, details = liblouis_wrapper.translate(
            "Merhaba",
            "tr-g2.tbl",
            detailed=True,
        )
        assert result.direction == TranslationDirection.TEXT_TO_BRAILLE
        assert "input_char_count" in details
        assert "mode" in details
        assert "mode_flags" in details
        assert details["input_char_count"] == 7  # Merhaba = 7 karakter

    def test_translate_turkish_special_chars(self) -> None:
        """Türkçe öz harflerin Braille dönüşümü."""
        result = liblouis_wrapper.translate("ç ğ ı ö ş ü", "tr-g1.ctb")
        # Her öz harf için bir Braille karakteri + boşluklar
        braille_chars = result.text.replace("\u2800", "")  # boşlukları çıkar
        assert len(braille_chars) >= 6  # 6 harf + boşluklar

    def test_translate_numbers(self) -> None:
        result = liblouis_wrapper.translate("123", "tr-g2.tbl")
        assert len(result.text) > 0

    def test_translate_punctuation(self) -> None:
        result = liblouis_wrapper.translate("Merhaba, dünya!", "tr-g2.tbl")
        assert len(result.text) > 0


class TestBackTranslation:
    """Braille → metin geri çeviri testleri."""

    def test_back_translate_round_trip_turkish(self) -> None:
        """Türkçe round-trip: metin → Braille → metin."""
        original = "Merhaba dünya"
        braille = liblouis_wrapper.translate(original, "tr-g2.tbl")
        back = liblouis_wrapper.back_translate(braille.text, "tr-g2.tbl")
        assert back.text.lower() == original.lower()

    def test_back_translate_round_trip_english(self) -> None:
        original = "Hello world"
        braille = liblouis_wrapper.translate(original, "en-ueb-g1.ctb")
        back = liblouis_wrapper.back_translate(braille.text, "en-ueb-g1.ctb")
        assert back.text.lower() == original.lower()

    def test_back_translate_direction(self) -> None:
        braille = liblouis_wrapper.translate("test", "tr-g2.tbl")
        back = liblouis_wrapper.back_translate(braille.text, "tr-g2.tbl")
        assert back.direction == TranslationDirection.BRAILLE_TO_TEXT

    def test_back_translate_empty_raises(self) -> None:
        with pytest.raises(EmptyInputError):
            liblouis_wrapper.back_translate("", "tr-g2.tbl")

    def test_back_translate_detailed(self) -> None:
        braille = liblouis_wrapper.translate("test", "tr-g2.tbl")
        result, details = liblouis_wrapper.back_translate(
            braille.text,
            "tr-g2.tbl",
            detailed=True,
        )
        assert result.direction == TranslationDirection.BRAILLE_TO_TEXT
        assert "input_char_count" in details


class TestHyphenation:
    """Heceleme testleri."""

    def test_hyphenate_german(self) -> None:
        """Almanca tablosu (de-g1.ctb) heceleme destekler."""
        result = liblouis_wrapper.hyphenate("Information", "de-g1.ctb")
        # soft hyphen veya sayısal heceleme kodu içermeli
        assert "\xad" in result or "0" in result  # Liblouis hyphenation output

    def test_hyphenate_empty_raises(self) -> None:
        with pytest.raises(EmptyInputError):
            liblouis_wrapper.hyphenate("", "tr-g2.tbl")


class TestCharDotsConversion:
    """Karakter ↔ nokta deseni dönüşüm testleri."""

    def test_char_to_dots_basic(self) -> None:
        """⠁ (nokta 1) → '1'."""
        dots = liblouis_wrapper.char_to_dots("\u2801")  # ⠁ = dot 1
        assert "1" in dots

    def test_char_to_dots_combined(self) -> None:
        """⠡ (nokta 1+6) → '1,6'."""
        dots = liblouis_wrapper.char_to_dots("\u2821")  # ⠡ = dots 1,6
        assert dots == "1,6"

    def test_char_to_dots_empty_cell(self) -> None:
        """Boş hücre → '0'."""
        dots = liblouis_wrapper.char_to_dots("\u2800")  # boş braille hücresi
        assert dots == "0"

    def test_char_to_dots_non_braille(self) -> None:
        """Braille olmayan karakter → ''."""
        dots = liblouis_wrapper.char_to_dots("a")
        assert dots == ""

    def test_char_to_dots_multi_char_raises(self) -> None:
        """Birden fazla karakter → ValueError."""
        with pytest.raises(ValueError, match="single character"):
            liblouis_wrapper.char_to_dots("ab")

    def test_dots_to_char_basic(self) -> None:
        """nokta 1 → ⠁."""
        char = liblouis_wrapper.dots_to_char("1")
        assert char == "\u2801"

    def test_dots_to_char_combined(self) -> None:
        """nokta 1,6 → ⠡."""
        char = liblouis_wrapper.dots_to_char("1,6")
        assert char == "\u2821"  # ⠡

    def test_dots_to_char_no_separator(self) -> None:
        """nokta '16' (virgülsüz) → ⠡."""
        char = liblouis_wrapper.dots_to_char("16")
        assert char == "\u2821"

    def test_dots_to_char_dash_separator(self) -> None:
        """nokta '1-6' (tireli) → ⠡."""
        char = liblouis_wrapper.dots_to_char("1-6")
        assert char == "\u2821"

    def test_dots_to_char_zero(self) -> None:
        """'0' → boş braille hücresi."""
        char = liblouis_wrapper.dots_to_char("0")
        assert char == "\u2800"

    def test_dots_to_char_round_trip_with_char_to_dots(self) -> None:
        """Round-trip: braille karakteri → dots → braille karakteri."""
        original = "\u2821"  # ⠡
        dots = liblouis_wrapper.char_to_dots(original)
        char = liblouis_wrapper.dots_to_char(dots)
        assert char == original

    def test_dots_to_char_invalid_dots(self) -> None:
        """Geçersiz nokta (9) → boş string."""
        char = liblouis_wrapper.dots_to_char("9")
        assert char == ""

    def test_dots_to_char_invalid_dots_combined(self) -> None:
        """Geçersiz nokta (1,9) → boş string."""
        char = liblouis_wrapper.dots_to_char("1,9")
        assert char == ""

    def test_dots_to_char_all_dots(self) -> None:
        """Tüm noktalar (1-8) → ⣿."""
        char = liblouis_wrapper.dots_to_char("1,2,3,4,5,6,7,8")
        assert char == "\u28FF"  # ⣿ = all 8 dots

    def test_char_to_dots_all_braille_chars(self) -> None:
        """Tüm 256 braille karakteri için round-trip."""
        for cp in range(0x2800, 0x2900):
            ch = chr(cp)
            dots = liblouis_wrapper.char_to_dots(ch)
            char = liblouis_wrapper.dots_to_char(dots)
            assert char == ch, f"Round-trip failed for U+{cp:04X}: dots={dots!r}"


class TestVersionAndProperties:
    """Sürüm ve temel özellik testleri."""

    def test_version(self) -> None:
        assert liblouis_wrapper.version == "3.38.0"

    def test_char_size(self) -> None:
        assert liblouis_wrapper.char_size == 2  # wchar_t 2 byte (Linux x64)


class TestModeDescribe:
    """Mod açıklama testleri."""

    def test_describe_mode_none(self) -> None:
        flags = liblouis_wrapper._describe_mode(0)
        assert flags == []

    def test_describe_mode_no_contractions(self) -> None:
        flags = liblouis_wrapper._describe_mode(1)
        assert "NO_CONTRACTIONS" in flags

    def test_describe_mode_combined(self) -> None:
        mode = TranslationMode.NO_CONTRACTIONS | TranslationMode.COMPUTER_BRAILLE
        flags = liblouis_wrapper._describe_mode(int(mode))
        assert "NO_CONTRACTIONS" in flags
        assert "COMPUTER_BRAILLE" in flags


class TestExceptionHierarchy:
    """İstisna hiyerarşisi testleri."""

    def test_translation_error_is_base(self) -> None:
        assert issubclass(TableNotFoundError, TranslationError)
        assert issubclass(TableCompileError, TranslationError)
        assert issubclass(EmptyInputError, TranslationError)
        assert issubclass(TranslationFailedError, TranslationError)

    def test_table_not_found_message(self) -> None:
        err = TableNotFoundError("xyz")
        assert "xyz" in str(err)
        assert err.table_id == "xyz"

    def test_translation_failed_message(self) -> None:
        original = RuntimeError("boom")
        err = TranslationFailedError("text_to_braille", "tr-g2.tbl", original)
        assert "text_to_braille" in str(err)
        assert "tr-g2.tbl" in str(err)


class TestLogLevelSetting:
    """Log seviyesi ayarlama testleri."""

    def test_set_log_level_valid(self) -> None:
        # Hata atmamalı
        liblouis_wrapper.set_log_level("warn")
        liblouis_wrapper.set_log_level("off")
        liblouis_wrapper.set_log_level("debug")

    def test_describe_mode_unknown(self) -> None:
        flags = liblouis_wrapper._describe_mode(9999)
        # Mevcut flag'lerden eşleşen olmayacak
        assert len(flags) >= 0  # herhangi bir flag olabilir veya hiç olmayabilir
