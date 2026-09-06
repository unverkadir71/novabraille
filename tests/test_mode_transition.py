# Mode transition tests — F7.13
#
# APP_MODE değişiminde UI/API davranış doğrulaması.
# Self-hosted: login-only entry + admin bootstrap + SMTP yönetimi + hesap düzenleme.

from __future__ import annotations

import os
import secrets

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src import config
from backend.src.database import get_db
from backend.src.main import app
from backend.src.models import Base


@pytest_asyncio.fixture
async def self_hosted_client():
    """Self-hosted modda, in-memory SQLite + tablo oluşturulmuş client."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with sf() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override

    old_mode = config.settings.app_mode
    config.settings.app_mode = "self_hosted"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, sf

    config.settings.app_mode = old_mode
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hosted_client():
    """Hosted modda, in-memory SQLite + tablo oluşturulmuş client."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with sf() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override

    old_mode = config.settings.app_mode
    config.settings.app_mode = "hosted"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, sf

    config.settings.app_mode = old_mode
    app.dependency_overrides.clear()


class TestSelfHostedMode:
    """Self-hosted modda davranış testleri."""

    @pytest.mark.asyncio
    async def test_root_redirects_to_login(self, self_hosted_client):
        """Self-hosted modda / → login sayfasına yönlendirilir."""
        client, sf = self_hosted_client  # noqa: F841
        res = await client.get("/", follow_redirects=False)
        assert res.status_code in (302, 303, 307, 308), res.text
        location = res.headers.get("location", "")
        assert "login" in location.lower(), f"Expected login in location, got: {location}"

    @pytest.mark.asyncio
    async def test_admin_can_access_smtp(self, self_hosted_client):
        """Self-hosted admin SMTP endpoint'ine erişebilir."""
        client, sf = self_hosted_client

        from backend.src.services.auth import auth_service
        from backend.src.services.user import user_service

        email = f"admin-{secrets.token_hex(4)}@test.local"
        async with sf() as db:
            user = await user_service.create(
                db,
                email=email,
                password_hash=auth_service.hash_password("AdminPass123"),
            )
            user.role = "admin"
            await user_service.activate(db, user)
            await db.commit()

        # Login
        res = await client.post(
            "/api/v1/auth/login",
            data={"email": email, "password": "AdminPass123"},
        )
        assert res.status_code == 200, res.text

        for cookie in client.cookies.jar:
            if cookie.name == "nova_csrf":
                client.headers["X-CSRF-Token"] = cookie.value
                break

        # SMTP endpoint erişilebilir
        res2 = await client.get("/api/v1/admin/smtp")
        assert res2.status_code == 200, res2.text
        data = res2.json()
        assert "enabled" in data
        assert "host" in data

    @pytest.mark.asyncio
    async def test_account_update_works(self, self_hosted_client):
        """Self-hosted kullanıcı hesap düzenleme yapabilir."""
        client, sf = self_hosted_client

        from backend.src.services.auth import auth_service
        from backend.src.services.user import user_service

        email = f"user-{secrets.token_hex(4)}@test.local"
        async with sf() as db:
            user = await user_service.create(
                db,
                email=email,
                password_hash=auth_service.hash_password("TestPass123"),
            )
            await user_service.activate(db, user)
            await db.commit()

        res = await client.post(
            "/api/v1/auth/login",
            data={"email": email, "password": "TestPass123"},
        )
        assert res.status_code == 200

        for cookie in client.cookies.jar:
            if cookie.name == "nova_csrf":
                client.headers["X-CSRF-Token"] = cookie.value
                break

        res2 = await client.patch(
            "/api/v1/account",
            json={"display_name": "Updated", "current_password": "TestPass123"},
        )
        assert res2.status_code == 200, res2.text


class TestHostedMode:
    """Hosted modda davranış testleri."""

    @pytest.mark.asyncio
    async def test_root_redirects_to_public(self, hosted_client):
        """Hosted modda / → public site'ye yönlendirilir."""
        client, sf = hosted_client  # noqa: F841
        res = await client.get("/", follow_redirects=False)
        assert res.status_code in (302, 303, 307, 308)
        location = res.headers.get("location", "").lower()
        assert "public" in location

    @pytest.mark.asyncio
    async def test_plans_api_available(self, hosted_client):
        """Hosted modda /api/v1/plans herkese açık."""
        client, sf = hosted_client  # noqa: F841
        res = await client.get("/api/v1/plans")
        assert res.status_code == 200


class TestModeSwitchGraceful:
    """Mod geçişinde hata olmadan çalışma."""

    @pytest.mark.asyncio
    async def test_development_mode_health(self):
        """Development modda health endpoint çalışır."""
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def _override():
            async with sf() as session:
                try:
                    yield session
                finally:
                    await session.close()

        app.dependency_overrides[get_db] = _override

        old_mode = config.settings.app_mode
        config.settings.app_mode = "development"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/health")
            assert res.status_code == 200
            assert res.json() == {"status": "ok"}

        config.settings.app_mode = old_mode
        app.dependency_overrides.clear()