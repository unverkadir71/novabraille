"""Tests for output format API endpoints.

Plan v9: Faz 2.5 — Çıktı Formatları (ADR-008)
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
from backend.src.services.user import user_service

TEST_PASS = "Tst1234!"


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sf() as db:
        user = await user_service.create(
            db, email="a@b.com",
            password_hash=auth_service.hash_password(TEST_PASS),
        )
        await user_service.activate(db, user)
        await db.commit()

    async def override_get_db():
        async with sf() as session:
            try: yield session
            finally: await session.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_cookies(client: AsyncClient) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", data={"email": "a@b.com", "password": TEST_PASS})
    assert resp.status_code == 200
    return dict(resp.cookies)


@pytest.mark.asyncio
async def test_list_output_modes(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/output/modes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    modes = {m["id"] for m in data}
    assert modes == {"display", "embosser", "notetaker"}


@pytest.mark.asyncio
async def test_list_page_layouts(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/output/layouts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    layout_ids = {l["id"] for l in data}
    assert "a4" in layout_ids


@pytest.mark.asyncio
async def test_translate_display_mode(client: AsyncClient, auth_cookies: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/output/translate",
        json={"text": "Merhaba", "table_id": "tr.tbl", "mode": "display"},
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    assert resp.json()["direction"] == "text_to_braille"


@pytest.mark.asyncio
async def test_translate_embosser_mode(client: AsyncClient, auth_cookies: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/output/translate",
        json={"text": "Test", "table_id": "tr.tbl", "mode": "embosser"},
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["braille"]) > 0


@pytest.mark.asyncio
async def test_translate_notetaker_mode(client: AsyncClient, auth_cookies: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/output/translate",
        json={"text": "Test", "table_id": "tr.tbl", "mode": "notetaker"},
        cookies=auth_cookies,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_translate_invalid_mode(client: AsyncClient, auth_cookies: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/output/translate",
        json={"text": "Test", "table_id": "tr.tbl", "mode": "invalid_mode"},
        cookies=auth_cookies,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_download_brf(client: AsyncClient, auth_cookies: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/output/download",
        json={"text": "Merhaba", "table_id": "tr.tbl", "output_format": "brf"},
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["output_format"] == "brf"
    assert data["content_base64"]
    assert data["byte_size"] > 0


@pytest.mark.asyncio
async def test_download_brl(client: AsyncClient, auth_cookies: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/output/download",
        json={"text": "Hello", "table_id": "en-ueb-g1.ctb", "output_format": "brl"},
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["output_format"] == "brl"


@pytest.mark.asyncio
async def test_download_invalid_format(client: AsyncClient, auth_cookies: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/output/download",
        json={"text": "Test", "table_id": "tr.tbl", "output_format": "pdf"},
        cookies=auth_cookies,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_output_no_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/output/translate", json={"text": "Test", "table_id": "tr.tbl", "mode": "display"})
    assert resp.status_code == 401