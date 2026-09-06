# CSRF protection tests
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.database import get_db
from backend.src.main import app
from backend.src.models import Base
from backend.src.services.auth import auth_service
from backend.src.services.user import user_service

PW = "***"


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        u = await user_service.create(db, email="test@test.com", password_hash=auth_service.hash_password(PW))
        await user_service.activate(db, u)
        await db.commit()
    async def override():
        async with sf() as s:
            try: yield s
            finally: await s.close()
    app.dependency_overrides[get_db] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_csrf_missing_gets_403(client):
    """CSRF cookie olmadan logout POST'u 403 döndürür."""
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]["code"]


@pytest.mark.asyncio
async def test_csrf_wrong_token_gets_403(client):
    """Yanlış CSRF token ile 403."""
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": "wrong"},
        cookies={"nova_csrf": "correct"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_skips_csrf(client):
    """GET istekleri CSRF kontrolünü atlar."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401  # Auth yok → 401, CSRF değil


@pytest.mark.asyncio
async def test_login_sets_csrf_cookie(client):
    """Login başarılı olduğunda CSRF cookie'si set edilir."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"email": "test@test.com", "password": PW},
    )
    assert resp.status_code == 200
    assert "nova_csrf" in resp.cookies
    csrf = resp.cookies["nova_csrf"]
    assert len(csrf) == 43  # token_urlsafe(32) → 43 chars


@pytest.mark.asyncio
async def test_logout_with_valid_csrf(client):
    """Geçerli CSRF token ile logout başarılı."""
    # Login → CSRF cookie + session cookie al
    r1 = await client.post(
        "/api/v1/auth/login",
        data={"email": "test@test.com", "password": PW},
    )
    cookies = dict(r1.cookies)
    csrf_token = cookies.get("nova_csrf", "")

    # Logout → X-CSRF-Token header ile
    r2 = await client.post(
        "/api/v1/auth/logout",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert r2.status_code == 200