# TranslationProfile service — profil CRUD ve varsayılan profil mantığı
#
# Plan v10 referansı: Faz 5.1-5.2.

from __future__ import annotations

import json

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.translation_profile import TranslationProfile
from ..models.user import User


class ProfileLimitError(Exception):
    """Kullanıcının profil limiti dolduğunda fırlatılır."""

    def __init__(self, current: int, maximum: int):
        self.current = current
        self.maximum = maximum
        super().__init__(
            f"Profil limiti doldu: {current}/{maximum}"
        )


class ProfileService:
    """Çeviri profili yönetimi."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(
        self,
        db: AsyncSession,
        user: User,
        name: str,
        locale: str,
        table_id: str,
        mode: str,
        grade: str = "grade2",
        layout: str | None = None,
        contraction_categories: list[str] | None = None,
        page_settings: dict | None = None,
        output_format: str | None = None,
        is_default: bool = False,
    ) -> TranslationProfile:
        """Yeni profil oluşturur."""
        categories_json = (
            json.dumps(contraction_categories, ensure_ascii=False)
            if contraction_categories
            else None
        )
        page_settings_json = (
            json.dumps(page_settings, ensure_ascii=False)
            if page_settings
            else None
        )

        profile = TranslationProfile(
            user_id=user.id,
            name=name,
            locale=locale,
            table_id=table_id,
            mode=mode,
            layout=layout,
            grade=grade,
            contraction_categories=categories_json,
            page_settings=page_settings_json,
            output_format=output_format,
            is_default=is_default,
        )

        if is_default:
            await self._unset_other_defaults(db, user.id)

        db.add(profile)
        await db.flush()
        return profile

    async def get_by_id(
        self, db: AsyncSession, user_id: str, profile_id: str
    ) -> TranslationProfile | None:
        """ID'ye göre profil getirir (ownership kontrolü)."""
        result = await db.execute(
            select(TranslationProfile).where(
                TranslationProfile.id == profile_id,
                TranslationProfile.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, db: AsyncSession, user_id: str
    ) -> list[TranslationProfile]:
        """Kullanıcının tüm profillerini listeler."""
        result = await db.execute(
            select(TranslationProfile)
            .where(TranslationProfile.user_id == user_id)
            .order_by(TranslationProfile.is_default.desc(), TranslationProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(
        self,
        db: AsyncSession,
        profile: TranslationProfile,
        **kwargs,
    ) -> TranslationProfile:
        """Profili günceller."""
        for key, value in kwargs.items():
            if hasattr(profile, key):
                if key == "contraction_categories" and isinstance(value, list) or key == "page_settings" and isinstance(value, dict):
                    setattr(profile, key, json.dumps(value, ensure_ascii=False))
                else:
                    setattr(profile, key, value)

        if kwargs.get("is_default"):
            await self._unset_other_defaults(db, profile.user_id, exclude=profile.id)
            profile.is_default = True

        await db.flush()
        return profile

    async def delete(self, db: AsyncSession, profile: TranslationProfile) -> None:
        """Profili siler."""
        await db.delete(profile)
        await db.flush()

    async def get_default(
        self, db: AsyncSession, user_id: str
    ) -> TranslationProfile | None:
        """Kullanıcının varsayılan profilini döndürür."""
        result = await db.execute(
            select(TranslationProfile).where(
                TranslationProfile.user_id == user_id,
                TranslationProfile.is_default == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Limit kontrolü
    # ------------------------------------------------------------------

    async def get_count(self, db: AsyncSession, user_id: str) -> int:
        """Kullanıcının toplam profil sayısını döndürür."""
        result = await db.execute(
            select(func.count(TranslationProfile.id)).where(
                TranslationProfile.user_id == user_id
            )
        )
        return result.scalar() or 0

    async def check_limit(
        self, db: AsyncSession, user: User, max_profiles: int
    ) -> None:
        """Profil limitini kontrol eder; doluysa ProfileLimitError fırlatır."""
        if max_profiles == -1:  # sınırsız
            return
        count = await self.get_count(db, user.id)
        if count >= max_profiles:
            raise ProfileLimitError(count, max_profiles)

    # ------------------------------------------------------------------
    # Varsayılan profil
    # ------------------------------------------------------------------

    async def ensure_default_profile(
        self, db: AsyncSession, user: User
    ) -> TranslationProfile | None:
        """Kullanıcının varsayılan profili yoksa bir tane oluşturur.

        Yalnızca user rolündeki kullanıcılar için (admin'ler için gerekmez).
        Returns: varsayılan profil veya None (zaten varsa ya da admin kullanıcı).
        """
        from ..services.rbac import Role, normalize_role

        existing = await self.get_default(db, user.id)
        if existing:
            return None

        role = normalize_role(user.role)
        if role != Role.USER:
            return None

        profile = TranslationProfile(
            user_id=user.id,
            name="Varsayılan",
            locale="tr",
            table_id="tr-g2.ctb",
            mode="display",
            grade="grade2",
            is_default=True,
        )
        db.add(profile)
        await db.flush()
        return profile

    async def _unset_other_defaults(
        self, db: AsyncSession, user_id: str, exclude: str | None = None
    ) -> None:
        """Aynı kullanıcıya ait diğer profillerin is_default değerini False yapar."""
        stmt = (
            update(TranslationProfile)
            .where(
                TranslationProfile.user_id == user_id,
                TranslationProfile.is_default == True,  # noqa: E712
            )
        )
        if exclude:
            stmt = stmt.where(TranslationProfile.id != exclude)
        stmt = stmt.values(is_default=False)
        await db.execute(stmt)
        await db.flush()


# Singleton
profile_service = ProfileService()
