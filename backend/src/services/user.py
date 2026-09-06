# User service — account creation, lookup, and management
#
# Plan v9 referansı: Bölüm 1.7.1 (Müşteri Akışı), 1.15.1 (User Modeli)

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User


class UserService:
    """Kullanıcı hesabı yönetimi servisi."""

    @staticmethod
    def normalize_email(email: str) -> str:
        """E-posta adresini normalize eder: küçük harf, boşluk temizleme."""
        return email.strip().lower()

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """E-posta ile kullanıcı arar (normalize edilmiş)."""
        normalized = self.normalize_email(email)
        result = await db.execute(
            select(User).where(User.email_normalized == normalized)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: str) -> User | None:
        """ID ile kullanıcı arar."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        email: str,
        password_hash: str,
        display_name: str | None = None,
    ) -> User:
        """Yeni kullanıcı oluşturur. Email benzersizliği çağrı öncesinde kontrol edilmeli."""
        normalized = self.normalize_email(email)
        user = User(
            email=email,
            email_normalized=normalized,
            password_hash=password_hash,
            display_name=display_name,
        )
        db.add(user)
        await db.flush()
        return user

    async def activate(self, db: AsyncSession, user: User) -> None:
        """Kullanıcı hesabını etkinleştirir."""
        user.status = "active"
        user.email_verified_at = datetime.now(UTC)
        await db.flush()

    async def update_last_login(self, db: AsyncSession, user: User) -> None:
        """Son giriş zamanını günceller."""
        user.last_login_at = datetime.now(UTC)
        await db.flush()


# Singleton
user_service = UserService()