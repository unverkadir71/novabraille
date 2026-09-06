# Token service — one-time action tokens (account activation, password reset)
#
# Plan v9 referansı: Bölüm 1.8.3 (Hesap Etkinleştirme ve Parola Sıfırlama Token'ları)

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.action_token import ActionToken


class TokenService:
    """Eylem token'ları — tek kullanımlık, kısa ömürlü."""

    TOKEN_BYTES = 64  # 86 chars URL-safe
    ACTIVATION_TTL = timedelta(hours=24)
    RESET_TTL = timedelta(hours=1)

    @staticmethod
    def _hash(token: str) -> str:
        """Ham token'ı SHA-256 ile hash'ler."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def create_token(
        self,
        db: AsyncSession,
        user_id: str,
        purpose: str,
        ttl: timedelta | None = None,
    ) -> str:
        """Yeni eylem token'ı oluşturur. Ham token'ı döndürür (e-postaya konur)."""
        if ttl is None:
            ttl = (
                self.ACTIVATION_TTL
                if purpose == "activate_account"
                else self.RESET_TTL
            )

        raw_token = token_urlsafe(self.TOKEN_BYTES)
        token_hash = self._hash(raw_token)

        action_token = ActionToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + ttl,
        )
        db.add(action_token)
        await db.flush()

        return raw_token

    async def verify_token(
        self,
        db: AsyncSession,
        raw_token: str,
        purpose: str,
    ) -> ActionToken | None:
        """Ham token'ı hash'leyip veritabanında arar. Geçerliyse döndürür."""
        token_hash = self._hash(raw_token)

        result = await db.execute(
            select(ActionToken).where(
                ActionToken.token_hash == token_hash,
                ActionToken.purpose == purpose,
            )
        )
        action_token = result.scalar_one_or_none()

        if action_token is None:
            return None
        if action_token.is_expired:
            return None
        if action_token.is_used:
            return None

        return action_token

    async def consume_token(
        self,
        db: AsyncSession,
        action_token: ActionToken,
    ) -> None:
        """Token'ı kullanıldı olarak işaretler."""
        action_token.used_at = datetime.now(UTC)
        await db.flush()

    async def invalidate_user_tokens(
        self,
        db: AsyncSession,
        user_id: str,
        purpose: str | None = None,
    ) -> None:
        """Kullanıcının tüm kullanılmamış token'larını geçersiz kılar.

        purpose verilirse yalnızca o amaçtaki token'lar etkilenir.
        Başarılı aktivasyon sonrası tüm eski aktivasyon token'ları,
        başarılı parola sıfırlama sonrası tüm eski sıfırlama token'ları silinir.
        """
        stmt = update(ActionToken).where(
            ActionToken.user_id == user_id,
            ActionToken.used_at.is_(None),
        )
        if purpose is not None:
            stmt = stmt.where(ActionToken.purpose == purpose)

        stmt = stmt.values(used_at=datetime.now(UTC))
        await db.execute(stmt)
        await db.flush()


# Singleton
token_service = TokenService()