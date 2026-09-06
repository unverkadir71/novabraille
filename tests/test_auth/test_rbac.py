"""Tests for RBAC — roles, permissions, and mapping.

Plan v10: ADR-010 — Rol tabanlı yetkilendirme sistemi
"""

from __future__ import annotations

from backend.src.services.rbac import (
    Permission,
    Role,
    get_permissions_for_role,
    has_permission,
    is_valid_role_for_mode,
    normalize_role,
)


class TestRoleEnum:
    def test_all_roles(self) -> None:
        assert Role.SUPER_ADMIN.value == "super_admin"
        assert Role.ADMIN.value == "admin"
        assert Role.BILLING.value == "billing"
        assert Role.SUPPORT.value == "support"
        assert Role.USER.value == "user"

    def test_permission_values(self) -> None:
        assert Permission.VIEW_DASHBOARD.value == "view_dashboard"
        assert Permission.MANAGE_USERS.value == "manage_users"
        assert Permission.MANAGE_ROLES.value == "manage_roles"
        assert Permission.MANAGE_PLANS.value == "manage_plans"
        assert Permission.MANAGE_PAYMENT_SETTINGS.value == "manage_payment_settings"


class TestRoleMapping:
    def test_super_admin_has_all(self) -> None:
        perms = get_permissions_for_role(Role.SUPER_ADMIN)
        assert Permission.MANAGE_ROLES in perms
        assert Permission.MANAGE_PAYMENT_SETTINGS in perms
        assert Permission.MANAGE_PLANS in perms

    def test_admin_lacks_super_only_permissions(self) -> None:
        perms = get_permissions_for_role(Role.ADMIN)
        assert Permission.MANAGE_ROLES not in perms
        assert Permission.MANAGE_PAYMENT_SETTINGS not in perms
        # Admin still has most permissions
        assert Permission.MANAGE_USERS in perms
        assert Permission.MANAGE_PLANS in perms
        assert Permission.MANAGE_LEGAL in perms

    def test_billing_only_financial(self) -> None:
        perms = get_permissions_for_role(Role.BILLING)
        assert Permission.MANAGE_SUBSCRIPTIONS in perms
        assert Permission.VIEW_SUBSCRIPTIONS in perms
        assert Permission.MANAGE_USERS not in perms
        assert Permission.MANAGE_PLANS not in perms
        assert Permission.VIEW_DASHBOARD not in perms

    def test_support_readonly(self) -> None:
        perms = get_permissions_for_role(Role.SUPPORT)
        assert Permission.VIEW_USERS in perms
        assert Permission.VIEW_EMAIL_LOGS in perms
        assert Permission.VIEW_TRANSLATION_LOGS in perms
        assert Permission.MANAGE_USERS not in perms
        assert Permission.MANAGE_SUBSCRIPTIONS not in perms

    def test_user_has_no_permissions(self) -> None:
        perms = get_permissions_for_role(Role.USER)
        assert len(perms) == 0


class TestHasPermission:
    def test_has_permission_true(self) -> None:
        assert has_permission(Role.SUPER_ADMIN, Permission.MANAGE_ROLES) is True
        assert has_permission(Role.ADMIN, Permission.MANAGE_USERS) is True
        assert has_permission(Role.BILLING, Permission.VIEW_SUBSCRIPTIONS) is True

    def test_has_permission_false(self) -> None:
        assert has_permission(Role.USER, Permission.MANAGE_USERS) is False
        assert has_permission(Role.BILLING, Permission.MANAGE_USERS) is False
        assert has_permission(Role.ADMIN, Permission.MANAGE_ROLES) is False


class TestSelfHostedMapping:
    def test_self_hosted_admin_permissions(self) -> None:
        perms = get_permissions_for_role(Role.ADMIN, is_self_hosted=True)
        assert Permission.MANAGE_USERS in perms
        assert Permission.MANAGE_LEGAL in perms
        assert Permission.MANAGE_SITE_SETTINGS in perms
        # Hosted-only permissions must NOT be present
        assert Permission.MANAGE_PLANS not in perms
        assert Permission.MANAGE_PAYMENT_SETTINGS not in perms
        assert Permission.MANAGE_SUBSCRIPTIONS not in perms

    def test_self_hosted_user_no_permissions(self) -> None:
        perms = get_permissions_for_role(Role.USER, is_self_hosted=True)
        assert len(perms) == 0

    def test_self_hosted_super_admin_not_defined(self) -> None:
        # super_admin self-hosted'de geçerli değil
        assert is_valid_role_for_mode(Role.SUPER_ADMIN, is_self_hosted=True) is False


class TestValidRolesForMode:
    def test_hosted_valid_roles(self) -> None:
        assert is_valid_role_for_mode(Role.SUPER_ADMIN) is True
        assert is_valid_role_for_mode(Role.ADMIN) is True
        assert is_valid_role_for_mode(Role.BILLING) is True
        assert is_valid_role_for_mode(Role.SUPPORT) is True
        assert is_valid_role_for_mode(Role.USER) is True

    def test_self_hosted_valid_roles(self) -> None:
        assert is_valid_role_for_mode(Role.ADMIN, is_self_hosted=True) is True
        assert is_valid_role_for_mode(Role.USER, is_self_hosted=True) is True
        assert is_valid_role_for_mode(Role.BILLING, is_self_hosted=True) is False
        assert is_valid_role_for_mode(Role.SUPPORT, is_self_hosted=True) is False


class TestNormalizeRole:
    def test_valid_strings(self) -> None:
        assert normalize_role("super_admin") == Role.SUPER_ADMIN
        assert normalize_role("admin") == Role.ADMIN
        assert normalize_role("billing") == Role.BILLING

    def test_invalid_falls_back_to_user(self) -> None:
        assert normalize_role("nonexistent") == Role.USER
        assert normalize_role("") == Role.USER
        assert normalize_role(None) == Role.USER

    def test_none_falls_back_to_user(self) -> None:
        assert normalize_role(None) == Role.USER
