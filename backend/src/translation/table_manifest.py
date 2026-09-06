# Table manifest and allowlist system
#
# Single source of truth for available Braille tables.
# Built at startup by scanning the Liblouis table directory.
# Plan v9 referansı: Faz 2.1.2 — Tablo manifest ve allowlist sistemi
#
# Compatibility: louis.listTables() available in liblouis >= 3.34.0.
# Falls back to filesystem scan for older versions (e.g., Debian 3.33.0).

from __future__ import annotations

import glob
import logging
import os
from dataclasses import dataclass
from typing import ClassVar

import louis  # type: ignore[import-untyped]

from .types import BrailleGrade

logger = logging.getLogger(__name__)


# ── Compatibility: louis.listTables() shim ────────────────────────────────

def _list_tables() -> list[str]:
    """List all available Liblouis table files.

    Uses the native louis.listTables() if available (liblouis >= 3.34.0).
    Falls back to scanning the filesystem table directory.
    """
    if hasattr(louis, "listTables"):
        return sorted(louis.listTables())  # type: ignore[attr-defined]

    # Filesystem fallback for liblouis < 3.34.0
    possible_dirs = [
        "/usr/share/liblouis/tables",
        "/usr/local/share/liblouis/tables",
    ]
    table_extensions = {".ctb", ".utb", ".tbl"}
    tables: list[str] = []

    for tables_dir in possible_dirs:
        if not os.path.isdir(tables_dir):
            continue
        for ext in table_extensions:
            tables.extend(glob.glob(os.path.join(tables_dir, f"*{ext}")))
        break  # Use first found directory

    return sorted(tables)


# ── İnsan-okunur isimlendirme (8 öncelikli dil) ─────────────────────────────

@dataclass(frozen=True, slots=True)
class TableName:
    """Bir tablonun Türkçe ve İngilizce adı."""

    tr: str
    en: str


# 8 öncelikli dil için el yapımı isimlendirme.
# Geri kalan diller Liblouis metadata'sından otomatik tespit edilir.
_PRIORITY_TABLE_NAMES: dict[str, TableName] = {
    # Türkçe
    "tr-g1.ctb": TableName(tr="Türkçe — Kısaltmasız", en="Turkish — Uncontracted"),
    "tr-g2.tbl": TableName(tr="Türkçe — Kısaltmalı", en="Turkish — Contracted"),
    "tr.tbl": TableName(tr="Türkçe — Bilgisayar Braille'i", en="Turkish — Computer Braille"),
    "tr-g2.ctb": TableName(tr="Türkçe — Kısaltmalı (6 nokta)", en="Turkish — Contracted (6-dot)"),
    "tr.ctb": TableName(tr="Türkçe — Temel", en="Turkish — Base"),
    # İngilizce
    "en-ueb-g1.ctb": TableName(
        tr="İngilizce (UEB) — Kısaltmasız", en="English (UEB) — Uncontracted"
    ),
    "en-ueb-g2.ctb": TableName(tr="İngilizce (UEB) — Kısaltmalı", en="English (UEB) — Contracted"),
    "en-us-g1.ctb": TableName(tr="İngilizce (ABD) — Kısaltmasız", en="English (US) — Uncontracted"),
    "en-us-g2.ctb": TableName(tr="İngilizce (ABD) — Kısaltmalı", en="English (US) — Contracted"),
    "en-gb-g1.utb": TableName(tr="İngilizce (BK) — Kısaltmasız", en="English (UK) — Uncontracted"),
    "en-GB-g2.ctb": TableName(tr="İngilizce (BK) — Kısaltmalı", en="English (UK) — Contracted"),
    # Almanca
    "de-g1.ctb": TableName(tr="Almanca — Basisschrift", en="German — Basisschrift"),
    "de-g1-detailed.ctb": TableName(
        tr="Almanca — Basisschrift (detaylı)", en="German — Basisschrift (detailed)"
    ),
    "de-g2.ctb": TableName(tr="Almanca — Kurzschrift", en="German — Kurzschrift (contracted)"),
    "de-g0.utb": TableName(tr="Almanca — Bilgisayar Braille'i", en="German — Computer Braille"),
    "de-de-comp8.ctb": TableName(tr="Almanca — 8-nokta", en="German — 8-dot Computer"),
    # Fransızca
    "fr-bfu-g2.ctb": TableName(tr="Fransızca — Kısaltmalı", en="French — Contracted"),
    "fr-bfu-comp6.utb": TableName(
        tr="Fransızca — 6-nokta Kısaltmasız", en="French — 6-dot Uncontracted"
    ),
    "fr-bfu-comp8.utb": TableName(tr="Fransızca — 8-nokta", en="French — 8-dot Computer"),
    # İspanyolca
    "es-g1.ctb": TableName(tr="İspanyolca — Kısaltmasız", en="Spanish — Uncontracted"),
    "es-g2.ctb": TableName(tr="İspanyolca — Kısaltmalı", en="Spanish — Contracted"),
    # Arapça
    "ar-ar-g1.utb": TableName(tr="Arapça — Kısaltmasız", en="Arabic — Uncontracted"),
    "ar-ar-g2.ctb": TableName(tr="Arapça — Kısaltmalı", en="Arabic — Contracted"),
    "ar-ar-comp8.utb": TableName(tr="Arapça — 8-nokta", en="Arabic — 8-dot Computer"),
    # Rusça
    "ru-ru-g1.ctb": TableName(tr="Rusça — Kısaltmasız", en="Russian — Uncontracted"),
    "ru-litbrl.ctb": TableName(tr="Rusça — Edebî", en="Russian — Literary"),
    "ru-comp8.utb": TableName(tr="Rusça — 8-nokta", en="Russian — 8-dot Computer"),
    # Portekizce
    "pt-pt-g1.utb": TableName(tr="Portekizce — Kısaltmasız", en="Portuguese — Uncontracted"),
    "pt-pt-g2.ctb": TableName(tr="Portekizce — Kısaltmalı", en="Portuguese — Contracted"),
    "pt-pt-comp8.ctb": TableName(tr="Portekizce — 8-nokta", en="Portuguese — 8-dot Computer"),
}

# 8 öncelikli dil: ISO 639-1 → Türkçe ad
_PRIORITY_LANGUAGE_NAMES: dict[str, str] = {
    "tr": "Türkçe",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "ar": "العربية",
    "ru": "Русский",
    "pt": "Português",
}


# ── TableManifestEntry ───────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TableManifestEntry:
    """Tek bir Braille tablosunun tam metadata'sı."""

    id: str
    """Tablo kimliği (dosya adı, örn. 'tr-g2.tbl')."""

    language: str | None
    """ISO 639-1 veya -2 dil kodu (örn. 'tr', 'en')."""

    grade: BrailleGrade | None
    """Braille kısaltma düzeyi."""

    table_type: str | None
    """Tablo türü: 'literary', 'computer', 'math', 'hyphenation', None."""

    dots: int | None
    """Nokta sayısı: 6 veya 8."""

    contraction: str | None
    """Kısaltma düzeyi: 'no', 'partial', 'full', None."""

    supports_back_translation: bool
    """Geri çeviri (Braille → metin) destekleniyor mu?"""

    human_name: TableName | None
    """İnsan-okunur isim (Türkçe + İngilizce)."""

    @property
    def is_computer_braille(self) -> bool:
        """Bilgisayar Braille'i tablosu mu?"""
        return self.table_type == "computer" or self.grade == BrailleGrade.GRADE_0

    @property
    def is_literary(self) -> bool:
        """Edebî (literary) Braille tablosu mu?"""
        return self.table_type == "literary"

    @property
    def is_contracted(self) -> bool:
        """Kısaltmalı tablo mu?"""
        return self.contraction in ("full", "partial") or self.grade == BrailleGrade.GRADE_2


# ── TableManifest ─────────────────────────────────────────────────────────────


class TableManifest:
    """Tüm mevcut Liblouis tablolarının kataloğu.

    İlk erişimde tembel yüklenir. Derlenemeyen tablolar otomatik elenir.
    Tüm tablo doğrulaması bu katalog üzerinden yapılır.

    Kullanım:
        manifest = TableManifest.load()
        entry = manifest.get("tr-g2.tbl")
        tables = manifest.filter(language="tr", grade=BrailleGrade.GRADE_2)
    """

    _instance: ClassVar[TableManifest | None] = None

    def __init__(self, entries: list[TableManifestEntry]) -> None:
        self._entries: dict[str, TableManifestEntry] = {e.id: e for e in entries}
        self._by_language: dict[str, list[TableManifestEntry]] = {}
        self._by_grade: dict[BrailleGrade, list[TableManifestEntry]] = {}

        for entry in entries:
            if entry.language:
                self._by_language.setdefault(entry.language, []).append(entry)
            if entry.grade is not None:
                self._by_grade.setdefault(entry.grade, []).append(entry)

    @classmethod
    def load(cls) -> TableManifest:
        """Tüm tabloları tarar, doğrular ve manifest'i oluşturur.

        Singleton — ilk çağrıda yüklenir, sonraki çağrılarda önbellekten döner.
        """
        if cls._instance is not None:
            return cls._instance

        logger.info("Building table manifest...")
        entries = cls._enumerate()
        cls._instance = cls(entries)
        logger.info(
            "Table manifest built: %d tables, %d languages",
            len(entries),
            len(cls._instance.languages),
        )
        return cls._instance

    @classmethod
    def _enumerate(cls) -> list[TableManifestEntry]:
        """Tüm Liblouis tablolarını tarar ve metadata ile zenginleştirir."""
        all_tables = sorted(_list_tables())
        entries: list[TableManifestEntry] = []
        seen_ids: set[str] = set()

        for full_path in all_tables:
            table_id = os.path.basename(full_path)
            if table_id in seen_ids:
                continue

            try:
                louis.checkTable([table_id])
            except RuntimeError as e:
                logger.debug("Skipping uncompilable table %s: %s", table_id, e)
                continue

            seen_ids.add(table_id)
            entry = cls._build_entry(table_id)
            entries.append(entry)

        return entries

    @staticmethod
    def _build_entry(table_id: str) -> TableManifestEntry:
        """Tek bir tablo için TableManifestEntry oluşturur."""
        # Liblouis metadata'sı
        language = louis.getTableInfo(table_id, "language")
        table_type = louis.getTableInfo(table_id, "type")
        dots_str = louis.getTableInfo(table_id, "dots")
        contraction = louis.getTableInfo(table_id, "contraction")

        dots: int | None = int(dots_str) if dots_str else None

        # Grade tespiti — metadata + dosya adı çıkarımı
        grade: BrailleGrade | None = None
        base = table_id.lower()
        if contraction == "no":
            grade = BrailleGrade.GRADE_1
        elif contraction in ("full", "partial"):
            grade = BrailleGrade.GRADE_2
        elif "comp8" in base or "comp6" in base or "-g0" in base:
            grade = BrailleGrade.GRADE_0
        elif "-g2" in base:
            grade = BrailleGrade.GRADE_2
        elif "-g1" in base:
            grade = BrailleGrade.GRADE_1

        # Back-translation desteği testi
        supports_back = _test_back_translation(table_id)

        # İnsan-okunur isim
        human_name = _PRIORITY_TABLE_NAMES.get(table_id)

        return TableManifestEntry(
            id=table_id,
            language=language,
            grade=grade,
            table_type=table_type,
            dots=dots,
            contraction=contraction,
            supports_back_translation=supports_back,
            human_name=human_name,
        )

    # ── Erişim ───────────────────────────────────────────────────────────

    @property
    def entries(self) -> dict[str, TableManifestEntry]:
        """Tüm tablolar: id → entry."""
        return dict(self._entries)

    @property
    def languages(self) -> set[str]:
        """Mevcut tüm dil kodları."""
        return set(self._by_language.keys())

    @property
    def count(self) -> int:
        """Toplam tablo sayısı."""
        return len(self._entries)

    def get(self, table_id: str) -> TableManifestEntry | None:
        """ID'ye göre tablo arar."""
        return self._entries.get(table_id)

    def get_required(self, table_id: str) -> TableManifestEntry:
        """ID'ye göre tablo arar; yoksa KeyError fırlatır."""
        entry = self._entries.get(table_id)
        if entry is None:
            raise KeyError(f"Table not in manifest: {table_id!r}")
        return entry

    def filter(
        self,
        *,
        language: str | None = None,
        grade: BrailleGrade | None = None,
        table_type: str | None = None,
        dots: int | None = None,
        back_translation: bool | None = None,
        literary_only: bool = False,
        priority_languages_only: bool = False,
    ) -> list[TableManifestEntry]:
        """Tabloları kriterlere göre filtreler.

        Args:
            language: ISO 639-1 dil kodu.
            grade: Braille kısaltma düzeyi.
            table_type: 'literary', 'computer', 'math', vb.
            dots: 6 veya 8 nokta.
            back_translation: True → yalnızca geri çeviri destekleyenler.
            literary_only: True → yalnızca edebî tablolar.
            priority_languages_only: True → yalnızca 8 öncelikli dil.
        """
        if language:
            candidates = self._by_language.get(language, [])
        else:
            candidates = list(self._entries.values())

        result: list[TableManifestEntry] = []
        for entry in candidates:
            if grade is not None and entry.grade != grade:
                continue
            if table_type is not None and entry.table_type != table_type:
                continue
            if dots is not None and entry.dots != dots:
                continue
            if back_translation and not entry.supports_back_translation:
                continue
            if literary_only and not entry.is_literary:
                continue
            if priority_languages_only and entry.language not in _PRIORITY_LANGUAGE_NAMES:
                continue
            result.append(entry)

        return sorted(result, key=lambda e: e.id)

    def list_languages(self, priority_only: bool = False) -> list[dict[str, str]]:
        """Mevcut dillerin listesini döner.

        Args:
            priority_only: True → yalnızca 8 öncelikli dil.

        Returns:
            Her dil için {'code': ..., 'name': ...} dict'leri listesi.
        """
        result: list[dict[str, str]] = []
        seen: set[str] = set()

        for entry in self._entries.values():
            if entry.language is None:
                continue
            if entry.language in seen:
                continue
            if priority_only and entry.language not in _PRIORITY_LANGUAGE_NAMES:
                continue

            seen.add(entry.language)
            name = _PRIORITY_LANGUAGE_NAMES.get(entry.language, entry.language.upper())
            result.append({"code": entry.language, "name": name})

        return sorted(result, key=lambda d: d["code"])

    def to_api_response(
        self,
        *,
        language: str | None = None,
        priority_only: bool = False,
    ) -> list[dict[str, object]]:
        """API yanıtı için serileştirilebilir format.

        Yalnızca kullanıcıya gösterilmesi gereken alanları içerir.
        """
        entries = self.filter(
            language=language, priority_languages_only=priority_only
        )
        result: list[dict[str, object]] = []
        for entry in entries:
            item: dict[str, object] = {
                "id": entry.id,
                "language": entry.language,
                "grade": entry.grade.value if entry.grade else None,
                "type": entry.table_type,
                "dots": entry.dots,
                "contraction": entry.contraction,
                "supports_back_translation": entry.supports_back_translation,
            }
            if entry.human_name:
                item["name_tr"] = entry.human_name.tr
                item["name_en"] = entry.human_name.en
            result.append(item)
        return result


# ── TableAllowlist ────────────────────────────────────────────────────────────


class TableAllowlist:
    """Güvenlik geçidi — yalnızca manifest'teki tablolara izin verir.

    Kullanıcıdan gelen table_id değerlerini doğrulamak için kullanılır.
    Manifest dışındaki hiçbir tablo kabul edilmez.

    Kullanım:
        allowlist = TableAllowlist(manifest)
        allowlist.validate("tr-g2.tbl")           # → None (geçerli)
        allowlist.validate("../../../etc/passwd")  # → ValueError
    """

    def __init__(self, manifest: TableManifest) -> None:
        self._manifest = manifest
        self._valid_ids: set[str] = set(manifest.entries.keys())

    @property
    def valid_ids(self) -> frozenset[str]:
        """Geçerli tüm tablo ID'leri (salt-okunur)."""
        return frozenset(self._valid_ids)

    def validate(self, table_id: str) -> None:
        """Tablo ID'sini doğrular. Geçersizse ValueError fırlatır.

        Args:
            table_id: Doğrulanacak tablo kimliği.

        Raises:
            ValueError: Tablo manifest'te yoksa.
        """
        if table_id not in self._valid_ids:
            raise ValueError(
                f"Table {table_id!r} is not in the allowed tables list"
            )

    def validate_all(self, table_ids: list[str]) -> None:
        """Birden fazla tablo ID'sini doğrular.

        Args:
            table_ids: Doğrulanacak tablo kimlikleri.

        Raises:
            ValueError: Herhangi bir tablo manifest'te yoksa.
        """
        invalid = [tid for tid in table_ids if tid not in self._valid_ids]
        if invalid:
            raise ValueError(
                f"Tables not in allowlist: {', '.join(repr(t) for t in invalid)}"
            )

    def is_allowed(self, table_id: str) -> bool:
        """Tablo ID'si manifest'te var mı?"""
        return table_id in self._valid_ids

    def get_entry(self, table_id: str) -> TableManifestEntry:
        """Tablo ID'sini doğrular ve manifest girişini döner.

        Args:
            table_id: Tablo kimliği.

        Returns:
            TableManifestEntry.

        Raises:
            ValueError: Tablo manifest'te yoksa.
        """
        self.validate(table_id)
        return self._manifest.get_required(table_id)


# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────


def _test_back_translation(table_id: str) -> bool:
    """Bir tablonun geri çeviriyi (Braille → metin) destekleyip desteklemediğini test eder.

    'test' kelimesini çevirip geri çevirerek deneysel doğrulama yapar.
    """
    try:
        brl = louis.translateString([table_id], "test")
        back = louis.backTranslateString([table_id], brl)
        return bool(back.strip())
    except Exception:
        return False


# ── Singleton ────────────────────────────────────────────────────────────────

_table_manifest: TableManifest | None = None
_table_allowlist: TableAllowlist | None = None


def get_manifest() -> TableManifest:
    """TableManifest singleton'ını döner (tembel yükleme)."""
    global _table_manifest
    if _table_manifest is None:
        _table_manifest = TableManifest.load()
    return _table_manifest


def get_allowlist() -> TableAllowlist:
    """TableAllowlist singleton'ını döner."""
    global _table_allowlist
    if _table_allowlist is None:
        _table_allowlist = TableAllowlist(get_manifest())
    return _table_allowlist
