# Integration tests — login/logout HTTP API
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

TEST_PASS = "Tst1234!"


@pytest_asyncio.fixture
async def client():
    """Fixture with proper dependency override for in-memory SQLite."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create an active user in the same database the app will use
    async with sf() as db:
        user = await user_service.create(
            db, email="a@b.com",
            password_hash=auth_service.hash_password("Tst1234!"),
        )
        await user_service.activate(db, user)
        await db.commit()

    # Override app's get_db to use the test engine
    async def override_get_db():
        async with sf() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_login_success(client):
    resp = await client.post("/api/v1/auth/login", data={"email": "a@b.com", "password": TEST_PASS})
    assert resp.status_code == 200
    assert "nova_session" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_pass(client):
    resp = await client.post("/api/v1/auth/login", data={"email": "a@b.com", "password": "NoWay99!"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_ghost(client):
    resp = await client.post("/api/v1/auth/login", data={"email": "x@x.com", "password": "NoWay99!"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_ok(client):
    resp = await client.post("/api/v1/auth/login", data={"email": "a@b.com", "password": TEST_PASS})
    cookies = dict(resp.cookies)
    resp = await client.get("/api/v1/auth/me", cookies=cookies)
    assert resp.status_code == 200
    assert resp.json()["email"] == "a@b.com"


@pytest.mark.asyncio
async def test_me_noauth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_flow(client):
    resp = await client.post("/api/v1/auth/login", data={"email": "a@b.com", "password": TEST_PASS})
    cookies = dict(resp.cookies)
    csrf = cookies.get("nova_csrf", "")
    resp = await client.post(
        "/api/v1/auth/logout",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    resp = await client.get("/api/v1/auth/me", cookies=cookies)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_nosession(client):
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 403  # CSRF required