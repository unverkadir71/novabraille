# Tests for TranslationService (F2.2.1 + F2.2.2 + F2.2.3)
#
# Tests the service layer: input validation, table validation,
# translate, back-translate, char limits.
# Plan v9 referansı: Faz 2.2 — Çeviri Motoru

from __future__ import annotations

import pytest

from backend.src.services.translation import CharLimit, translation_service


class TestCharLimit:
    """Karakter sınır kontrolü testleri."""

    def test_valid_text_passes(self) -> None:
        lim = CharLimit(max_per_request=100)
        lim.check("Hello")  # hata atmaz

    def test_exact_limit_passes(self) -> None:
        lim = CharLimit(max_per_request=5)
        lim.check("Hello")  # tam 5 karakter

    def test_exceeds_limit_raises(self) -> None:
        lim = CharLimit(max_per_request=5)
        with pytest.raises(ValueError, match="Text too long"):
            lim.check("Hello, world!")

    def test_empty_text_raises(self) -> None:
        lim = CharLimit(max_per_request=100)
        with pytest.raises(ValueError, match="Text is empty"):
            lim.check("")

    def test_whitespace_only_counts(self) -> None:
        """Boşluk karakterleri de karakter sayılır."""
        lim = CharLimit(max_per_request=10)
        # 6 boşluk — limit altında, hata atmaz
        lim.check("      ")

    def test_default_limit_is_large(self) -> None:
        lim = CharLimit()
        assert lim.max_per_request == 500_000


class TestTranslateService:
    """Çeviri servisi testleri."""

    @pytest.mark.asyncio
    async def test_translate_turkish_g2(self) -> None:
        result = await translation_service.translate("Merhaba dünya", "tr-g2.tbl")
        assert result.direction == "text_to_braille"
        assert len(result.text) > 0
        assert result.table_id == "tr-g2.tbl"

    @pytest.mark.asyncio
    async def test_translate_turkish_g1_grade_override(self) -> None:
        """grade=grade1 → noContractions modu."""
        result = await translation_service.translate(
            "Merhaba dünya", "tr-g2.tbl", grade="grade1"
        )
        assert result.direction == "text_to_braille"
        assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_translate_english(self) -> None:
        result = await translation_service.translate("Hello world", "en-ueb-g1.ctb")
        assert result.direction == "text_to_braille"
        assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_translate_german(self) -> None:
        result = await translation_service.translate("Hallo Welt", "de-g1.ctb")
        assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_translate_arabic(self) -> None:
        result = await translation_service.translate("مرحبا", "ar-ar-g2.ctb")
        assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_translate_round_trip(self) -> None:
        """Metin → Braille → metin round-trip."""
        original = "Merhaba dünya"
        braille = await translation_service.translate(original, "tr-g2.tbl")
        back = await translation_service.back_translate(braille.text, "tr-g2.tbl")
        assert back.text.lower() == original.lower()

    @pytest.mark.asyncio
    async def test_invalid_table_raises(self) -> None:
        with pytest.raises(ValueError, match="not in the allowed tables list"):
            await translation_service.translate("test", "hacked.tbl")

    @pytest.mark.asyncio
    async def test_empty_text_raises(self) -> None:
        with pytest.raises(ValueError, match="Text is empty"):
            await translation_service.translate("", "tr-g2.tbl")

    @pytest.mark.asyncio
    async def test_whitespace_only_raises_empty(self) -> None:
        """Yalnızca boşluk → EmptyInputError (anlamlı içerik yok)."""
        from backend.src.translation.exceptions import EmptyInputError

        with pytest.raises(EmptyInputError):
            await translation_service.translate("   ", "tr-g2.tbl")

    @pytest.mark.asyncio
    async def test_all_8_languages_translate(self) -> None:
        """8 öncelikli dilin tamamı çeviri yapabilmeli."""
        test_cases = [
            ("Merhaba", "tr-g2.tbl"),
            ("Hello", "en-ueb-g1.ctb"),
            ("Hallo", "de-g1.ctb"),
            ("Bonjour", "fr-bfu-g2.ctb"),
            ("Hola", "es-g2.ctb"),
            ("مرحبا", "ar-ar-g2.ctb"),
            ("Привет", "ru-ru-g1.ctb"),
            ("Olá", "pt-pt-g1.utb"),
        ]
        for text, table in test_cases:
            result = await translation_service.translate(text, table)
            assert len(result.text) > 0, f"Failed: {text} → {table}"


class TestBackTranslateService:
    """Geri çeviri servisi testleri."""

    @pytest.mark.asyncio
    async def test_back_translate_turkish(self) -> None:
        braille = await translation_service.translate("Merhaba", "tr-g2.tbl")
        result = await translation_service.back_translate(braille.text, "tr-g2.tbl")
        assert result.direction == "braille_to_text"
        assert result.text.lower() == "merhaba"

    @pytest.mark.asyncio
    async def test_back_translate_english(self) -> None:
        braille = await translation_service.translate("Hello", "en-ueb-g1.ctb")
        result = await translation_service.back_translate(braille.text, "en-ueb-g1.ctb")
        assert result.text.lower() == "hello"

    @pytest.mark.asyncio
    async def test_back_translate_invalid_table_raises(self) -> None:
        with pytest.raises(ValueError, match="not in the allowed tables list"):
            await translation_service.back_translate("⠓", "hacked.tbl")

    @pytest.mark.asyncio
    async def test_back_translate_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="Text is empty"):
            await translation_service.back_translate("", "tr-g2.tbl")


class TestHelperMethods:
    """Yardımcı metot testleri."""

    def test_get_tables_for_language(self) -> None:
        tables = translation_service.get_tables_for_language("tr")
        assert "tr-g2.tbl" in tables
        assert "tr-g1.ctb" in tables

    def test_get_back_translation_tables(self) -> None:
        tables = translation_service.get_back_translation_tables("tr")
        assert "tr-g2.tbl" in tables
        assert all(
            translation_service.get_tables_for_language("tr")
        )

    def test_validate_table_valid(self) -> None:
        translation_service.validate_table("tr-g2.tbl")  # hata atmaz

    def test_validate_table_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            translation_service.validate_table("hacked.tbl")