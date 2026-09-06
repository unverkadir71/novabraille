# Braille çıktı formatı üreticileri
#
# Plan v9 referansı: Bölüm 1.10.6 — Çıktı Formatları (ADR-008)
# Bölüm 1.10.4 — Combo Box Yapısı
#
# Desteklenen çıktı formatları:
#   BRF (Braille Ready File)   — Index Everest-D V4/V5 ve diğer embosser'lar
#   BRL (Braille Lite)         — BrailleNote ve nota alıcı cihazlar
#   DISPLAY                    — Braille ekranlar (sayfa sonu yok, cihaza bırakılır)
#
# Referans: BRAILLE.md (Memory) — BRF format kuralları:
#   Satır sonu: \r\n (CRLF)
#   Sayfa ayracı: \f (0x0C) — her iki yanında \r\n olmalı (\r\n\f\r\n)
#   Belge sonu: \x1a (Ctrl+Z footer)

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# ── Enum types ─────────────────────────────────────────────────────────


class OutputMode(StrEnum):
    """Çıktı modu — Combo Box 2'deki seçenek."""

    DISPLAY = "display"  # Braille ekranlar için
    EMBOSSER = "embosser"  # Yazdırmaya hazırla (BRF)
    NOTETAKER = "notetaker"  # Nota alıcı cihaz (BRL)


class OutputFormat(StrEnum):
    """Dosya çıktı formatı."""

    BRF = "brf"  # Braille Ready File
    BRL = "brl"  # Braille Lite formatı
    TXT = "txt"  # Ham metin (display modu)
    NONE = "none"  # Doğrudan API yanıtı, dosya yok


# ── Sayfa düzeni ───────────────────────────────────────────────────────


@dataclass
class PageLayout:
    """Braille sayfa düzeni yapılandırması.

    Plan v9 referansı (Memory.md):
      Index Everest-D V4 fabrika varsayılanı:
      - A4 dikey (210×297 mm)
      - Satır başına 30 karakter
      - Sayfa başına 28 satır
      - Çift taraflı (interpoint)
    """

    chars_per_line: int = 30  # Satır başına max Braille karakter (hücre)
    lines_per_page: int = 28  # Sayfa başına max satır


# Kullanıcıya sunulacak hazır sayfa düzenleri
PAGE_LAYOUT_PRESETS: dict[str, PageLayout] = {
    "a4": PageLayout(30, 28),  # A4 dikey — Index varsayılanı
    "a4_landscape": PageLayout(40, 22),  # A4 yatay
    "letter": PageLayout(32, 25),  # Letter
}


# ── BRF Üretici ────────────────────────────────────────────────────────


@dataclass
class BraillePage:
    """Tek bir Braille sayfası."""

    lines: list[str] = field(default_factory=list)
    page_number: int = 0

    @property
    def char_count(self) -> int:
        """Sayfadaki toplam karakter sayısı (yeni satırlar hariç)."""
        return sum(len(line) for line in self.lines)


class BRFProducer:
    """BRF (Braille Ready File) üretici.

    Plan v9 + Memory.md referansı:
      - Satır sonu: \\r\\n (CRLF)
      - Sayfa ayracı: \\f (0x0C) — her iki yanında \\r\\n
      - Belge sonu: \\x1a (Ctrl+Z footer)
      - Karakter (hücre) tabanlı sayfa düzeni — bayt değil

    Kullanım:
        producer = BRFProducer(layout=PageLayout(30, 28))
        brf_bytes = producer.produce(braille_text)
    """

    CRLF = b"\r\n"
    FORM_FEED = b"\f"
    EOF_MARKER = b"\x1a"

    def __init__(self, layout: PageLayout | None = None) -> None:
        self.layout = layout or PageLayout()

    def produce(self, braille_text: str) -> bytes:
        """Braille metnini BRF formatına dönüştür.

        Args:
            braille_text: Liblouis çıktısı (Unicode Braille karakterleri)

        Returns:
            BRF formatında byte dizisi
        """
        pages = self._paginate(braille_text)
        return self._encode_pages(pages)

    def produce_with_layout(
        self, braille_text: str, chars_per_line: int, lines_per_page: int
    ) -> bytes:
        """Özel sayfa düzeni ile BRF üret."""
        self.layout = PageLayout(chars_per_line, lines_per_page)
        return self.produce(braille_text)

    # ------------------------------------------------------------------
    # Özel metotlar
    # ------------------------------------------------------------------

    def _paginate(self, text: str) -> list[BraillePage]:
        """Metni sayfalara ve satırlara böl."""
        pages: list[BraillePage] = []
        current_page_lines: list[str] = []
        current_line_chars: list[str] = []

        # Unicode normalize — satır sonlarını tek tipleştir
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        original_lines = text.split("\n")

        for original_line in original_lines:
            # Boş satır (paragraf arası) — mevcut satırı kapat ve boş satır ekle
            if not original_line.strip():
                if current_line_chars:
                    current_page_lines.append("".join(current_line_chars))
                    current_line_chars = []
                current_page_lines.append("")
                if len(current_page_lines) >= self.layout.lines_per_page:
                    pages.append(BraillePage(
                        lines=list(current_page_lines),
                        page_number=len(pages) + 1,
                    ))
                    current_page_lines = []
                continue

            # Karakterleri tek tek işle
            for char in original_line:
                current_line_chars.append(char)
                if len(current_line_chars) >= self.layout.chars_per_line:
                    current_page_lines.append("".join(current_line_chars))
                    current_line_chars = []
                    if len(current_page_lines) >= self.layout.lines_per_page:
                        pages.append(BraillePage(
                            lines=list(current_page_lines),
                            page_number=len(pages) + 1,
                        ))
                        current_page_lines = []

            # Satır sonu: mevcut satırı kapat (tam dolmadıysa bile)
            if current_line_chars:
                current_page_lines.append("".join(current_line_chars))
                current_line_chars = []
                if len(current_page_lines) >= self.layout.lines_per_page:
                    pages.append(BraillePage(
                        lines=list(current_page_lines),
                        page_number=len(pages) + 1,
                    ))
                    current_page_lines = []

        # Son sayfa
        if current_line_chars:
            current_page_lines.append("".join(current_line_chars))
        if current_page_lines:
            pages.append(BraillePage(
                lines=list(current_page_lines),
                page_number=len(pages) + 1,
            ))

        # Hiç sayfa yoksa boş sayfa
        if not pages:
            pages.append(BraillePage(lines=[""], page_number=1))

        return pages

    def _encode_pages(self, pages: list[BraillePage]) -> bytes:
        """Sayfaları BRF binary formatına kodla."""
        parts: list[bytes] = []

        for i, page in enumerate(pages):
            if i > 0:
                # Sayfa ayracı — iki yanında CRLF
                parts.append(self.CRLF)
                parts.append(self.FORM_FEED)
                parts.append(self.CRLF)

            for j, line in enumerate(page.lines):
                if j > 0:
                    parts.append(self.CRLF)
                parts.append(line.encode("utf-8"))

        # Belge sonu
        parts.append(self.CRLF)
        parts.append(self.EOF_MARKER)

        return b"".join(parts)


# ── BRL Üretici ────────────────────────────────────────────────────────


class BRLProducer:
    """BRL (Braille Lite) üretici — BrailleNote ve nota alıcı cihazlar için.

    BRL formatı BRF'e benzer ancak:
    - Sayfa ayracı ve Ctrl+Z footer kullanılmaz
    - Satır sonları platform bağımsız (LF)
    - Düz metin olarak kaydedilir

    Kullanım:
        producer = BRLProducer()
        brl_text = producer.produce(braille_text)
    """

    def __init__(self, layout: PageLayout | None = None) -> None:
        self.layout = layout or PageLayout()

    def produce(self, braille_text: str) -> str:
        """Braille metnini BRL formatına dönüştür.

        Sayfalar arasına boş satır eklenir, satırlar LF ile ayrılır.
        """
        producer = BRFProducer(layout=self.layout)
        pages = producer._paginate(braille_text)

        lines: list[str] = []
        for i, page in enumerate(pages):
            if i > 0:
                lines.append("")  # Sayfalar arası boş satır
            lines.extend(page.lines)

        return "\n".join(lines)


# ── Display Mod Üretici ────────────────────────────────────────────────


class DisplayProducer:
    """Braille ekranlar için çıktı üretici.

    Plan v9 referansı (ADR-008):
    - Sayfa sonu \\f eklenmez
    - Satır kırma yapılmaz
    - Tüm düzen cihaza bırakılır

    Kullanım:
        producer = DisplayProducer()
        display_text = producer.produce(braille_text)
    """

    def produce(self, braille_text: str) -> str:
        """Braille metnini ekran için hazırla — hiçbir düzenleme yapmaz."""
        # Cihaz kendi düzenini yapacak, ham çıktı döndür
        return braille_text


# ── Çıktı formatı seçici ───────────────────────────────────────────────


def get_producer(mode: OutputMode, layout: PageLayout | None = None) -> BRFProducer | BRLProducer | DisplayProducer:
    """Çıktı moduna göre uygun üreticiyi döndür."""
    if mode == OutputMode.EMBOSSER:
        return BRFProducer(layout=layout)
    if mode == OutputMode.NOTETAKER:
        return BRLProducer(layout=layout)
    # display modu
    return DisplayProducer()