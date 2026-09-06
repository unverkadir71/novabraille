"""Tests for contraction configuration system.

Plan v9: Bölüm 1.10.5 — Kısaltma Sistemi (ADR-008)
"""

from __future__ import annotations

from backend.src.translation.contraction_config import (
    CONTRACTION_PROFILES,
    ContractionLevel,
    get_all_contraction_profiles,
    get_contraction_profile,
)


class TestContractionProfiles:
    """Tüm dil profillerinin yapısal doğrulaması."""

    def test_all_eight_languages_present(self) -> None:
        profiles = get_all_contraction_profiles()
        assert set(profiles.keys()) == {"tr", "en", "de", "fr", "es", "ar", "ru", "pt"}

    def test_every_profile_has_levels(self) -> None:
        for code, profile in CONTRACTION_PROFILES.items():
            assert len(profile.levels) >= 2, f"{code}: en az 2 düzey olmalı"
            # Her profilin computer ve default level'ı olmalı
            level_ids = {lvl.id for lvl in profile.levels}
            assert "computer" in level_ids, f"{code}: computer level eksik"
            assert profile.default_level_id in level_ids, f"{code}: default_level_id geçersiz"

    def test_get_contraction_profile_valid(self) -> None:
        for code in ["tr", "en", "de", "fr", "es", "ar", "ru", "pt"]:
            profile = get_contraction_profile(code)
            assert profile is not None
            assert profile.language_code == code

    def test_get_contraction_profile_invalid(self) -> None:
        assert get_contraction_profile("xx") is None
        assert get_contraction_profile("") is None


class TestTurkishContractions:
    """Türkçe 7 seviyeli kısaltma sistemi."""

    def test_turkish_has_seven_levels(self) -> None:
        profile = get_contraction_profile("tr")
        assert profile is not None
        assert len(profile.levels) == 7
        level_ids = {lvl.id for lvl in profile.levels}
        expected = {"computer", "full_write", "single_letter", "two_letter", "syllable", "contracted", "contracted_full"}
        assert level_ids == expected

    def test_turkish_default_is_contracted_full(self) -> None:
        profile = get_contraction_profile("tr")
        assert profile is not None
        assert profile.default_level_id == "contracted_full"

    def test_turkish_supports_contraction(self) -> None:
        profile = get_contraction_profile("tr")
        assert profile is not None
        assert profile.supports_contraction is True

    def test_turkish_level_labels(self) -> None:
        profile = get_contraction_profile("tr")
        assert profile is not None
        for level in profile.levels:
            assert level.label_tr, f"{level.id} TR etiketi boş"
            assert level.label_en, f"{level.id} EN etiketi boş"
            assert level.description_tr, f"{level.id} TR açıklama boş"
            assert level.description_en, f"{level.id} EN açıklama boş"


class TestEnglishContractions:
    def test_english_three_levels(self) -> None:
        profile = get_contraction_profile("en")
        assert profile is not None
        level_ids = {lvl.id for lvl in profile.levels}
        assert level_ids == {"computer", "full_write", "contracted"}


class TestSpanishNoContraction:
    def test_spanish_no_contraction_system(self) -> None:
        profile = get_contraction_profile("es")
        assert profile is not None
        assert profile.supports_contraction is False
        assert profile.info_message_tr is not None

    def test_spanish_only_two_levels(self) -> None:
        profile = get_contraction_profile("es")
        assert profile is not None
        level_ids = {lvl.id for lvl in profile.levels}
        assert level_ids == {"computer", "full_write"}


class TestGermanThreeTiers:
    def test_german_four_levels(self) -> None:
        profile = get_contraction_profile("de")
        assert profile is not None
        level_ids = {lvl.id for lvl in profile.levels}
        assert "basisschrift" in level_ids
        assert "vollschrift" in level_ids
        assert "kurzschrift" in level_ids

    def test_german_default_vollschrift(self) -> None:
        profile = get_contraction_profile("de")
        assert profile is not None
        assert profile.default_level_id == "vollschrift"


class TestContractionLevel:
    def test_contraction_level_immutable(self) -> None:
        level = ContractionLevel(
            id="test", label_tr="T", label_en="T",
            description_tr="D", description_en="D",
        )
        assert level.id == "test"
        # frozen dataclass — hashable
        _ = hash(level)