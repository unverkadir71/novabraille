# Translation types, enums, and constants
#
# Type definitions for the translation engine.
# Plan v9 referansı: Faz 2.1 — Çeviri Çekirdeği

from __future__ import annotations

from enum import IntFlag, StrEnum

import louis  # type: ignore[import-untyped]


class TranslationDirection(StrEnum):
    """Çeviri yönü."""

    TEXT_TO_BRAILLE = "text_to_braille"
    BRAILLE_TO_TEXT = "braille_to_text"


class BrailleGrade(StrEnum):
    """Braille kısaltma düzeyi."""

    GRADE_0 = "grade0"  # Bilgisayar Braille'i (8 nokta, birebir)
    GRADE_1 = "grade1"  # Kısaltmasız
    GRADE_2 = "grade2"  # Kısaltmalı


class TranslationMode(IntFlag):
    """Liblouis çeviri modu bitmask'ları.

    Birden fazla mod OR (|) ile birleştirilebilir.
    """

    NONE = 0
    NO_CONTRACTIONS = louis.noContractions  # 1 — kısaltma kullanma (grade 1 zorla)
    COMPBRL_AT_CURSOR = louis.compbrlAtCursor  # 2 — imleçte bilgisayar Braille'i
    DOTS_IO = louis.dotsIO  # 4 — giriş/çıkış nokta deseni
    UC_BRL = louis.ucBrl  # 64 — Unicode Braille
    NO_UNDEFINED = louis.noUndefined  # 128 — tanımsız karakterler için hata
    PARTIAL_TRANS = louis.partialTrans  # 256 — kısmî çeviri
    COMPUTER_BRAILLE = louis.computer_braille  # 1024 — bilgisayar Braille'i (8 nokta)


class Typeform(IntFlag):
    """Liblouis typeform (karakter vurgusu) bitmask'ları."""

    PLAIN_TEXT = louis.plain_text  # 0 — düz metin
    ITALIC = louis.italic  # 1 — italik
    UNDERLINE = louis.underline  # 2 — altı çizili
    BOLD = louis.bold  # 4 — kalın


# Log seviyeleri
LOG_LEVELS: dict[str, int] = {
    "off": louis.LOG_OFF,
    "fatal": louis.LOG_FATAL,
    "error": louis.LOG_ERROR,
    "warn": louis.LOG_WARN,
    "info": louis.LOG_INFO,
    "debug": louis.LOG_DEBUG,
    "all": louis.LOG_ALL,
}

# Liblouis tarafından desteklenen Türkçe tablolar
TURKISH_TABLES: dict[BrailleGrade, str] = {
    BrailleGrade.GRADE_0: "tr.tbl",
    BrailleGrade.GRADE_1: "tr-g1.ctb",
    BrailleGrade.GRADE_2: "tr-g2.tbl",
}

# Varsayılan tablo
DEFAULT_TABLE = "tr-g2.tbl"

# Önerilen dil eşleştirmeleri (locale → tablo grubu)
# Disk üzerinde mevcut tablolarla doğrulanmıştır.
# G1 tablosu olmayan dillerde G2 tablosu noContractions modu ile kullanılır.
LANGUAGE_TABLE_MAP: dict[str, dict[BrailleGrade, str]] = {
    "tr": TURKISH_TABLES,
    "en": {
        BrailleGrade.GRADE_0: "en-ueb-g1.ctb",
        BrailleGrade.GRADE_1: "en-ueb-g1.ctb",
        BrailleGrade.GRADE_2: "en-ueb-g2.ctb",
    },
    "de": {
        BrailleGrade.GRADE_0: "de-g0-detailed.utb",
        BrailleGrade.GRADE_1: "de-g1.ctb",
        BrailleGrade.GRADE_2: "de-g2.ctb",
    },
    "fr": {
        BrailleGrade.GRADE_0: "fr-bfu-comp8.utb",
        BrailleGrade.GRADE_1: "fr-bfu-g2.ctb",  # G1 yok → G2 + noContractions
        BrailleGrade.GRADE_2: "fr-bfu-g2.ctb",
    },
    "es": {
        BrailleGrade.GRADE_0: "es-g1.ctb",
        BrailleGrade.GRADE_1: "es-g1.ctb",
        BrailleGrade.GRADE_2: "es-g2.ctb",
    },
    "ar": {
        BrailleGrade.GRADE_0: "ar-ar-g1.utb",
        BrailleGrade.GRADE_1: "ar-ar-g1.utb",
        BrailleGrade.GRADE_2: "ar-ar-g2.ctb",
    },
    "ru": {
        BrailleGrade.GRADE_0: "ru-ru-g1.ctb",
        BrailleGrade.GRADE_1: "ru-ru-g1.ctb",
        BrailleGrade.GRADE_2: "ru-ru-g1.ctb",  # G2 yok
    },
    "pt": {
        BrailleGrade.GRADE_0: "pt-pt-g1.utb",
        BrailleGrade.GRADE_1: "pt-pt-g1.utb",
        BrailleGrade.GRADE_2: "pt-pt-g2.ctb",
    },
}