# Audit logging — suspicious activity monitoring
#
# Plan v9 referansı: Bölüm 1.8.2, 1.17.1. PII minimize edilmiş structlog.

from __future__ import annotations

import structlog

logger = structlog.get_logger("nova_braille.audit")


class AuditLog:
    """Güvenlik denetim logları — tüm auth olaylarını kaydeder."""

    # ---------- Auth olayları ----------

    def login_success(self, user_id: str, ip: str | None = None) -> None:
        logger.info(
            "auth.login_success",
            user_id=user_id[:8],
            ip=_mask_ip(ip),
        )

    def login_failure(self, email: str, ip: str | None = None, reason: str = "invalid") -> None:
        logger.warning(
            "auth.login_failure",
            email=_mask_email(email),
            ip=_mask_ip(ip),
            reason=reason,
        )

    def login_locked(self, email: str, ip: str | None = None) -> None:
        logger.warning(
            "auth.account_locked",
            email=_mask_email(email),
            ip=_mask_ip(ip),
        )

    def password_changed(self, user_id: str) -> None:
        logger.info(
            "auth.password_changed",
            user_id=user_id[:8],
        )

    # ---------- Oturum olayları ----------

    def session_created(self, user_id: str, ip: str | None = None) -> None:
        logger.info(
            "session.created",
            user_id=user_id[:8],
            ip=_mask_ip(ip),
        )

    def session_revoked(self, user_id: str, reason: str = "logout") -> None:
        logger.info(
            "session.revoked",
            user_id=user_id[:8],
            reason=reason,
        )

    def session_expired(self, user_id: str) -> None:
        logger.info(
            "session.expired",
            user_id=user_id[:8],
        )

    def session_cleanup(self, count: int) -> None:
        logger.info(
            "session.cleanup",
            expired_count=count,
        )

    # ---------- Hesap olayları ----------

    def account_activated(self, user_id: str) -> None:
        logger.info(
            "account.activated",
            user_id=user_id[:8],
        )

    def account_created(self, user_id: str, email: str) -> None:
        logger.info(
            "account.created",
            user_id=user_id[:8],
            email=_mask_email(email),
        )

    def token_consumed(self, user_id: str, purpose: str) -> None:
        logger.info(
            "token.consumed",
            user_id=user_id[:8],
            purpose=purpose,
        )

    def token_invalidated(self, user_id: str, purpose: str) -> None:
        logger.info(
            "token.invalidated",
            user_id=user_id[:8],
            purpose=purpose,
        )

    # ---------- Dosya olayları ----------

    def file_uploaded(
        self, user_id: str, filename: str, input_format: str, file_size: int
    ) -> None:
        logger.info(
            "file.uploaded",
            user_id=user_id[:8],
            input_format=input_format,
            file_size=file_size,
            original_filename=_safe_filename(filename),
        )

    # ---------- Admin/RBAC olayları ----------

    def role_changed(
        self, actor_id: str, target_user_id: str, old_role: str, new_role: str
    ) -> None:
        logger.info(
            "admin.role_changed",
            actor_id=actor_id[:8],
            target_user_id=target_user_id[:8],
            old_role=old_role,
            new_role=new_role,
        )

    def plan_created(self, actor_id: str, plan_code: str) -> None:
        logger.info(
            "admin.plan_created",
            actor_id=actor_id[:8],
            plan_code=plan_code,
        )

    def plan_updated(self, actor_id: str, plan_code: str) -> None:
        logger.info(
            "admin.plan_updated",
            actor_id=actor_id[:8],
            plan_code=plan_code,
        )

    def plan_archived(self, actor_id: str, plan_code: str) -> None:
        logger.info(
            "admin.plan_archived",
            actor_id=actor_id[:8],
            plan_code=plan_code,
        )

    def legal_created(self, actor_id: str, slug: str) -> None:
        logger.info(
            "admin.legal_created",
            actor_id=actor_id[:8],
            slug=slug,
        )

    def legal_updated(self, actor_id: str, slug: str) -> None:
        logger.info(
            "admin.legal_updated",
            actor_id=actor_id[:8],
            slug=slug,
        )

    def legal_deleted(self, actor_id: str, slug: str) -> None:
        logger.info(
            "admin.legal_deleted",
            actor_id=actor_id[:8],
            slug=slug,
        )

    def rate_limit_hit(self, ip: str | None = None) -> None:
        logger.warning(
            "rate_limit.hit",
            ip=_mask_ip(ip),
        )

    # ---------- Veri ve hesap olayları ----------

    def data_exported(self, user_id: str) -> None:
        logger.info(
            "account.data_exported",
            user_id=user_id[:8],
        )

    def account_closed(self, user_id: str) -> None:
        logger.info(
            "account.closed",
            user_id=user_id[:8],
        )

    def account_updated(self, user_id: str, changes: str) -> None:
        logger.info(
            "account.updated",
            user_id=user_id[:8],
            changes=changes,
        )

    def smtp_updated(self, actor_id: str, fields: list[str]) -> None:
        logger.info(
            "admin.smtp_updated",
            actor_id=actor_id[:8],
            fields=",".join(fields),
        )

    # ---------- Çeviri olayları ----------

    def translation_completed(
        self, user_id: str, table_id: str, char_count: int
    ) -> None:
        logger.info(
            "translation.completed",
            user_id=user_id[:8],
            table_id=table_id,
            char_count=char_count,
        )

    def profile_created(self, user_id: str) -> None:
        logger.info(
            "profile.created",
            user_id=user_id[:8],
        )

    def profile_deleted(self, user_id: str) -> None:
        logger.info(
            "profile.deleted",
            user_id=user_id[:8],
        )


# ---------- PII masking ----------

def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"


def _mask_ip(ip: str | None) -> str:
    if not ip:
        return "unknown"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    # IPv6
    return ip[:7] + "***"


def _safe_filename(filename: str) -> str:
    """Dosya adını log için güvenli hale getir."""
    if len(filename) > 50:
        return filename[:20] + "..." + filename[-20:]
    return filename


# Singleton
audit_log = AuditLog()