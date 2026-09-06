# Admin API schemas — role management
#
# Plan v10 referansı: ADR-010 — RBAC

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RoleUpdate(BaseModel):
    """Kullanıcı rolü güncelleme (admin)."""

    role: str = Field(
        ...,
        description="Yeni rol: super_admin, admin, billing, support, user",
    )


class UserAdminRead(BaseModel):
    """Admin panelinde dönen kullanıcı bilgisi (role dahil)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str | None = None
    locale: str = "tr"
    status: str
    role: str
    plan_code: str | None = None
    created_at: object
    last_login_at: object | None = None


class PermissionItem(BaseModel):
    """İzin bilgisi (rol yönetimi sayfası için)."""

    code: str
    description_tr: str
    description_en: str
