# Session service — server-side session management
#
# Plan v9 referansı: Bölüm 1.8.1 (Tarayıcı Oturumu), 1.15.1 (Session Modeli)

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from ..models.session import Session
from ..models.user import User

SESSION_IDLE_TIMEOUT = timedelta(hours=8)
SESSION_COOKIE = "nova_session"


class SessionService:
    """Sunucu tarafı oturum yönetimi — HttpOnly cookie ile."""

    async def create(
        self,
        db: DbSession,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[Session, str]:
        """Yeni oturum oluşturur. (Session, raw_token) çiftini döndürür."""
        raw_token = Session.generate_token()
        token_hash = self._hash_token(raw_token)
        expires = datetime.now(UTC) + SESSION_IDLE_TIMEOUT

        ua_hash = None
        if user_agent:
            ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:32]

        session = Session(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires,
            ip_address=ip_address,
            user_agent_hash=ua_hash,
        )
        db.add(session)
        await db.flush()

        return session, raw_token

    async def verify(
        self, db: DbSession, raw_token: str
    ) -> tuple[Session, User] | tuple[None, None]:
        """Ham token'ı doğrular. Geçerliyse (session, user) döndürür."""
        token_hash = self._hash_token(raw_token)
        result = await db.execute(
            select(Session).where(Session.token_hash == token_hash)
        )
        session = result.scalar_one_or_none()

        if session is None:
            return None, None
        if session.is_expired:
            return None, None
        if session.is_revoked:
            return None, None

        user = session.user
        if user is None or user.status != "active":
            return None, None

        return session, user

    async def refresh(self, db: DbSession, session: Session) -> None:
        """Oturum süresini yeniler (idle timeout sıfırla)."""
        session.last_seen_at = datetime.now(UTC)
        session.expires_at = datetime.now(UTC) + SESSION_IDLE_TIMEOUT
        await db.flush()

    async def revoke(self, db: DbSession, session: Session) -> None:
        """Tek bir oturumu iptal eder."""
        session.revoked_at = datetime.now(UTC)
        await db.flush()

    async def revoke_all_user_sessions(self, db: DbSession, user_id: str) -> None:
        """Kullanıcının tüm oturumlarını toplu iptal eder."""
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await db.execute(stmt)
        await db.flush()

    async def cleanup_expired(self, db: DbSession) -> int:
        """Süresi dolmuş oturumları iptal eder."""
        stmt = (
            update(Session)
            .where(Session.expires_at < datetime.now(UTC), Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount or 0

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


session_service = SessionService()