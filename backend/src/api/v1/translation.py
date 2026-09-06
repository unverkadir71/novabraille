# Translation router — /api/v1/tables, /api/v1/translate, /api/v1/back-translate
#
# Plan v9 referansı: Faz 2.1.4 (tables endpoint), Faz 2.2 (translate endpoints)
# Tablo listesi herkese açıktır. Çeviri endpoint'leri auth gerektirir.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from ...schemas.contraction import (
    ContractionCategoryItem,
    ContractionLevelItem,
    ContractionProfileItem,
)
from ...schemas.translation import (
    BackTranslateRequest,
    BackTranslateResponse,
    TableItem,
    TableLanguageItem,
    TranslateRequest,
    TranslateResponse,
)
from ...services.audit import audit_log
from ...services.translation import translation_service
from ...translation import BrailleGrade, get_manifest
from ...translation.contraction_config import (
    CONTRACTION_CATEGORIES,
    CONTRACTION_PROFILES,
    get_contraction_profile,
)
from ...translation.exceptions import (
    EmptyInputError,
    TableNotFoundError,
    TranslationFailedError,
)
from .deps import CurrentUser

router = APIRouter(prefix="/tables", tags=["translation"])

# ── Herkese açık endpoint'ler ─────────────────────────────────────────────


@router.get("/languages", summary="Desteklenen dilleri listele")
async def list_languages(
    priority_only: Annotated[
        bool,
        Query(description="Yalnızca 8 öncelikli dili göster"),
    ] = False,
) -> list[TableLanguageItem]:
    """Sistemde mevcut tüm dillerin ISO kodlarını ve adlarını döner."""
    manifest = get_manifest()
    languages = manifest.list_languages(priority_only=priority_only)
    return [TableLanguageItem(**lang) for lang in languages]


@router.get("", summary="Braille tablolarını listele")
async def list_tables(
    language: Annotated[
        str | None,
        Query(description="ISO 639-1 dil koduna göre filtrele (örn. 'tr')"),
    ] = None,
    grade: Annotated[
        str | None,
        Query(
            description="Kısaltma düzeyi: grade0, grade1, grade2",
            pattern=r"^grade[012]$",
        ),
    ] = None,
    priority_only: Annotated[
        bool,
        Query(description="Yalnızca 8 öncelikli dilin tablolarını göster"),
    ] = False,
    type: Annotated[
        str | None,
        Query(
            description="Tablo türü: literary, computer",
            pattern=r"^(literary|computer)$",
        ),
    ] = None,
) -> list[TableItem]:
    """Mevcut Braille tablolarını filtreleme seçenekleriyle listeler."""
    manifest = get_manifest()

    grade_enum = None
    if grade:
        grade_map: dict[str, BrailleGrade] = {
            "grade0": BrailleGrade.GRADE_0,
            "grade1": BrailleGrade.GRADE_1,
            "grade2": BrailleGrade.GRADE_2,
        }
        grade_enum = grade_map[grade]

    entries = manifest.filter(
        language=language,
        grade=grade_enum,
        table_type=type,
        priority_languages_only=priority_only,
    )

    result: list[TableItem] = []
    for entry in entries:
        item = TableItem(
            id=entry.id,
            language=entry.language,
            grade=entry.grade.value if entry.grade else None,
            type=entry.table_type,
            dots=entry.dots,
            contraction=entry.contraction,
            supports_back_translation=entry.supports_back_translation,
            name_tr=entry.human_name.tr if entry.human_name else None,
            name_en=entry.human_name.en if entry.human_name else None,
        )
        result.append(item)
    return result


@router.get("/{table_id}", summary="Tek bir tablonun detayını getir")
async def get_table(table_id: str) -> TableItem:
    """Belirli bir Braille tablosunun tüm metadata'sını döner."""
    manifest = get_manifest()
    entry = manifest.get(table_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TABLE_NOT_FOUND",
                "message": f"Braille tablosu bulunamadı: {table_id!r}",
            },
        )

    return TableItem(
        id=entry.id,
        language=entry.language,
        grade=entry.grade.value if entry.grade else None,
        type=entry.table_type,
        dots=entry.dots,
        contraction=entry.contraction,
        supports_back_translation=entry.supports_back_translation,
        name_tr=entry.human_name.tr if entry.human_name else None,
        name_en=entry.human_name.en if entry.human_name else None,
    )


# ── Kısaltma profili endpoint'leri (herkese açık) ────────────────────

contraction_router = APIRouter(prefix="/contractions", tags=["translation"])


@contraction_router.get(
    "/languages", summary="Tüm dillerin kısaltma profillerini listele"
)
async def list_contraction_profiles() -> list[ContractionProfileItem]:
    """Her dilin kısaltma düzeylerini ve açıklamalarını döner."""
    result: list[ContractionProfileItem] = []
    for profile in CONTRACTION_PROFILES.values():
        result.append(
            ContractionProfileItem(
                language_code=profile.language_code,
                language_name_tr=profile.language_name_tr,
                language_name_en=profile.language_name_en,
                supports_contraction=profile.supports_contraction,
                default_level_id=profile.default_level_id,
                levels=[
                    ContractionLevelItem(
                        id=lvl.id,
                        label_tr=lvl.label_tr,
                        label_en=lvl.label_en,
                        description_tr=lvl.description_tr,
                        description_en=lvl.description_en,
                    )
                    for lvl in profile.levels
                ],
                info_message_tr=profile.info_message_tr,
                info_message_en=profile.info_message_en,
            )
        )
    return result


@contraction_router.get(
    "/{language_code}/categories",
    summary="Belirli bir dilin kısaltma kategorilerini listele",
)
async def get_contraction_categories(
    language_code: str,
) -> list[ContractionCategoryItem]:
    """Dil için onay kutusu seçimine uygun kısaltma kategorilerini döner.
    Şimdilik yalnızca Türkçe'de 5 kategori vardır (MEB/Ankara Üniv. müfredatı).
    """
    categories = CONTRACTION_CATEGORIES.get(language_code)
    if categories is None:
        return []
    return [
        ContractionCategoryItem(
            id=cat.id,
            label_tr=cat.label_tr,
            label_en=cat.label_en,
            description_tr=cat.description_tr,
            description_en=cat.description_en,
            sort_order=cat.sort_order,
        )
        for cat in sorted(categories, key=lambda c: c.sort_order)
    ]


@contraction_router.get(
    "/{language_code}",
    summary="Belirli bir dilin kısaltma profilini getir",
)
async def get_contraction_profile_for_language(
    language_code: str,
) -> ContractionProfileItem:
    """ISO 639-1 dil kodu için kısaltma profilini döner."""
    profile = get_contraction_profile(language_code)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "LANGUAGE_NOT_FOUND",
                "message": (
                    f"Kısaltma profili bulunamadı: {language_code!r}. "
                    "Desteklenen: tr, en, de, fr, es, ar, ru, pt"
                ),
            },
        )

    return ContractionProfileItem(
        language_code=profile.language_code,
        language_name_tr=profile.language_name_tr,
        language_name_en=profile.language_name_en,
        supports_contraction=profile.supports_contraction,
        default_level_id=profile.default_level_id,
        levels=[
            ContractionLevelItem(
                id=lvl.id,
                label_tr=lvl.label_tr,
                label_en=lvl.label_en,
                description_tr=lvl.description_tr,
                description_en=lvl.description_en,
            )
            for lvl in profile.levels
        ],
        info_message_tr=profile.info_message_tr,
        info_message_en=profile.info_message_en,
    )


# ── Kimlik doğrulama gerektiren endpoint'ler ────────────────────────────

translate_router = APIRouter(prefix="/translate", tags=["translation"])


@translate_router.post("", response_model=TranslateResponse, status_code=200)
async def translate_text(
    body: TranslateRequest,
    current_user: CurrentUser,  # noqa: ARG001
) -> TranslateResponse:
    """Metni Braille'e çevirir. Kimlik doğrulama gerektirir."""
    try:
        result = await translation_service.translate(
            body.text,
            body.table_id,
            grade=body.grade,
        )
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

    audit_log.translation_completed(
        current_user.id, body.table_id, result.char_count
    )

    return TranslateResponse(
        braille=result.text,
        table_id=result.table_id,
        char_count=result.char_count,
    )


@translate_router.post("/back", response_model=BackTranslateResponse, status_code=200)
async def back_translate_text(
    body: BackTranslateRequest,
    current_user: CurrentUser,  # noqa: ARG001
) -> BackTranslateResponse:
    """Braille'i metne geri çevirir. Kimlik doğrulama gerektirir."""
    try:
        result = await translation_service.back_translate(
            body.braille,
            body.table_id,
        )
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

    audit_log.translation_completed(
        current_user.id, body.table_id, result.char_count
    )

    return BackTranslateResponse(
        text=result.text,
        table_id=result.table_id,
        char_count=result.char_count,
    )