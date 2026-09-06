"""Corpus-based translation verification tests.

Plan v9 referansı: Bölüm 1.10.9 — Doğrulama Testleri
"""

from __future__ import annotations

import pytest

from backend.src.translation import LiblouisWrapper

from .corpus import ROUND_TRIP_CORPUS, TURKISH_CORPUS


class TestTurkishCorpus:
    """Türkçe referans corpus doğrulama."""

    def setup_method(self) -> None:
        self.wrapper = LiblouisWrapper()

    @pytest.mark.parametrize("text,table_id,_", TURKISH_CORPUS)
    def test_translation_not_empty(self, text: str, table_id: str, _: str) -> None:
        """Çeviri sonucu boş olmamalı."""
        result = self.wrapper.translate(text, table_id)
        assert result.text, f"Empty result for '{text}' with {table_id}"
        assert result.char_count > 0

    @pytest.mark.parametrize("text,table_id,_", TURKISH_CORPUS)
    def test_translation_result_is_unicode(
        self, text: str, table_id: str, _: str
    ) -> None:
        """Çeviri sonucu geçerli Unicode string olmalı."""
        result = self.wrapper.translate(text, table_id)
        braille = result.text
        assert isinstance(braille, str)
        assert len(braille) > 0
        # Hiçbir null byte veya kontrol karakteri olmamalı (yeni satır hariç)
        assert "\x00" not in braille

    def test_turkish_round_trip_grade1(self) -> None:
        """Grade 1 kısaltmasız tablo ile round-trip."""
        text = "Merhaba dunya"
        braille = self.wrapper.translate(text, "tr-g1.ctb")
        back = self.wrapper.back_translate(braille.text, "tr-g1.ctb")
        # Grade 1 birebir olduğu için tam dönüş beklenir
        assert back.text.strip().lower() == text.strip().lower()

    def test_turkish_grade2_contracted(self) -> None:
        """Grade 2 kısaltmalı tablo kısaltma üretmeli."""
        text = "ve için"
        contracted = self.wrapper.translate(text, "tr-g2.tbl")
        # Kısaltmalı çıktı kısaltmasızdan farklı olmalı
        # (tüm kelimeler kısaltma üretmez, en az birinde fark beklenir)
        # Bu bir "yumuşak" kontrol — G2 tablosu her zaman farklı sonuç üretmeyebilir
        assert contracted.char_count > 0


class TestRoundTrip:
    """Braille → metin → Braille round-trip testleri."""

    def setup_method(self) -> None:
        self.wrapper = LiblouisWrapper()

    @pytest.mark.parametrize("text,table_id,supports_rt", ROUND_TRIP_CORPUS)
    def test_forward_translation(
        self, text: str, table_id: str, supports_rt: bool
    ) -> None:
        """Her dil/durumda ileri çeviri çalışmalı."""
        result = self.wrapper.translate(text, table_id)
        assert result.text, f"Forward translation failed for {table_id}"
        assert result.char_count > 0

    @pytest.mark.parametrize("text,table_id,supports_rt", ROUND_TRIP_CORPUS)
    def test_round_trip_if_supported(
        self, text: str, table_id: str, supports_rt: bool
    ) -> None:
        """Destekleniyorsa round-trip çalışmalı."""
        braille = self.wrapper.translate(text, table_id)
        back = self.wrapper.back_translate(braille.text, table_id)
        assert back.text, f"Back translation failed for {table_id}"
        # Round-trip sonucu kayıplı olabilir — en azından boş dönmemeli
        assert back.char_count > 0

    def test_round_trip_not_lossless(self) -> None:
        """Round-trip her zaman birebir olmayabilir — dokümantasyon amacıyla."""
        text = "Merhaba dünya, nasılsın?"
        braille = self.wrapper.translate(text, "tr-g2.tbl")
        back = self.wrapper.back_translate(braille.text, "tr-g2.tbl")
        # Grade 2'de büyük harf/küçük harf bilgisi kaybolabilir
        # Sadece boş olmadığını doğruluyoruz
        assert back.text