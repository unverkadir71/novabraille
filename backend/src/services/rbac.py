# Role-based access control (RBAC) — roles, permissions, and mapping
#
# Plan v10 referansı: ADR-010 — Rol tabanlı yetkilendirme sistemi
#
# İki bağımsız katman:
#   User.role      → admin panelinde ne yapabileceği (iç ekip yetkisi)
#   User.plan_code → son kullanıcının hangi çeviri özelliklerine erişebileceği
#
# Hosted roller (4):  super_admin, admin, billing, support
# Self-hosted roller (2): admin, user
# Son kullanıcı rolü: user (her iki modda da)

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Kullanıcı rollerinin tanımları."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    BILLING = "billing"
    SUPPORT = "support"
    USER = "user"


class Permission(StrEnum):
    """Admin paneli izinleri."""

    # Dashboard
    VIEW_DASHBOARD = "view_dashboard"

    # Kullanıcı yönetimi
    MANAGE_USERS = "manage_users"  # oluşturma, dondurma, silme
    VIEW_USERS = "view_users"  # listeleme ve detay görüntüleme
    MANAGE_ROLES = "manage_roles"  # rol atama/değiştirme

    # Abonelik (hosted)
    MANAGE_SUBSCRIPTIONS = "manage_subscriptions"  # durdurma, iptal
    VIEW_SUBSCRIPTIONS = "view_subscriptions"  # listeleme

    # Plan yönetimi (hosted)
    MANAGE_PLANS = "manage_plans"  # oluştur, düzenle, arşivle

    # Ödeme ayarları (hosted)
    MANAGE_PAYMENT_SETTINGS = "manage_payment_settings"  # API anahtarı, webhook

    # Hukuki belgeler
    MANAGE_LEGAL = "manage_legal"

    # Site ayarları
    MANAGE_SITE_SETTINGS = "manage_site_settings"

    # E-posta
    MANAGE_EMAIL = "manage_email"

    # Yedekleme
    MANAGE_BACKUPS = "manage_backups"

    # Loglar
    VIEW_AUDIT_LOG = "view_audit_log"
    VIEW_EMAIL_LOGS = "view_email_logs"
    VIEW_TRANSLATION_LOGS = "view_translation_logs"


# Rol → İzin eşleştirmesi (hosted mod)
# Self-hosted modda yalnızca admin ve user rolleri geçerlidir;
# admin, super_admin + admin izinlerinin birleşimini alır.
HOSTED_ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.SUPER_ADMIN: frozenset({
        Permission.VIEW_DASHBOARD,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.MANAGE_ROLES,
        Permission.MANAGE_SUBSCRIPTIONS,
        Permission.VIEW_SUBSCRIPTIONS,
        Permission.MANAGE_PLANS,
        Permission.MANAGE_PAYMENT_SETTINGS,
        Permission.MANAGE_LEGAL,
        Permission.MANAGE_SITE_SETTINGS,
        Permission.MANAGE_EMAIL,
        Permission.MANAGE_BACKUPS,
        Permission.VIEW_AUDIT_LOG,
        Permission.VIEW_EMAIL_LOGS,
        Permission.VIEW_TRANSLATION_LOGS,
    }),
    Role.ADMIN: frozenset({
        Permission.VIEW_DASHBOARD,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.MANAGE_SUBSCRIPTIONS,
        Permission.VIEW_SUBSCRIPTIONS,
        Permission.MANAGE_PLANS,
        Permission.MANAGE_LEGAL,
        Permission.MANAGE_SITE_SETTINGS,
        Permission.MANAGE_EMAIL,
        Permission.MANAGE_BACKUPS,
        Permission.VIEW_AUDIT_LOG,
        Permission.VIEW_EMAIL_LOGS,
        Permission.VIEW_TRANSLATION_LOGS,
        # NOT: manage_roles, manage_payment_settings — super_admin'e özel
    }),
    Role.BILLING: frozenset({
        Permission.MANAGE_SUBSCRIPTIONS,
        Permission.VIEW_SUBSCRIPTIONS,
    }),
    Role.SUPPORT: frozenset({
        Permission.VIEW_USERS,
        Permission.VIEW_EMAIL_LOGS,
        Permission.VIEW_TRANSLATION_LOGS,
    }),
    Role.USER: frozenset(),
}

# Self-hosted modda admin, hosted'deki super_admin + admin birleşimini alır
# (ödeme/plan ile ilgili izinler anlamsız olduğu için doğal olarak dışarıda kalır,
# çünkü self-hosted'de bu endpoint'ler zaten route seviyesinde devre dışıdır).
SELF_HOSTED_ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset({
        Permission.VIEW_DASHBOARD,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.MANAGE_LEGAL,
        Permission.MANAGE_SITE_SETTINGS,
        Permission.MANAGE_EMAIL,
        Permission.MANAGE_BACKUPS,
        Permission.VIEW_AUDIT_LOG,
        Permission.VIEW_EMAIL_LOGS,
        Permission.VIEW_TRANSLATION_LOGS,
    }),
    Role.USER: frozenset(),
}

# Hosted modda geçerli roller (son kullanıcı dahil)
HOSTED_ROLES: frozenset[Role] = frozenset({
    Role.SUPER_ADMIN,
    Role.ADMIN,
    Role.BILLING,
    Role.SUPPORT,
    Role.USER,
})

# Self-hosted modda geçerli roller
SELF_HOSTED_ROLES: frozenset[Role] = frozenset({
    Role.ADMIN,
    Role.USER,
})


def get_permissions_for_role(role: Role, is_self_hosted: bool = False) -> frozenset[Permission]:
    """Bir rolün izin kümesini döndürür.

    Args:
        role: Kullanıcı rolü
        is_self_hosted: Self-hosted modda mı (rol eşleştirmesi farklı)

    Returns:
        İzin kümesi (boş olabilir)
    """
    table = SELF_HOSTED_ROLE_PERMISSIONS if is_self_hosted else HOSTED_ROLE_PERMISSIONS
    return table.get(role, frozenset())


def has_permission(role: Role, permission: Permission, is_self_hosted: bool = False) -> bool:
    """Bir rolün belirli bir izne sahip olup olmadığını döndürür."""
    return permission in get_permissions_for_role(role, is_self_hosted)


def is_valid_role_for_mode(role: Role, is_self_hosted: bool = False) -> bool:
    """Rolün geçerli modda tanımlı olup olmadığını döndürür."""
    roles = SELF_HOSTED_ROLES if is_self_hosted else HOSTED_ROLES
    return role in roles


def normalize_role(value: str | None) -> Role:
    """String değeri Role enum'a normalize eder. Geçersizse USER döner."""
    if not value:
        return Role.USER
    try:
        return Role(value)
    except ValueError:
        return Role.USER
