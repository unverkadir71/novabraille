"""Integration tests — admin RBAC and plan management API.

Plan v10: ADR-010 (RBAC), ADR-011 (Admin paneli), ADR-013 (Plan yapısı)
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.database import get_db
from backend.src.main import app
from backend.src.models import Base
from backend.src.services.auth import auth_service
from backend.src.services.entitlement import entitlement_service
from backend.src.services.user import user_service

TEST_PASS = "Tst1234!"


async def _make_user(db: AsyncSession, email: str, role: str | None = None) -> None:
    user = await user_service.create(
        db,
        email=email,
        password_hash=auth_service.hash_password(TEST_PASS),
    )
    await user_service.activate(db, user)
    if role:
        user.role = role
    await db.commit()


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sf() as db:
        # Normal user
        await _make_user(db, "user@x.com", role="user")
        # Super admin
        await _make_user(db, "admin@x.com", role="super_admin")
        # Billing
        await _make_user(db, "billing@x.com", role="billing")
        # Varsayılan planları seed et (lifespan ASGITransport'ta çalışmaz)
        await entitlement_service.seed_default_plans(db)
        await db.commit()

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


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        data={"email": email, "password": TEST_PASS},
    )
    assert resp.status_code == 200
    return dict(resp.cookies)


# ── RBAC guard testleri ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_cannot_access_admin(client: AsyncClient) -> None:
    cookies = await _login(client, "user@x.com")
    resp = await client.get("/api/v1/admin/users", cookies=cookies)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_can_list_users(client: AsyncClient) -> None:
    cookies = await _login(client, "admin@x.com")
    resp = await client.get("/api/v1/admin/users", cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    # Role alanı dönmeli
    assert "role" in data[0]


@pytest.mark.asyncio
async def test_billing_cannot_list_users(client: AsyncClient) -> None:
    cookies = await _login(client, "billing@x.com")
    resp = await client.get("/api/v1/admin/users", cookies=cookies)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_without_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 401


# ── Rol yönetimi testleri ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_super_admin_can_view_permissions(client: AsyncClient) -> None:
    cookies = await _login(client, "admin@x.com")
    resp = await client.get("/api/v1/admin/roles/permissions", cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert "super_admin" in data
    assert "billing" in data


@pytest.mark.asyncio
async def test_super_admin_can_change_role(client: AsyncClient) -> None:
    cookies = await _login(client, "admin@x.com")
    # billing kullanıcısını admin yap
    resp = await client.get("/api/v1/admin/users", cookies=cookies)
    billing_user = next(u for u in resp.json() if u["email"] == "billing@x.com")

    resp = await client.put(
        f"/api/v1/admin/users/{billing_user['id']}/role",
        json={"role": "admin"},
        cookies=cookies,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_non_super_admin_cannot_change_role(client: AsyncClient) -> None:
    # Billing rolünde olan kullanıcı rol değiştiremez
    cookies = await _login(client, "billing@x.com")
    # admin kullanıcısını bul
    super_cookies = await _login(client, "admin@x.com")
    resp = await client.get("/api/v1/admin/users", cookies=super_cookies)
    target = next(u for u in resp.json() if u["email"] == "user@x.com")

    resp = await client.put(
        f"/api/v1/admin/users/{target['id']}/role",
        json={"role": "admin"},
        cookies=cookies,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_change_role_invalid_role(client: AsyncClient) -> None:
    cookies = await _login(client, "admin@x.com")
    resp = await client.get("/api/v1/admin/users", cookies=cookies)
    target = next(u for u in resp.json() if u["email"] == "user@x.com")

    resp = await client.put(
        f"/api/v1/admin/users/{target['id']}/role",
        json={"role": "nonexistent"},
        cookies=cookies,
    )
    assert resp.status_code == 422


# ── Plan yönetimi testleri (hosted only) ───────────────────────────────


@pytest.mark.asyncio
async def test_super_admin_can_list_plans(client: AsyncClient) -> None:
    cookies = await _login(client, "admin@x.com")
    resp = await client.get("/api/v1/admin/plans", cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    # Varsayılan 3 plan seed edilmiş olmalı (lifespan ile)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_admin_can_create_plan(client: AsyncClient) -> None:
    cookies = await _login(client, "admin@x.com")
    resp = await client.post(
        "/api/v1/admin/plans",
        json={
            "plan_code": "premium",
            "name_tr": "Premium",
            "name_en": "Premium",
            "price_monthly": 1000,
            "price_annual": 10000,
            "entitlements": {"max_chars": 500000, "file_upload": 1},
        },
        cookies=cookies,
    )
    assert resp.status_code == 201
    assert resp.json()["plan_code"] == "premium"
    assert resp.json()["entitlements"]["max_chars"] == 500000


@pytest.mark.asyncio
async def test_billing_cannot_create_plan(client: AsyncClient) -> None:
    cookies = await _login(client, "billing@x.com")
    resp = await client.post(
        "/api/v1/admin/plans",
        json={
            "plan_code": "premium2",
            "name_tr": "Premium",
            "name_en": "Premium",
            "price_monthly": 1000,
            "price_annual": 10000,
        },
        cookies=cookies,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_plan_conflict(client: AsyncClient) -> None:
    cookies = await _login(client, "admin@x.com")
    resp = await client.post(
        "/api/v1/admin/plans",
        json={
            "plan_code": "starter",  # zaten seed edilmiş
            "name_tr": "X",
            "name_en": "X",
            "price_monthly": 0,
            "price_annual": 0,
        },
        cookies=cookies,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_public_plans_listing(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
