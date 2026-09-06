# Output format router — /api/v1/output
#
# Plan v9 referansı: Faz 2.5 — Çıktı Formatları (ADR-008)
# Combo Box akışı: dil → çıktı modu → profil/yazıcı

from __future__ import annotations

import base64
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, status

from ...schemas.output_format import (
    FileDownloadResponse,
    OutputFileFormat,
    OutputModeItem,
    PageLayoutItem,
)
from ...schemas.translation import TranslateResponse
from ...services.audit import audit_log
from ...services.translation import translation_service
from ...translation import OutputMode, get_producer
from ...translation.exceptions import (
    EmptyInputError,
    TableNotFoundError,
    TranslationFailedError,
)
from ...translation.output_formats import PAGE_LAYOUT_PRESETS, OutputFormat
from .deps import CurrentUser

router = APIRouter(prefix="/output", tags=["output"])

# ── Dosya formatı tanımları (her mod için desteklenen formatlar) ────────

# Referanslar:
#   Braille ekranlar: Unicode Braille karakterleri (U+2800-U+28FF), tüm ekranlar okur.
#     Bazı ekranlar BRF de okuyabilir (Orbit Reader, Brailliant BI X).
#   Embosser: BRF standarttır (sayfa düzenli, FF ayraçlı). Düz TXT de basılabilir.
#   Nota alıcı: BRL native formattır (BrailleNote, BrailleSense). BRF ve TXT de okur.
#   Kaynak: DAISY Consortium eBraille Problem Statement, Library of Congress BRF spec,
#     Helen Keller Services braille display comparison (2023).

_OUTPUT_FILE_FORMATS: dict[str, list[OutputFileFormat]] = {
    "display": [
        OutputFileFormat(
            id="txt",
            label_tr="Unicode Braille Metin (.txt)",
            label_en="Unicode Braille Text (.txt)",
            extension=".txt",
            description_tr="Unicode Braille karakterleri (U+2800–U+28FF). Tüm Braille ekranlar tarafından doğrudan okunur. Satır kırma ve sayfa düzeni uygulanmaz — düzen cihaza bırakılır.",
            description_en="Unicode Braille characters (U+2800–U+28FF). Read directly by all braille displays. No line wrapping or page layout — formatting is left to the device.",
            recommended=True,
        ),
        OutputFileFormat(
            id="brf",
            label_tr="BRF (Braille Ready File) (.brf)",
            label_en="BRF (Braille Ready File) (.brf)",
            extension=".brf",
            description_tr="ASCII Braille formatında, sayfa düzeni uygulanmış. Orbit Reader, Brailliant BI X gibi BRF destekleyen ekranlarda okunabilir.",
            description_en="ASCII braille with page layout. Readable on BRF-compatible displays like Orbit Reader, Brailliant BI X.",
            recommended=False,
        ),
    ],
    "embosser": [
        OutputFileFormat(
            id="brf",
            label_tr="BRF (Braille Ready File) (.brf)",
            label_en="BRF (Braille Ready File) (.brf)",
            extension=".brf",
            description_tr="Sayfa düzeni uygulanmış, form feed (\f) sayfa ayraçlı, CRLF satır sonlu. Index Everest-D V4/V5 ve tüm embosser'lar için standart format. Doğrudan basıma hazır.",
            description_en="Page layout applied, form feed (\f) page breaks, CRLF line endings. Standard format for Index Everest-D V4/V5 and all embossers. Ready to print.",
            recommended=True,
        ),
        OutputFileFormat(
            id="txt",
            label_tr="ASCII Braille Metin (.txt)",
            label_en="ASCII Braille Text (.txt)",
            extension=".txt",
            description_tr="ASCII Braille karakterleri, sayfa düzeni uygulanmamış. Ham çıktı olarak basılabilir ancak sayfa sonu ve kenar boşlukları embosser kontrol paneline bırakılır.",
            description_en="ASCII braille characters without page layout. Can be printed as raw output but page breaks and margins are left to the embosser control panel.",
            recommended=False,
        ),
    ],
    "notetaker": [
        OutputFileFormat(
            id="brl",
            label_tr="BRL (Braille Lite) (.brl)",
            label_en="BRL (Braille Lite) (.brl)",
            extension=".brl",
            description_tr="BrailleNote, BrailleSense ve çoğu nota alıcı cihaz için native format. CRLF satır sonlu, sayfa düzeni uygulanmış.",
            description_en="Native format for BrailleNote, BrailleSense and most notetakers. CRLF line endings, page layout applied.",
            recommended=True,
        ),
        OutputFileFormat(
            id="brf",
            label_tr="BRF (Braille Ready File) (.brf)",
            label_en="BRF (Braille Ready File) (.brf)",
            extension=".brf",
            description_tr="ASCII Braille formatında, sayfa düzeni uygulanmış. Çoğu nota alıcı cihaz BRF dosyalarını da okuyabilir.",
            description_en="ASCII braille with page layout. Most notetakers can also read BRF files.",
            recommended=False,
        ),
        OutputFileFormat(
            id="txt",
            label_tr="ASCII Braille Metin (.txt)",
            label_en="ASCII Braille Text (.txt)",
            extension=".txt",
            description_tr="ASCII Braille karakterleri, sayfa düzeni uygulanmamış. Evrensel — tüm cihazlarda okunabilir.",
            description_en="ASCII braille characters without page layout. Universal — readable on all devices.",
            recommended=False,
        ),
    ],
}

# ── Mod tanımları (sadeleştirilmiş — açıklama yok) ────────────────────

_OUTPUT_MODES: list[OutputModeItem] = [
    OutputModeItem(
        id="display",
        label_tr="Braille Ekran",
        label_en="Braille Display",
        file_formats=_OUTPUT_FILE_FORMATS["display"],
    ),
    OutputModeItem(
        id="embosser",
        label_tr="Embosser (Yazıcı)",
        label_en="Embosser (Printer)",
        file_formats=_OUTPUT_FILE_FORMATS["embosser"],
    ),
    OutputModeItem(
        id="notetaker",
        label_tr="Nota Alıcı Cihaz",
        label_en="Notetaker Device",
        file_formats=_OUTPUT_FILE_FORMATS["notetaker"],
    ),
]

_LAYOUT_LABELS: dict[str, dict[str, str]] = {
    "a4": {"tr": "A4 Dikey (30×28)", "en": "A4 Portrait (30×28)"},
    "a4_landscape": {"tr": "A4 Yatay (40×22)", "en": "A4 Landscape (40×22)"},
    "letter": {"tr": "Letter (32×25)", "en": "Letter (32×25)"},
}


# ── Herkese açık endpoint'ler ──────────────────────────────────────────


@router.get("/modes", summary="Çıktı modlarını listele")
async def list_output_modes() -> list[OutputModeItem]:
    """Braille ekran, embosser ve nota alıcı için çıktı modlarını listeler.

    Her modun desteklediği dosya formatlarını da içerir.
    """
    return _OUTPUT_MODES


@router.get(
    "/modes/{mode_id}/formats",
    summary="Belirli bir mod için dosya formatlarını listele",
)
async def list_mode_formats(mode_id: str) -> list[OutputFileFormat]:
    """Seçilen mod için desteklenen dosya formatlarını döndürür."""
    if mode_id not in _OUTPUT_FILE_FORMATS:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MODE_NOT_FOUND", "message": f"Mod bulunamadı: {mode_id!r}"},
        )
    return _OUTPUT_FILE_FORMATS[mode_id]


@router.get("/layouts", summary="Sayfa düzeni seçeneklerini listele")
async def list_page_layouts() -> list[PageLayoutItem]:
    """BRF/BRL için hazır sayfa düzeni seçeneklerini listeler."""
    result: list[PageLayoutItem] = []
    for preset_id, layout in PAGE_LAYOUT_PRESETS.items():
        labels = _LAYOUT_LABELS.get(preset_id, {"tr": preset_id, "en": preset_id})
        result.append(
            PageLayoutItem(
                id=preset_id,
                label_tr=labels["tr"],
                label_en=labels["en"],
                chars_per_line=layout.chars_per_line,
                lines_per_page=layout.lines_per_page,
            )
        )
    return result


# ── Kimlik doğrulama gerektiren endpoint'ler ────────────────────────────


@router.post(
    "/translate",
    response_model=TranslateResponse,
    status_code=200,
    summary="Çevir ve çıktı moduna göre formatla",
)
async def translate_with_output(
    text: Annotated[str, Body(..., min_length=1, max_length=500_000)],
    table_id: Annotated[str, Body(..., max_length=50)],
    mode: Annotated[str, Body()] = "display",
    grade: Annotated[str | None, Body()] = None,
    current_user: CurrentUser = None,  # noqa: ARG001
) -> TranslateResponse:
    """Metni Braille'e çevirir ve belirtilen çıktı modunda formatlar."""
    try:
        output_mode = OutputMode(mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_MODE",
                "message": f"Geçersiz çıktı modu: {mode!r}. Desteklenen: display, embosser, notetaker",
            },
        ) from None

    try:
        result = await translation_service.translate(text, table_id, grade=grade)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_INPUT", "message": str(e)},
        ) from e
    except EmptyInputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "EMPTY_INPUT", "message": str(e)},
        ) from e
    except (TableNotFoundError, TranslationFailedError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TRANSLATION_FAILED", "message": str(e)},
        ) from e

    # Seçilen moda göre formatla
    producer = get_producer(output_mode)
    formatted = producer.produce(result.text)

    audit_log.translation_completed(
        current_user.id, table_id, result.char_count
    )

    return TranslateResponse(
        braille=(
            formatted
            if isinstance(formatted, str)
            else formatted.decode("utf-8", errors="replace")
        ),
        table_id=result.table_id,
        char_count=result.char_count,
    )


@router.post(
    "/download",
    response_model=FileDownloadResponse,
    status_code=200,
    summary="BRF/BRL dosyası olarak indir",
)
async def download_formatted(
    text: Annotated[str, Body(..., min_length=1, max_length=500_000)],
    table_id: Annotated[str, Body(..., max_length=50)],
    output_format: Annotated[str, Body()] = "brf",
    grade: Annotated[str | None, Body()] = None,
    chars_per_line: Annotated[int, Body()] = 30,
    lines_per_page: Annotated[int, Body()] = 28,
    current_user: CurrentUser = None,  # noqa: ARG001
) -> FileDownloadResponse:
    """Metni Braille'e çevir ve BRF/BRL dosyası olarak döndür."""
    try:
        fmt = OutputFormat(output_format)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_FORMAT",
                "message": f"Geçersiz format: {output_format!r}. Desteklenen: brf, brl",
            },
        ) from None

    try:
        result = await translation_service.translate(text, table_id, grade=grade)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_INPUT", "message": str(e)},
        ) from e
    except EmptyInputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "EMPTY_INPUT", "message": str(e)},
        ) from e
    except (TableNotFoundError, TranslationFailedError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TRANSLATION_FAILED", "message": str(e)},
        ) from e

    # Formatla
    if fmt == OutputFormat.BRF:
        from ...translation.output_formats import BRFProducer, PageLayout
        producer = BRFProducer(PageLayout(chars_per_line, lines_per_page))
        output_bytes = producer.produce(result.text)
        mime = "application/octet-stream"
        ext = ".brf"
    else:
        from ...translation.output_formats import BRLProducer, PageLayout
        producer = BRLProducer(PageLayout(chars_per_line, lines_per_page))
        formatted_text = producer.produce(result.text)
        output_bytes = formatted_text.encode("utf-8")
        mime = "text/plain; charset=utf-8"
        ext = ".brl"

    filename = f"nova-braille-{result.table_id.replace('.', '-')}{ext}"

    audit_log.translation_completed(
        current_user.id, table_id, result.char_count
    )

    return FileDownloadResponse(
        content_base64=base64.b64encode(output_bytes).decode("ascii"),
        filename=filename,
        mime_type=mime,
        byte_size=len(output_bytes),
        output_format=fmt.value,
    )