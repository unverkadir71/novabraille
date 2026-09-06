"""Tests for entitlement service and plan management.

Plan v10: ADR-013 — Son kullanıcı plan yapısı
"""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.models import Base, User
from backend.src.services.entitlement import (
    DEFAULT_PLANS,
    FEATURE_BRF_DOWNLOAD,
    FEATURE_FILE_UPLOAD,
    FEATURE_MAX_CHARS,
    UNLIMITED,
    entitlement_service,
)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as session:
        yield session
    await engine.dispose()


class TestSeedDefaultPlans:
    async def test_seed_creates_three_plans(self, db_session: AsyncSession) -> None:
        created = await entitlement_service.seed_default_plans(db_session)
        assert created == 3

    async def test_seed_is_idempotent(self, db_session: AsyncSession) -> None:
        await entitlement_service.seed_default_plans(db_session)
        # İkinci çağrı yeni plan oluşturmaz
        created_again = await entitlement_service.seed_default_plans(db_session)
        assert created_again == 0

    async def test_seed_creates_entitlements(self, db_session: AsyncSession) -> None:
        await entitlement_service.seed_default_plans(db_session)
        ents = await entitlement_service.get_entitlements(db_session, "professional")
        assert FEATURE_MAX_CHARS in ents
        assert ents[FEATURE_MAX_CHARS] == 250_000
        assert ents[FEATURE_FILE_UPLOAD] == 1

    async def test_default_plans_have_expected_codes(self) -> None:
        codes = [p["plan_code"] for p in DEFAULT_PLANS]
        assert codes == ["starter", "professional", "enterprise"]


class TestGetEntitlements:
    async def test_get_feature_limit(self, db_session: AsyncSession) -> None:
        await entitlement_service.seed_default_plans(db_session)
        limit = await entitlement_service.get_feature_limit(
            db_session, "starter", FEATURE_MAX_CHARS
        )
        assert limit == 50_000

    async def test_get_feature_limit_unknown_returns_zero(
        self, db_session: AsyncSession
    ) -> None:
        await entitlement_service.seed_default_plans(db_session)
        limit = await entitlement_service.get_feature_limit(
            db_session, "starter", "nonexistent_feature"
        )
        assert limit == 0

    async def test_enterprise_unlimited_chars(self, db_session: AsyncSession) -> None:
        await entitlement_service.seed_default_plans(db_session)
        limit = await entitlement_service.get_feature_limit(
            db_session, "enterprise", FEATURE_MAX_CHARS
        )
        assert limit == UNLIMITED


class TestHasFeature:
    async def test_professional_has_file_upload(self, db_session: AsyncSession) -> None:
        await entitlement_service.seed_default_plans(db_session)
        user = User(email="a@b.com", email_normalized="a@b.com", password_hash="x")
        user.plan_code = "professional"
        assert await entitlement_service.has_feature(
            db_session, user, FEATURE_FILE_UPLOAD
        ) is True

    async def test_starter_lacks_file_upload(self, db_session: AsyncSession) -> None:
        await entitlement_service.seed_default_plans(db_session)
        user = User(email="a@b.com", email_normalized="a@b.com", password_hash="x")
        user.plan_code = "starter"
        assert await entitlement_service.has_feature(
            db_session, user, FEATURE_FILE_UPLOAD
        ) is False

    async def test_no_plan_no_feature(self, db_session: AsyncSession) -> None:
        await entitlement_service.seed_default_plans(db_session)
        user = User(email="a@b.com", email_normalized="a@b.com", password_hash="x")
        user.plan_code = None
        assert await entitlement_service.has_feature(
            db_session, user, FEATURE_BRF_DOWNLOAD
        ) is False


class TestCharLimit:
    async def test_char_limit_starter(self, db_session: AsyncSession) -> None:
        await entitlement_service.seed_default_plans(db_session)
        user = User(email="a@b.com", email_normalized="a@b.com", password_hash="x")
        user.plan_code = "starter"
        assert await entitlement_service.get_char_limit(db_session, user) == 50_000

    async def test_char_limit_enterprise_unlimited(
        self, db_session: AsyncSession
    ) -> None:
        await entitlement_service.seed_default_plans(db_session)
        user = User(email="a@b.com", email_normalized="a@b.com", password_hash="x")
        user.plan_code = "enterprise"
        assert await entitlement_service.get_char_limit(db_session, user) == UNLIMITED

    async def test_profile_limit(self, db_session: AsyncSession) -> None:
        await entitlement_service.seed_default_plans(db_session)
        user = User(email="a@b.com", email_normalized="a@b.com", password_hash="x")
        user.plan_code = "professional"
        assert await entitlement_service.get_profile_limit(db_session, user) == 5
