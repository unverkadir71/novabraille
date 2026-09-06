# TranslationProfile + Account API tests
#
# Plan v10: Faz 5.1-5.2, 5.5, 5.6 — Profil CRUD, export, hesap kapatma

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.database import get_db
from backend.src.main import app
from backend.src.models import Base
from backend.src.services.auth import auth_service
from backend.src.services.profile import ProfileLimitError, profile_service
from backend.src.services.user import user_service

PW = "testpass123"


async def _login(ac: AsyncClient) -> tuple[str, str]:
    """Login yapar ve (session_token, csrf_token) döndürür."""
    resp = await ac.post(
        "/api/v1/auth/login",
        data={"email": "test@test.com", "password": PW},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    session = ac.cookies.get("nova_session")
    csrf = ac.cookies.get("nova_csrf")
    assert session, "Session cookie not found"
    assert csrf, "CSRF cookie not found"
    return session, csrf


def _auth_headers(session: str, csrf: str) -> dict:
    """CSRF header — httpx otomatik olarak cookie'leri gönderir."""
    return {"X-CSRF-Token": csrf}


@pytest_asyncio.fixture
async def authed():
    """Auth'lı client ve cookie token'ları sağlar."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        u = await user_service.create(
            db,
            email="test@test.com",
            password_hash=auth_service.hash_password(PW),
        )
        await user_service.activate(db, u)
        await db.commit()

    async def override():
        async with sf() as s:
            try:
                yield s
            finally:
                await s.close()

    app.dependency_overrides[get_db] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        session, csrf = await _login(ac)
        yield ac, session, csrf
    app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# CRUD testleri
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_profiles_empty(authed):
    """Yeni kullanıcının profili yok — boş liste."""
    ac, session, csrf = authed
    resp = await ac.get("/api/v1/profiles")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_profile(authed):
    """Profil oluşturma."""
    ac, session, csrf = authed
    resp = await ac.post(
        "/api/v1/profiles",
        json={
            "name": "Türkçe Ders Notları",
            "locale": "tr",
            "table_id": "tr-g2.ctb",
            "mode": "display",
            "grade": "grade2",
            "contraction_categories": ["single_letter", "two_letter"],
            "is_default": True,
        },
        headers=_auth_headers(session, csrf),
    )
    assert resp.status_code == 201, f"Create failed: {resp.text}"
    data = resp.json()
    assert data["name"] == "Türkçe Ders Notları"
    assert data["is_default"] is True
    assert data["id"]


@pytest.mark.asyncio
async def test_create_profile_validation(authed):
    """Geçersiz mod ile profil oluşturulamaz."""
    ac, session, csrf = authed
    resp = await ac.post(
        "/api/v1/profiles",
        json={"name": "T", "locale": "tr", "table_id": "tr-g2.ctb", "mode": "invalid_mode"},
        headers=_auth_headers(session, csrf),
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_list_profiles(authed):
    """Profiller listelenir."""
    ac, session, csrf = authed
    hdrs = _auth_headers(session, csrf)
    await ac.post(
        "/api/v1/profiles",
        json={"name": "P1", "locale": "tr", "table_id": "tr-g2.ctb", "mode": "display"},
        headers=hdrs,
    )
    await ac.post(
        "/api/v1/profiles",
        json={"name": "P2", "locale": "en", "table_id": "en-ueb-g2.ctb", "mode": "embosser", "layout": "a4"},
        headers=hdrs,
    )
    resp = await ac.get("/api/v1/profiles")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_profile(authed):
    """Tek profil detayı."""
    ac, session, csrf = authed
    hdrs = _auth_headers(session, csrf)
    create = await ac.post(
        "/api/v1/profiles",
        json={"name": "Tek Profil", "locale": "de", "table_id": "de-g2.ctb", "mode": "notetaker"},
        headers=hdrs,
    )
    profile_id = create.json()["id"]

    resp = await ac.get(f"/api/v1/profiles/{profile_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Tek Profil"


@pytest.mark.asyncio
async def test_get_nonexistent_profile(authed):
    """Var olmayan profil 404."""
    ac, session, csrf = authed
    resp = await ac.get("/api/v1/profiles/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_profile(authed):
    """Profil güncelleme."""
    ac, session, csrf = authed
    hdrs = _auth_headers(session, csrf)
    create = await ac.post(
        "/api/v1/profiles",
        json={"name": "Eski", "locale": "tr", "table_id": "tr-g2.ctb", "mode": "display"},
        headers=hdrs,
    )
    profile_id = create.json()["id"]

    resp = await ac.put(
        f"/api/v1/profiles/{profile_id}",
        json={"name": "Yeni", "mode": "embosser", "layout": "a4"},
        headers=hdrs,
    )
    assert resp.status_code == 200, f"Update failed: {resp.text}"
    data = resp.json()
    assert data["name"] == "Yeni"
    assert data["mode"] == "embosser"
    assert data["layout"] == "a4"


@pytest.mark.asyncio
async def test_delete_profile(authed):
    """Profil silme."""
    ac, session, csrf = authed
    hdrs = _auth_headers(session, csrf)
    await ac.post(
        "/api/v1/profiles",
        json={"name": "Kalacak", "locale": "tr", "table_id": "tr-g2.ctb", "mode": "display"},
        headers=hdrs,
    )
    create = await ac.post(
        "/api/v1/profiles",
        json={"name": "Silinecek", "locale": "en", "table_id": "en-ueb-g2.ctb", "mode": "display"},
        headers=hdrs,
    )
    profile_id = create.json()["id"]

    resp = await ac.delete(f"/api/v1/profiles/{profile_id}", headers=hdrs)
    assert resp.status_code == 200, f"Delete failed: {resp.text}"
    assert resp.json()["message"] == "Profil silindi."

    get_resp = await ac.get(f"/api/v1/profiles/{profile_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_delete_last_profile(authed):
    """Son profil silinemez."""
    ac, session, csrf = authed
    hdrs = _auth_headers(session, csrf)
    await ac.post(
        "/api/v1/profiles",
        json={"name": "Tek", "locale": "tr", "table_id": "tr-g2.ctb", "mode": "display"},
        headers=hdrs,
    )
    profiles = await ac.get("/api/v1/profiles")
    profile_id = profiles.json()[0]["id"]

    resp = await ac.delete(f"/api/v1/profiles/{profile_id}", headers=hdrs)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "LAST_PROFILE"


@pytest.mark.asyncio
async def test_is_default_exclusive(authed):
    """Yeni varsayılan profil seçildiğinde eski varsayılan kalkar."""
    ac, session, csrf = authed
    hdrs = _auth_headers(session, csrf)
    p1 = await ac.post(
        "/api/v1/profiles",
        json={"name": "VD1", "locale": "tr", "table_id": "tr-g2.ctb", "mode": "display", "is_default": True},
        headers=hdrs,
    )
    p2 = await ac.post(
        "/api/v1/profiles",
        json={"name": "VD2", "locale": "en", "table_id": "en-ueb-g2.ctb", "mode": "display", "is_default": True},
        headers=hdrs,
    )

    resp = await ac.get(f"/api/v1/profiles/{p1.json()['id']}")
    assert resp.json()["is_default"] is False

    resp = await ac.get(f"/api/v1/profiles/{p2.json()['id']}")
    assert resp.json()["is_default"] is True


# ---------------------------------------------------------------------------
# Account export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_export(authed):
    """Veri dışa aktarma testi."""
    ac, session, csrf = authed
    hdrs = _auth_headers(session, csrf)
    await ac.post(
        "/api/v1/profiles",
        json={"name": "Export Profil", "locale": "tr", "table_id": "tr-g2.ctb", "mode": "display"},
        headers=hdrs,
    )

    resp = await ac.get("/api/v1/account/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["account"]["email"] == "test@test.com"
    assert len(data["profiles"]) >= 1
    assert data["usage_stats"]["total_entries"] == 0


@pytest.mark.asyncio
async def test_account_export_requires_auth():
    """Export endpoint'i auth gerektirir."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override():
        async with sf() as s:
            try:
                yield s
            finally:
                await s.close()

    app.dependency_overrides[get_db] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/account/export")
        assert resp.status_code == 401
    app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Account close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_account_wrong_password(authed):
    """Yanlış parola ile hesap kapatılamaz."""
    ac, session, csrf = authed
    resp = await ac.post(
        "/api/v1/account/close",
        json={"password": "wrong", "confirmation": "HESABIMI KAPAT"},
        headers=_auth_headers(session, csrf),
    )
    assert resp.status_code == 403, f"Got {resp.status_code}: {resp.text}"
    assert resp.json()["detail"]["code"] == "WRONG_PASSWORD"


@pytest.mark.asyncio
async def test_close_account_wrong_confirmation(authed):
    """Yanlış onay metni ile hesap kapatılamaz."""
    ac, session, csrf = authed
    resp = await ac.post(
        "/api/v1/account/close",
        json={"password": PW, "confirmation": "yanlis"},
        headers=_auth_headers(session, csrf),
    )
    assert resp.status_code == 422, f"Got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_close_account_success(authed):
    """Doğru parola ve onay ile hesap kapatılır."""
    ac, session, csrf = authed
    resp = await ac.post(
        "/api/v1/account/close",
        json={"password": PW, "confirmation": "HESABIMI KAPAT"},
        headers=_auth_headers(session, csrf),
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    assert "kapatıldı" in resp.json()["message"]


@pytest.mark.asyncio
async def test_close_account_already_closed(authed):
    """Zaten kapalı hesap ile oturum artık geçersiz olur."""
    ac, session, csrf = authed
    hdrs = _auth_headers(session, csrf)
    # Hesabı kapat
    resp = await ac.post(
        "/api/v1/account/close",
        json={"password": PW, "confirmation": "HESABIMI KAPAT"},
        headers=hdrs,
    )
    assert resp.status_code == 200
    # Kapatılan hesabın oturumu verify'da reddedilir
    resp2 = await ac.post(
        "/api/v1/account/close",
        json={"password": PW, "confirmation": "HESABIMI KAPAT"},
        headers=hdrs,
    )
    assert resp2.status_code == 401


# ---------------------------------------------------------------------------
# Profile limit tests (unit level)
# ---------------------------------------------------------------------------


class TestProfileLimits:
    """Profil limiti testleri."""

    @pytest.mark.asyncio
    async def test_check_limit_within_bounds(self):
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with sf() as db:
            u = await user_service.create(db, email="lim@t.com", password_hash=auth_service.hash_password(PW))
            await user_service.activate(db, u)
            await db.commit()
            await profile_service.check_limit(db, u, 2)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_check_limit_exceeded(self):
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with sf() as db:
            u = await user_service.create(db, email="lim2@t.com", password_hash=auth_service.hash_password(PW))
            await user_service.activate(db, u)
            await db.commit()
            await profile_service.create(db, u, "P1", "tr", "tr-g2.ctb", "display")
            await profile_service.create(db, u, "P2", "en", "en-ueb-g2.ctb", "display")
            with pytest.raises(ProfileLimitError) as exc:
                await profile_service.check_limit(db, u, 2)
            assert exc.value.current == 2
            assert exc.value.maximum == 2
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_check_limit_unlimited(self):
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with sf() as db:
            u = await user_service.create(db, email="unlim@t.com", password_hash=auth_service.hash_password(PW))
            await user_service.activate(db, u)
            await db.commit()
            for i in range(10):
                await profile_service.create(db, u, f"P{i}", "tr", "tr-g2.ctb", "display")
            await profile_service.check_limit(db, u, -1)
        await engine.dispose()


# ---------------------------------------------------------------------------
# CSRF koruması
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profile_create_requires_csrf(authed):
    """Profil oluşturma CSRF gerektirir."""
    ac, session, csrf = authed
    resp = await ac.post(
        "/api/v1/profiles",
        json={"name": "T", "locale": "tr", "table_id": "tr-g2.ctb", "mode": "display"},
        headers={"Cookie": f"nova_session={session}", "X-CSRF-Token": ""},
    )
    assert resp.status_code == 403