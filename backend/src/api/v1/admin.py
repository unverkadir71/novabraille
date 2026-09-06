# Admin router — /api/v1/admin
#
# Plan v10 referansı: ADR-010 (RBAC), ADR-011 (Admin paneli), ADR-013 (Plan yapısı)
#
# Tüm admin endpoint'leri role bazlı korumalıdır.
# Hosted-only endpoint'ler (plan yönetimi) self-hosted modda 404 döner.

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...models.plan import Entitlement, Plan
from ...models.user import User
from ...schemas.admin import RoleUpdate, UserAdminRead
from ...schemas.plan import PlanCreate, PlanDetailRead, PlanUpdate
from ...services.audit import audit_log
from ...services.entitlement import entitlement_service
from ...services.rbac import (
    Permission,
    Role,
    get_permissions_for_role,
)
from ...services.user import user_service
from ..errors import not_found
from .deps import require_admin, require_permission

router = APIRouter(prefix="/admin", tags=["admin"])

# ── Tip alias ───────────────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ── Yardımcı ───────────────────────────────────────────────────────────


def _hosted_only() -> None:
    """Self-hosted modda 404 döner (gizli bölüm)."""
    if settings.is_self_hosted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Bu bölüm bu uygulama modunda mevcut değil."},
        )


# ── Kullanıcı Yönetimi (admin) ─────────────────────────────────────────


@router.get(
    "/users",
    response_model=list[UserAdminRead],
    summary="Tüm kullanıcıları listele (admin)",
)
async def list_users_admin(
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.VIEW_USERS))],
) -> list[UserAdminRead]:
    """Kullanıcıları role ve durum bilgisiyle listeler."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [UserAdminRead.model_validate(u) for u in users]


@router.get(
    "/users/{user_id}",
    response_model=UserAdminRead,
    summary="Tek bir kullanıcının admin detayını getir",
)
async def get_user_admin(
    user_id: str,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.VIEW_USERS))],
) -> UserAdminRead:
    """Belirli bir kullanıcının detayını getirir."""
    user = await user_service.get_by_id(db, user_id)
    if user is None:
        raise not_found(code="USER_NOT_FOUND", message="Kullanıcı bulunamadı.")
    return UserAdminRead.model_validate(user)


@router.put(
    "/users/{user_id}/role",
    response_model=UserAdminRead,
    summary="Kullanıcı rolünü güncelle (super_admin)",
)
async def update_user_role(
    user_id: str,
    body: RoleUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_ROLES))],
) -> UserAdminRead:
    """Kullanıcı rolünü değiştirir. Yalnızca super_admin (hosted only)."""
    _hosted_only()
    user = await user_service.get_by_id(db, user_id)
    if user is None:
        raise not_found(code="USER_NOT_FOUND", message="Kullanıcı bulunamadı.")

    try:
        new_role = Role(body.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_ROLE",
                "message": f"Geçersiz rol: {body.role!r}",
            },
        ) from None

    # Kendi rolünü değiştirme koruması (kilitlenmeyi önle)
    if user.id == current_user.id and new_role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CANNOT_DEMOTE_SELF",
                "message": "Kendi super_admin rolünüzü değiştiremezsiniz.",
            },
        )

    old_role = user.role
    user.role = new_role.value
    await db.commit()
    await db.refresh(user)

    audit_log.role_changed(current_user.id, user.id, old_role, new_role.value)

    return UserAdminRead.model_validate(user)


# ── Roller ve İzinler (hosted only) ────────────────────────────────────


@router.get(
    "/roles/permissions",
    summary="Rol-izin matrisini getir (admin)",
    dependencies=[Depends(_hosted_only)],
)
async def get_role_permissions(
    current_user: Annotated[User, Depends(require_admin)],
) -> dict[str, list[str]]:
    """Her rolün izin listesini döndürür (izin matrisi için)."""
    result: dict[str, list[str]] = {}
    for role in Role:
        perms = get_permissions_for_role(role, settings.is_self_hosted)
        result[role.value] = sorted(p.value for p in perms)
    return result


@router.get(
    "/mode",
    summary="Uygulama modunu döndür (admin)",
)
async def get_app_mode(
    current_user: Annotated[User, Depends(require_admin)],
) -> dict[str, str]:
    """Uygulama modunu ve ilgili meta bilgileri döndürür.

    Hosted: plan/ödeme/abonelik/roller bölümleri görünür.
    Self-hosted: sadece kullanıcı, hukuki, SMTP bölümleri görünür.
    """
    return {
        "app_mode": settings.app_mode,
        "is_hosted": settings.is_hosted,
        "is_self_hosted": settings.is_self_hosted,
    }


# ── Plan Yönetimi (hosted only) ────────────────────────────────────────


@router.get(
    "/plans",
    response_model=list[PlanDetailRead],
    summary="Tüm planları entitlement'larıyla listele (admin)",
)
async def list_plans_admin(
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLANS))],
) -> list[PlanDetailRead]:
    """Planları entitlement'larıyla birlikte listeler."""
    _hosted_only()

    result = await db.execute(select(Plan).order_by(Plan.sort_order))
    plans = result.scalars().all()

    items: list[PlanDetailRead] = []
    for plan in plans:
        entitlements = await entitlement_service.get_entitlements(db, plan.plan_code)
        items.append(
            PlanDetailRead(
                plan_code=plan.plan_code,
                name_tr=plan.name_tr,
                name_en=plan.name_en,
                description_tr=plan.description_tr,
                description_en=plan.description_en,
                price_monthly=plan.price_monthly,
                price_annual=plan.price_annual,
                is_active=plan.is_active,
                sort_order=plan.sort_order,
                entitlements=entitlements,
            )
        )
    return items


@router.post(
    "/plans",
    response_model=PlanDetailRead,
    status_code=201,
    summary="Yeni plan oluştur (admin)",
)
async def create_plan(
    body: PlanCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLANS))],
) -> PlanDetailRead:
    """Yeni plan ve entitlement'larını oluşturur."""
    _hosted_only()

    existing = await entitlement_service.get_plan(db, body.plan_code)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PLAN_EXISTS", "message": f"Plan zaten mevcut: {body.plan_code!r}"},
        )

    plan = Plan(
        plan_code=body.plan_code,
        name_tr=body.name_tr,
        name_en=body.name_en,
        description_tr=body.description_tr,
        description_en=body.description_en,
        price_monthly=body.price_monthly,
        price_annual=body.price_annual,
        sort_order=body.sort_order,
        is_active=True,
    )
    db.add(plan)
    await db.flush()

    for feature_code, limit_value in body.entitlements.items():
        db.add(
            Entitlement(
                plan_code=body.plan_code,
                feature_code=feature_code,
                limit_value=limit_value,
            )
        )
    await db.commit()

    audit_log.plan_created(current_user.id, body.plan_code)

    return PlanDetailRead(
        plan_code=plan.plan_code,
        name_tr=plan.name_tr,
        name_en=plan.name_en,
        description_tr=plan.description_tr,
        description_en=plan.description_en,
        price_monthly=plan.price_monthly,
        price_annual=plan.price_annual,
        is_active=plan.is_active,
        sort_order=plan.sort_order,
        entitlements=body.entitlements,
    )


@router.put(
    "/plans/{plan_code}",
    response_model=PlanDetailRead,
    summary="Plan güncelle (admin)",
)
async def update_plan(
    plan_code: str,
    body: PlanUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLANS))],
) -> PlanDetailRead:
    """Plan bilgilerini ve entitlement'larını günceller."""
    _hosted_only()

    plan = await entitlement_service.get_plan(db, plan_code)
    if plan is None:
        raise not_found(code="PLAN_NOT_FOUND", message="Plan bulunamadı.")

    if body.name_tr is not None:
        plan.name_tr = body.name_tr
    if body.name_en is not None:
        plan.name_en = body.name_en
    if body.description_tr is not None:
        plan.description_tr = body.description_tr
    if body.description_en is not None:
        plan.description_en = body.description_en
    if body.price_monthly is not None:
        plan.price_monthly = body.price_monthly
    if body.price_annual is not None:
        plan.price_annual = body.price_annual
    if body.is_active is not None:
        plan.is_active = body.is_active
    if body.sort_order is not None:
        plan.sort_order = body.sort_order

    # Entitlement güncelleme
    if body.entitlements is not None:
        # Mevcut entitlement'ları sil ve yeniden ekle
        existing_ents = await db.execute(
            select(Entitlement).where(Entitlement.plan_code == plan_code)
        )
        for ent in existing_ents.scalars():
            await db.delete(ent)
        for feature_code, limit_value in body.entitlements.items():
            db.add(
                Entitlement(
                    plan_code=plan_code,
                    feature_code=feature_code,
                    limit_value=limit_value,
                )
            )

    await db.commit()
    await db.refresh(plan)

    entitlements = await entitlement_service.get_entitlements(db, plan_code)
    audit_log.plan_updated(current_user.id, plan_code)

    return PlanDetailRead(
        plan_code=plan.plan_code,
        name_tr=plan.name_tr,
        name_en=plan.name_en,
        description_tr=plan.description_tr,
        description_en=plan.description_en,
        price_monthly=plan.price_monthly,
        price_annual=plan.price_annual,
        is_active=plan.is_active,
        sort_order=plan.sort_order,
        entitlements=entitlements,
    )


@router.delete(
    "/plans/{plan_code}",
    status_code=204,
    summary="Plan arşivle (admin)",
)
async def archive_plan(
    plan_code: str,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLANS))],
) -> None:
    """Planı arşivler (yeni abonelik almasın ama mevcutlar devam etsin)."""
    _hosted_only()

    plan = await entitlement_service.get_plan(db, plan_code)
    if plan is None:
        raise not_found(code="PLAN_NOT_FOUND", message="Plan bulunamadı.")

    plan.is_active = False
    await db.commit()

    audit_log.plan_archived(current_user.id, plan_code)
