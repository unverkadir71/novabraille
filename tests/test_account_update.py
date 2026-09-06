# Account update tests — F6.9.4 (ADR-021)
#
# Kapsam: display_name, email, password değişikliği;
# hatalı parola, zayıf parola, duplicate email, CSRF.

from __future__ import annotations

import secrets

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.database import get_db
from backend.src.main import app
from backend.src.models import Base
from backend.src.services.auth import auth_service
from backend.src.services.user import user_service

TEST_PASS = "Tst1234!"


def _unique_email() -> str:
    return f"test-{secrets.token_hex(4)}@example.com"


@pytest_asyncio.fixture
async def authenticated_client():
    """In-memory SQLite + aktif kullanıcı + login + CSRF token hazır."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    email = _unique_email()
    async with sf() as db:
        user = await user_service.create(
            db,
            email=email,
            password_hash=auth_service.hash_password(TEST_PASS),
            display_name="Test Kullanıcı",
        )
        await user_service.activate(db, user)
        await db.commit()

    async def _override():
        async with sf() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/auth/login",
            data={"email": email, "password": TEST_PASS},
        )
        assert res.status_code == 200, f"Login failed: {res.text}"

        for cookie in ac.cookies.jar:
            if cookie.name == "nova_csrf":
                ac.headers["X-CSRF-Token"] = cookie.value
                break

        # Store sf and email for use in test_duplicate_email
        ac._sf = sf
        ac._email = email
        yield ac

    app.dependency_overrides.clear()


class TestAccountUpdate:
    """PATCH /api/v1/account — hesap bilgileri güncelleme."""

    @pytest.mark.asyncio
    async def test_update_display_name(self, authenticated_client):
        """display_name başarıyla güncellenir."""
        res = await authenticated_client.patch(
            "/api/v1/account",
            json={"display_name": "Yeni Isim", "current_password": TEST_PASS},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert "display_name" in data["changes"]
        assert data["user"]["display_name"] == "Yeni Isim"

    @pytest.mark.asyncio
    async def test_update_password(self, authenticated_client):
        """Parola başarıyla güncellenir."""
        res = await authenticated_client.patch(
            "/api/v1/account",
            json={"new_password": "NewPass456", "current_password": TEST_PASS},
        )
        assert res.status_code == 200, res.text
        assert "password" in res.json()["changes"]

    @pytest.mark.asyncio
    async def test_update_email_development(self, authenticated_client):
        """Development modda e-posta doğrudan değiştirilir."""
        new_email = _unique_email()
        res = await authenticated_client.patch(
            "/api/v1/account",
            json={"email": new_email, "current_password": TEST_PASS},
        )
        assert res.status_code == 200, res.text
        assert "email" in res.json()["changes"]

    @pytest.mark.asyncio
    async def test_wrong_current_password(self, authenticated_client):
        """Hatalı mevcut parola 403 döndürür."""
        res = await authenticated_client.patch(
            "/api/v1/account",
            json={"display_name": "Deneme", "current_password": "WrongPass"},
        )
        assert res.status_code == 403, res.text
        assert res.json()["detail"]["code"] == "WRONG_PASSWORD"

    @pytest.mark.asyncio
    async def test_weak_new_password(self, authenticated_client):
        """Zayıf yeni parola 422 döndürür."""
        res = await authenticated_client.patch(
            "/api/v1/account",
            json={"new_password": "1234567", "current_password": TEST_PASS},
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_no_changes(self, authenticated_client):
        """Hiçbir değişiklik alanı gönderilmezse 422 döner."""
        res = await authenticated_client.patch(
            "/api/v1/account",
            json={"current_password": TEST_PASS},
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_display_name(self, authenticated_client):
        """Boş display_name 422 döndürür."""
        res = await authenticated_client.patch(
            "/api/v1/account",
            json={"display_name": "", "current_password": TEST_PASS},
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_email(self, authenticated_client):
        """Başka kullanıcının e-postası 409 döndürür."""
        sf = authenticated_client._sf
        email2 = _unique_email()
        async with sf() as db:
            u2 = await user_service.create(
                db, email=email2, password_hash=auth_service.hash_password("2nd45678"),
            )
            await user_service.activate(db, u2)
            await db.commit()

        res = await authenticated_client.patch(
            "/api/v1/account",
            json={"email": email2, "current_password": TEST_PASS},
        )
        assert res.status_code == 409, res.text
        assert res.json()["detail"]["code"] == "EMAIL_ALREADY_EXISTS"

    @pytest.mark.asyncio
    async def test_multiple_fields_update(self, authenticated_client):
        """Aynı anda display_name + email güncellemesi."""
        new_email = _unique_email()
        res = await authenticated_client.patch(
            "/api/v1/account",
            json={
                "display_name": "Multi Update",
                "email": new_email,
                "current_password": TEST_PASS,
            },
        )
        assert res.status_code == 200, res.text
        assert len(res.json()["changes"]) >= 2


class TestAccountUnauthorized:
    """Yetkisiz erişim testleri."""

    @pytest.mark.asyncio
    async def test_patch_without_csrf_header(self, authenticated_client):
        """CSRF header'ı olmadan PATCH 403 döndürür."""
        authenticated_client.headers.pop("X-CSRF-Token", None)
        res = await authenticated_client.patch(
            "/api/v1/account",
            json={"display_name": "No CSRF", "current_password": TEST_PASS},
        )
        assert res.status_code == 403
        assert res.json()["detail"]["code"] == "CSRF_MISSING"
