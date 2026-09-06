# Tests for the table manifest and allowlist system (F2.1.2 + F2.1.3)
#
# Plan v9 referansı: Faz 2.1.2, 2.1.3

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from backend.src.translation import BrailleGrade
from backend.src.translation.table_manifest import (
    TableAllowlist,
    TableManifest,
    get_allowlist,
    get_manifest,
)


@pytest.fixture(scope="module")
def manifest() -> TableManifest:
    """Module-scoped: manifest bir kere yüklenir, tüm testler paylaşır."""
    return get_manifest()


@pytest.fixture(scope="module")
def allowlist() -> TableAllowlist:
    return get_allowlist()


class TestManifestBuild:
    """Manifest oluşturma ve temel özellikler."""

    def test_manifest_loads(self, manifest: TableManifest) -> None:
        assert manifest.count > 100  # 200+ derlenebilir tablo
        assert isinstance(manifest.count, int)

    def test_manifest_singleton(self) -> None:
        m1 = get_manifest()
        m2 = TableManifest.load()
        assert m1 is m2

    def test_all_entries_have_id(self, manifest: TableManifest) -> None:
        for entry in manifest.entries.values():
            assert entry.id
            assert isinstance(entry.id, str)

    def test_no_duplicate_ids(self, manifest: TableManifest) -> None:
        ids = list(manifest.entries.keys())
        assert len(ids) == len(set(ids))

    def test_languages_set(self, manifest: TableManifest) -> None:
        langs = manifest.languages
        assert "tr" in langs
        assert "en" in langs
        assert "de" in langs
        assert "fr" in langs
        assert len(langs) > 20  # en az 20 farklı dil

    def test_no_empty_ids(self, manifest: TableManifest) -> None:
        for entry in manifest.entries.values():
            assert entry.id.strip()


class TestManifestLookup:
    """get(), get_required(), filter() testleri."""

    def test_get_existing(self, manifest: TableManifest) -> None:
        entry = manifest.get("tr-g2.tbl")
        assert entry is not None
        assert entry.id == "tr-g2.tbl"
        assert entry.language == "tr"
        assert entry.grade == BrailleGrade.GRADE_2

    def test_get_nonexistent(self, manifest: TableManifest) -> None:
        assert manifest.get("nonexistent.tbl") is None

    def test_get_required_existing(self, manifest: TableManifest) -> None:
        entry = manifest.get_required("en-ueb-g1.ctb")
        assert entry.language == "en"

    def test_get_required_nonexistent_raises(self, manifest: TableManifest) -> None:
        with pytest.raises(KeyError):
            manifest.get_required("nonexistent.tbl")

    def test_filter_by_language(self, manifest: TableManifest) -> None:
        tr_tables = manifest.filter(language="tr")
        assert len(tr_tables) >= 2
        for e in tr_tables:
            assert e.language == "tr"

    def test_filter_by_grade(self, manifest: TableManifest) -> None:
        g2_tables = manifest.filter(grade=BrailleGrade.GRADE_2)
        assert len(g2_tables) > 0
        for e in g2_tables:
            assert e.grade == BrailleGrade.GRADE_2

    def test_filter_by_table_type(self, manifest: TableManifest) -> None:
        comp_tables = manifest.filter(table_type="computer")
        assert len(comp_tables) > 0
        for e in comp_tables:
            assert e.table_type == "computer"

    def test_filter_literary_only(self, manifest: TableManifest) -> None:
        lit_tables = manifest.filter(literary_only=True)
        assert len(lit_tables) > 0
        for e in lit_tables:
            assert e.is_literary or e.table_type == "literary"

    def test_filter_priority_languages_only(self, manifest: TableManifest) -> None:
        priority = manifest.filter(priority_languages_only=True)
        assert len(priority) > 0
        priority_langs = {"tr", "en", "de", "fr", "es", "ar", "ru", "pt"}
        for e in priority:
            assert e.language in priority_langs, f"{e.id} language={e.language}"

    def test_filter_back_translation(self, manifest: TableManifest) -> None:
        bt_tables = manifest.filter(back_translation=True)
        assert len(bt_tables) > 0
        for e in bt_tables:
            assert e.supports_back_translation

    def test_filter_combined(self, manifest: TableManifest) -> None:
        result = manifest.filter(
            language="tr",
            grade=BrailleGrade.GRADE_2,
            back_translation=True,
        )
        assert len(result) >= 1
        assert any(e.id == "tr-g2.tbl" for e in result)


class TestPriorityLanguages:
    """8 öncelikli dilin tam olarak kapsanması."""

    PRIORITY_LANGS = ["tr", "en", "de", "fr", "es", "ar", "ru", "pt"]

    def test_all_priority_languages_present(self, manifest: TableManifest) -> None:
        for lang in self.PRIORITY_LANGS:
            tables = manifest.filter(language=lang)
            assert len(tables) > 0, f"No tables for language: {lang}"

    def test_priority_languages_have_g1(self, manifest: TableManifest) -> None:
        """Her öncelikli dilde en az Grade 1 veya Grade 0 tablo olmalı."""
        for lang in self.PRIORITY_LANGS:
            g1 = manifest.filter(language=lang, grade=BrailleGrade.GRADE_1)
            g0 = manifest.filter(language=lang, grade=BrailleGrade.GRADE_0)
            assert len(g1) + len(g0) > 0, (
                f"No Grade 0/1 table for {lang}"
            )

    def test_priority_tables_have_human_names(self, manifest: TableManifest) -> None:
        """Öncelikli tablolarda insan-okunur isim olmalı."""
        named_count = 0
        for entry in manifest.filter(priority_languages_only=True):
            if entry.human_name:
                named_count += 1
        assert named_count >= 20  # 8 dil × en az 2-3 tablo = 20+

    def test_list_languages_priority_only(self, manifest: TableManifest) -> None:
        langs = manifest.list_languages(priority_only=True)
        assert len(langs) == 8
        lang_codes = {d["code"] for d in langs}
        assert lang_codes == set(self.PRIORITY_LANGS)

    def test_list_languages_all(self, manifest: TableManifest) -> None:
        langs = manifest.list_languages(priority_only=False)
        assert len(langs) > 8
        assert all("code" in d and "name" in d for d in langs)


class TestEntryProperties:
    """TableManifestEntry özellikleri."""

    def test_tr_g2_is_contracted(self, manifest: TableManifest) -> None:
        entry = manifest.get_required("tr-g2.tbl")
        assert entry.is_contracted
        assert not entry.is_computer_braille
        assert entry.is_literary

    def test_tr_tbl_is_computer(self, manifest: TableManifest) -> None:
        entry = manifest.get_required("tr.tbl")
        assert entry.is_computer_braille
        assert not entry.is_literary

    def test_en_ueb_g1_not_contracted(self, manifest: TableManifest) -> None:
        entry = manifest.get_required("en-ueb-g1.ctb")
        assert not entry.is_contracted
        assert entry.grade == BrailleGrade.GRADE_1

    def test_entry_is_frozen(self, manifest: TableManifest) -> None:
        entry = manifest.get_required("tr-g2.tbl")
        with pytest.raises(FrozenInstanceError):
            entry.id = "hacked.tbl"  # type: ignore[misc]


class TestToApiResponse:
    """API yanıt formatı testleri."""

    def test_basic_structure(self, manifest: TableManifest) -> None:
        data = manifest.to_api_response(priority_only=True)
        assert isinstance(data, list)
        assert len(data) > 0
        item = data[0]
        assert "id" in item
        assert "language" in item
        assert "grade" in item
        assert "type" in item

    def test_turkish_tables_have_names(self, manifest: TableManifest) -> None:
        data = manifest.to_api_response(language="tr")
        tr_items = [i for i in data if i["language"] == "tr"]
        assert len(tr_items) > 0
        assert any("name_tr" in i for i in tr_items)


class TestAllowlist:
    """TableAllowlist güvenlik testleri."""

    def test_validates_known_table(self, allowlist: TableAllowlist) -> None:
        # Hata atmaz
        allowlist.validate("tr-g2.tbl")

    def test_rejects_unknown_table(self, allowlist: TableAllowlist) -> None:
        with pytest.raises(ValueError):
            allowlist.validate("hacked.tbl")

    def test_rejects_empty(self, allowlist: TableAllowlist) -> None:
        with pytest.raises(ValueError):
            allowlist.validate("")

    def test_rejects_path_traversal(self, allowlist: TableAllowlist) -> None:
        with pytest.raises(ValueError):
            allowlist.validate("../../../etc/passwd")

    def test_is_allowed(self, allowlist: TableAllowlist) -> None:
        assert allowlist.is_allowed("tr-g2.tbl")
        assert not allowlist.is_allowed("hacked.tbl")

    def test_get_entry(self, allowlist: TableAllowlist) -> None:
        entry = allowlist.get_entry("tr-g2.tbl")
        assert entry.id == "tr-g2.tbl"
        assert entry.language == "tr"

    def test_get_entry_rejects_unknown(self, allowlist: TableAllowlist) -> None:
        with pytest.raises(ValueError):
            allowlist.get_entry("hacked.tbl")

    def test_validate_all_valid(self, allowlist: TableAllowlist) -> None:
        allowlist.validate_all(["tr-g2.tbl", "en-ueb-g1.ctb", "de-g1.ctb"])

    def test_validate_all_rejects_any_invalid(self, allowlist: TableAllowlist) -> None:
        with pytest.raises(ValueError, match="not in allowlist"):
            allowlist.validate_all(["tr-g2.tbl", "hacked.tbl"])

    def test_valid_ids_is_frozenset(self, allowlist: TableAllowlist) -> None:
        assert isinstance(allowlist.valid_ids, frozenset)
        assert "tr-g2.tbl" in allowlist.valid_ids

    def test_allowlist_singleton(self) -> None:
        a1 = get_allowlist()
        a2 = get_allowlist()
        assert a1 is a2


class TestAllowlistCoversAllManifestTables:
    """Allowlist ile manifest uyumluluğu."""

    def test_manifest_tables_in_allowlist(
        self, manifest: TableManifest, allowlist: TableAllowlist
    ) -> None:
        for table_id in manifest.entries:
            assert allowlist.is_allowed(table_id), (
                f"Table {table_id!r} in manifest but not in allowlist"
            )

    def test_allowlist_size_matches(self, manifest: TableManifest) -> None:
        allowlist = get_allowlist()
        # Çalışma anında yeni singleton — birebir eşleşmeli
        assert len(allowlist.valid_ids) == manifest.count


class TestCompileErrorsExcluded:
    """Derleme hatası veren tablolar manifest'e dahil edilmez."""

    def test_akk_borger_excluded(self, manifest: TableManifest) -> None:
        # akk-borger.utb 32-bit Unicode gerektirir, derlenemez
        assert manifest.get("akk-borger.utb") is None

    def test_cuneiform_excluded(self, manifest: TableManifest) -> None:
        assert manifest.get("cuneiform-transliterated.utb") is None
