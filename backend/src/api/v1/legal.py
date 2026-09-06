# Legal documents router — /api/v1/legal (public) + /api/v1/admin/legal (admin)
#
# Plan v9 referansı: Bölüm 1.11.2 (KVKK ve diğer yükümlülükler)
# Plan v10 görev listesi: F3.10 (hukuki belge yönetimi API)
#
# Public: yalnızca status=published belgeler görünür.
# Admin:  tam CRUD (draft dahil), MANAGE_LEGAL izni gerektirir.
#         Hem hosted hem self-hosted modda admin erişebilir (ADR-012).

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.legal_document import LegalDocument
from ...models.user import User
from ...schemas.legal import (
    LegalDocumentDetail,
    LegalDocumentRead,
    LegalDocumentUpsert,
)
from ...services.audit import audit_log
from ...services.rbac import Permission
from ..errors import not_found
from .deps import require_permission

DbSession = Annotated[AsyncSession, Depends(get_db)]

public_router = APIRouter(prefix="/legal", tags=["legal"])
admin_router = APIRouter(prefix="/admin/legal", tags=["admin-legal"])


# ── Public endpoint'ler ─────────────────────────────────────────────────


@public_router.get(
    "",
    response_model=list[LegalDocumentRead],
    summary="Yayındaki hukuki belgeleri listele",
)
async def list_published_legal(db: DbSession) -> list[LegalDocumentRead]:
    """Public sitede gösterilen yayındaki hukuki belgelerin özetini döndürür."""
    result = await db.execute(
        select(LegalDocument)
        .where(LegalDocument.status == "published")
        .order_by(LegalDocument.slug)
    )
    docs = result.scalars().all()
    return [LegalDocumentRead.model_validate(d) for d in docs]


@public_router.get(
    "/{slug}",
    response_model=LegalDocumentDetail,
    summary="Yayındaki tek bir hukuki belgeyi getir",
)
async def get_published_legal(slug: str, db: DbSession) -> LegalDocumentDetail:
    """Yayındaki bir hukuki belgenin Markdown içeriğini döndürür."""
    result = await db.execute(
        select(LegalDocument).where(
            LegalDocument.slug == slug,
            LegalDocument.status == "published",
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise not_found(code="LEGAL_NOT_FOUND", message="Belge bulunamadı.")
    return LegalDocumentDetail.model_validate(doc)


# ── Admin endpoint'ler ─────────────────────────────────────────────────


@admin_router.get(
    "",
    response_model=list[LegalDocumentRead],
    summary="Tüm hukuki belgeleri listele (admin)",
)
async def list_all_legal(
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_LEGAL))],
) -> list[LegalDocumentRead]:
    """Draft dahil tüm hukuki belgeleri listeler."""
    result = await db.execute(select(LegalDocument).order_by(LegalDocument.slug))
    docs = result.scalars().all()
    return [LegalDocumentRead.model_validate(d) for d in docs]


@admin_router.get(
    "/{slug}",
    response_model=LegalDocumentDetail,
    summary="Tek bir hukuki belgeyi getir (admin)",
)
async def get_legal_admin(
    slug: str,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_LEGAL))],
) -> LegalDocumentDetail:
    """Belirli bir hukuki belgeyi (draft veya published) getirir."""
    result = await db.execute(
        select(LegalDocument).where(LegalDocument.slug == slug)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise not_found(code="LEGAL_NOT_FOUND", message="Belge bulunamadı.")
    return LegalDocumentDetail.model_validate(doc)


@admin_router.put(
    "/{slug}",
    response_model=LegalDocumentDetail,
    summary="Hukuki belge oluştur veya güncelle (admin)",
)
async def upsert_legal(
    slug: str,
    body: LegalDocumentUpsert,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_LEGAL))],
) -> LegalDocumentDetail:
    """Belirtilen slug için hukuki belge oluşturur veya mevcut belgeyi günceller."""
    result = await db.execute(
        select(LegalDocument).where(LegalDocument.slug == slug)
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        doc = LegalDocument(slug=slug)
        db.add(doc)
        created = True
    else:
        created = False

    doc.title_tr = body.title_tr
    doc.title_en = body.title_en
    doc.content_markdown = body.content_markdown
    doc.status = body.status

    await db.commit()
    await db.refresh(doc)

    if created:
        audit_log.legal_created(current_user.id, slug)
    else:
        audit_log.legal_updated(current_user.id, slug)

    return LegalDocumentDetail.model_validate(doc)


@admin_router.delete(
    "/{slug}",
    status_code=204,
    summary="Hukuki belgeyi sil (admin)",
)
async def delete_legal(
    slug: str,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_LEGAL))],
) -> None:
    """Belirtilen hukuki belgeyi kalıcı olarak siler."""
    result = await db.execute(
        select(LegalDocument).where(LegalDocument.slug == slug)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise not_found(code="LEGAL_NOT_FOUND", message="Belge bulunamadı.")

    await db.delete(doc)
    await db.commit()

    audit_log.legal_deleted(current_user.id, slug)
