# Entitlement service — plan/özellik erişim kontrolü
#
# Plan v10 referansı: ADR-013 — Son kullanıcı plan yapısı
#
# Hosted modda kullanıcının planına göre özellik erişimini ve limitleri kontrol eder.
# Self-hosted modda tüm özellikler sınırsızdır (kontrol uygulanmaz).

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.plan import Entitlement, Plan
from ..models.user import User

# Feature code sabitleri (Plan v10 Bölüm 1 — Plan Matrisi)
FEATURE_MAX_CHARS = "max_chars"
FEATURE_MAX_PROFILES = "max_profiles"
FEATURE_FILE_UPLOAD = "file_upload"
FEATURE_BRF_DOWNLOAD = "brf_download"
FEATURE_HISTORY = "history"
FEATURE_API_ACCESS = "api_access"
FEATURE_PRIORITY_SUPPORT = "priority_support"

# Varsayılan planlar (kod ile tohumlanır; admin panelinden düzenlenebilir)
DEFAULT_PLANS: list[dict] = [
    {
        "plan_code": "starter",
        "name_tr": "Başlangıç",
        "name_en": "Starter",
        "description_tr": "Bireysel, ara sıra kullanan kullanıcılar için.",
        "description_en": "For individuals who translate occasionally.",
        "price_monthly": 0,  # Fiyatlar maliyet analizi sonrası belirlenecek
        "price_annual": 0,
        "sort_order": 1,
        "entitlements": {
            FEATURE_MAX_CHARS: 50_000,
            FEATURE_MAX_PROFILES: 2,
            FEATURE_FILE_UPLOAD: 0,
            FEATURE_BRF_DOWNLOAD: 0,
            FEATURE_HISTORY: 0,
            FEATURE_API_ACCESS: 0,
            FEATURE_PRIORITY_SUPPORT: 0,
        },
    },
    {
        "plan_code": "professional",
        "name_tr": "Profesyonel",
        "name_en": "Professional",
        "description_tr": "Günlük düzenli kullanıcılar için. Tüm temel özellikler.",
        "description_en": "For daily users. All core features.",
        "price_monthly": 0,
        "price_annual": 0,
        "sort_order": 2,
        "entitlements": {
            FEATURE_MAX_CHARS: 250_000,
            FEATURE_MAX_PROFILES: 5,
            FEATURE_FILE_UPLOAD: 1,
            FEATURE_BRF_DOWNLOAD: 1,
            FEATURE_HISTORY: 1,
            FEATURE_API_ACCESS: 0,
            FEATURE_PRIORITY_SUPPORT: 0,
        },
    },
    {
        "plan_code": "enterprise",
        "name_tr": "Kurumsal",
        "name_en": "Enterprise",
        "description_tr": "Kurumlar, okullar ve rehabilitasyon merkezleri için.",
        "description_en": "For institutions, schools, and rehabilitation centers.",
        "price_monthly": 0,
        "price_annual": 0,
        "sort_order": 3,
        "entitlements": {
            FEATURE_MAX_CHARS: -1,  # sınırsız
            FEATURE_MAX_PROFILES: -1,
            FEATURE_FILE_UPLOAD: 1,
            FEATURE_BRF_DOWNLOAD: 1,
            FEATURE_HISTORY: 1,
            FEATURE_API_ACCESS: 1,
            FEATURE_PRIORITY_SUPPORT: 1,
        },
    },
]

# Sınırsız değerini temsil eden sabit
UNLIMITED = -1


class EntitlementService:
    """Plan ve özellik erişim kontrolü."""

    async def get_plan(self, db: AsyncSession, plan_code: str) -> Plan | None:
        """Plan tanımını getirir."""
        result = await db.execute(select(Plan).where(Plan.plan_code == plan_code))
        return result.scalar_one_or_none()

    async def get_entitlements(
        self, db: AsyncSession, plan_code: str
    ) -> dict[str, int]:
        """Bir planın tüm özellik-limit eşleştirmesini döndürür."""
        result = await db.execute(
            select(Entitlement).where(Entitlement.plan_code == plan_code)
        )
        return {e.feature_code: e.limit_value for e in result.scalars()}

    async def get_feature_limit(
        self, db: AsyncSession, plan_code: str, feature_code: str
    ) -> int:
        """Belirli bir özelliğin limitini döndürür (varsayılan: 0 = kapalı)."""
        result = await db.execute(
            select(Entitlement).where(
                Entitlement.plan_code == plan_code,
                Entitlement.feature_code == feature_code,
            )
        )
        entitlement = result.scalar_one_or_none()
        return entitlement.limit_value if entitlement else 0

    async def has_feature(
        self, db: AsyncSession, user: User, feature_code: str
    ) -> bool:
        """Kullanıcının belirli bir özelliğe erişimi var mı?

        Self-hosted modda her zaman True döner (tüm özellikler sınırsız).
        Hosted modda kullanıcının planına bakar.
        """
        if settings.is_self_hosted:
            return True

        plan_code = user.plan_code if hasattr(user, "plan_code") else None
        if not plan_code:
            return False

        limit = await self.get_feature_limit(db, plan_code, feature_code)
        return limit > 0 or limit == UNLIMITED

    async def get_char_limit(self, db: AsyncSession, user: User) -> int:
        """Kullanıcının aylık karakter kotasını döndürür.

        Self-hosted veya sınırsız plan: -1 (sınırsız).
        """
        if settings.is_self_hosted:
            return UNLIMITED

        plan_code = user.plan_code if hasattr(user, "plan_code") else None
        if not plan_code:
            return 0

        return await self.get_feature_limit(db, plan_code, FEATURE_MAX_CHARS)

    async def get_profile_limit(self, db: AsyncSession, user: User) -> int:
        """Kullanıcının maksimum çeviri profili sayısını döndürür.

        Self-hosted modda her zaman sınırsız.
        Development modda, plan_code yoksa sınırsız (test/geliştirme kolaylığı).
        """
        if settings.is_self_hosted:
            return UNLIMITED

        plan_code = user.plan_code if hasattr(user, "plan_code") else None
        if not plan_code:
            # Development modda plansız kullanıcı sınırsız
            if settings.is_development:
                return UNLIMITED
            return 0

        return await self.get_feature_limit(db, plan_code, FEATURE_MAX_PROFILES)

    async def seed_default_plans(self, db: AsyncSession) -> int:
        """Varsayılan 3 planı ve entitlement'larını oluşturur.

        Yalnızca mevcut değilse ekler (idempotent).
        Returns: oluşturulan plan sayısı.
        """
        created = 0
        for plan_data in DEFAULT_PLANS:
            existing = await self.get_plan(db, plan_data["plan_code"])
            if existing is None:
                plan = Plan(
                    plan_code=plan_data["plan_code"],
                    name_tr=plan_data["name_tr"],
                    name_en=plan_data["name_en"],
                    description_tr=plan_data["description_tr"],
                    description_en=plan_data["description_en"],
                    price_monthly=plan_data["price_monthly"],
                    price_annual=plan_data["price_annual"],
                    sort_order=plan_data["sort_order"],
                    is_active=True,
                )
                db.add(plan)
                await db.flush()
                created += 1

                for feature_code, limit_value in plan_data["entitlements"].items():
                    db.add(
                        Entitlement(
                            plan_code=plan_data["plan_code"],
                            feature_code=feature_code,
                            limit_value=limit_value,
                        )
                    )
        await db.flush()
        return created


# Singleton
entitlement_service = EntitlementService()
