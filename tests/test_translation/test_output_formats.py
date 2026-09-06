"""Tests for output format producers (BRF, BRL, Display).

Plan v9: Bölüm 1.10.6 — Çıktı Formatları (ADR-008)
Memory.md: BRF format kuralları
"""

from __future__ import annotations

from backend.src.translation.output_formats import (
    BRFProducer,
    BRLProducer,
    DisplayProducer,
    OutputFormat,
    OutputMode,
    PageLayout,
    get_producer,
)

# ── PageLayout tests ───────────────────────────────────────────────────


class TestPageLayout:
    def test_default_a4(self) -> None:
        layout = PageLayout()
        assert layout.chars_per_line == 30
        assert layout.lines_per_page == 28

    def test_custom_layout(self) -> None:
        layout = PageLayout(chars_per_line=40, lines_per_page=25)
        assert layout.chars_per_line == 40
        assert layout.lines_per_page == 25


# ── BRF Producer tests ─────────────────────────────────────────────────


class TestBRFProducer:
    def test_empty_text(self) -> None:
        producer = BRFProducer()
        result = producer.produce("")
        assert result.endswith(b"\r\n\x1a")
        assert len(result) > 0

    def test_single_line(self) -> None:
        producer = BRFProducer()
        result = producer.produce("⠁⠃⠉")
        assert result.endswith(b"\r\n\x1a")
        assert b"\r\n" in result
        # Braille characters UTF-8 encoded in result
        assert b"\xe2\xa0\x81" in result

    def test_multi_line_text(self) -> None:
        producer = BRFProducer()
        text = "line1\nline2\nline3"
        result = producer.produce(text)
        # CRLF line endings
        assert result.count(b"\r\n") >= 2

    def test_page_breaks(self) -> None:
        """Çok satırlı metin sayfa ayracı içermeli."""
        producer = BRFProducer(PageLayout(chars_per_line=10, lines_per_page=2))
        # 5 satırlık metin → 3 sayfa (2 satır/sayfa)
        text = "\n".join([f"{"x" * 12}" for _ in range(6)])
        result = producer.produce(text)
        # Sayfa ayracı (CRLF + FF + CRLF)
        assert result.count(b"\r\n\f\r\n") >= 1

    def test_eof_marker(self) -> None:
        producer = BRFProducer()
        result = producer.produce("test")
        assert result.endswith(b"\r\n\x1a")

    def test_turkish_braille(self) -> None:
        producer = BRFProducer()
        text = "⠍⠑⠗⠓⠁⠃⠁"  # Merhaba
        result = producer.produce(text)
        assert b"\xe2\xa0\x8d" in result  # ⠍ (⠍) karakteri UTF-8

    def test_produce_with_layout(self) -> None:
        producer = BRFProducer()
        result = producer.produce_with_layout(
            "test1\ntest2\ntest3\ntest4\ntest5",
            chars_per_line=20,
            lines_per_page=2,
        )
        assert result.endswith(b"\r\n\x1a")
        assert result.count(b"\r\n\f\r\n") >= 1  # page break

    def test_paragraph_break_preserved(self) -> None:
        """Paragraf arası boş satırlar korunmalı."""
        producer = BRFProducer(PageLayout(chars_per_line=40, lines_per_page=10))
        text = "paragraf bir\n\nparagraf iki"
        result = producer.produce(text)
        # Empty line between paragraphs should be preserved
        assert b"\r\n\r\n" in result

    def test_single_page_no_form_feed(self) -> None:
        """Tek sayfalık metinde FF olmamalı."""
        producer = BRFProducer(PageLayout(chars_per_line=40, lines_per_page=10))
        text = "kisa metin"
        result = producer.produce(text)
        assert b"\f" not in result

    def test_long_text_multiple_pages(self) -> None:
        """Uzun metin birden fazla sayfaya bölünmeli."""
        producer = BRFProducer(PageLayout(chars_per_line=20, lines_per_page=3))
        # 10+ satır oluşturacak metin
        text = "\n".join(["satir" for _ in range(15)])
        result = producer.produce(text)
        # En az 2 sayfa olmalı (3 satır/sayfa, 15 satır → 5 sayfa)
        assert result.count(b"\r\n\f\r\n") >= 2


# ── BRL Producer tests ─────────────────────────────────────────────────


class TestBRLProducer:
    def test_simple_text(self) -> None:
        producer = BRLProducer()
        result = producer.produce("⠁⠃⠉")
        assert "⠁⠃⠉" in result
        assert "\x1a" not in result  # BRL'de Ctrl+Z yok

    def test_multi_line(self) -> None:
        producer = BRLProducer()
        result = producer.produce("a\nb\nc")
        assert result.count("\n") >= 2

    def test_page_separator(self) -> None:
        """Sayfalar arası boş satır olmalı."""
        producer = BRLProducer(PageLayout(chars_per_line=20, lines_per_page=2))
        text = "\n".join(["x" * 10 for _ in range(10)])
        result = producer.produce(text)
        # Sayfa aralarında boş satır
        assert "\n\n" in result


# ── Display Producer tests ─────────────────────────────────────────────


class TestDisplayProducer:
    def test_passthrough(self) -> None:
        producer = DisplayProducer()
        text = "⠍⠑⠗⠓⠁⠃⠁ dünya"
        result = producer.produce(text)
        assert result == text

    def test_no_modifications(self) -> None:
        producer = DisplayProducer()
        text = "line1\nline2\n\nline3"
        result = producer.produce(text)
        assert result == text  # Hiçbir düzenleme yok


# ── OutputMode / OutputFormat tests ────────────────────────────────────


class TestOutputEnums:
    def test_output_mode_values(self) -> None:
        assert OutputMode.DISPLAY == "display"
        assert OutputMode.EMBOSSER == "embosser"
        assert OutputMode.NOTETAKER == "notetaker"

    def test_output_format_values(self) -> None:
        assert OutputFormat.BRF == "brf"
        assert OutputFormat.BRL == "brl"
        assert OutputFormat.TXT == "txt"


# ── get_producer factory test ──────────────────────────────────────────


class TestGetProducer:
    def test_display_mode(self) -> None:
        p = get_producer(OutputMode.DISPLAY)
        assert isinstance(p, DisplayProducer)

    def test_embosser_mode(self) -> None:
        p = get_producer(OutputMode.EMBOSSER)
        assert isinstance(p, BRFProducer)

    def test_notetaker_mode(self) -> None:
        p = get_producer(OutputMode.NOTETAKER)
        assert isinstance(p, BRLProducer)

    def test_custom_layout(self) -> None:
        layout = PageLayout(25, 20)
        p = get_producer(OutputMode.EMBOSSER, layout=layout)
        assert isinstance(p, BRFProducer)
        assert p.layout.chars_per_line == 25
        assert p.layout.lines_per_page == 20