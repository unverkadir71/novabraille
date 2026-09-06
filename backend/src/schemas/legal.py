# Legal document schemas — hukuki belge yönetimi
#
# Plan v9 referansı: Bölüm 1.11.2
# Plan v10 görev listesi: F3.10

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LegalDocumentRead(BaseModel):
    """Public/admin listelemede dönen hukuki belge özeti."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    title_tr: str
    title_en: str
    status: str
    updated_at: object


class LegalDocumentDetail(BaseModel):
    """Tek bir hukuki belgenin tam içeriği."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    title_tr: str
    title_en: str
    content_markdown: str
    status: str
    updated_at: object


class LegalDocumentUpsert(BaseModel):
    """Admin panelinden belge oluşturma/güncelleme isteği.

    Mevcut slug için güncelleme, yeni slug için oluşturma yapar.
    """

    title_tr: str = Field(..., min_length=1, max_length=200)
    title_en: str = Field(..., min_length=1, max_length=200)
    content_markdown: str = Field(..., min_length=1)
    status: str = Field(
        "draft",
        description="draft: taslak, published: yayında",
        pattern="^(draft|published)$",
    )
