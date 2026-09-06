# Integration tests — file upload HTTP API
#
# Plan v9 referansı: Faz 2.3.3 — Dosya Yükleme Endpoint'i

from __future__ import annotations

from pathlib import Path

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
FIXTURES_DIR = Path(__file__).parent.parent / "test_file_processing" / "fixtures"


@pytest_asyncio.fixture
async def client():
    """Test istemcisi — in-memory SQLite + önceden oluşturulmuş kullanıcı."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sf() as db:
        user = await user_service.create(
            db,
            email="a@b.com",
            password_hash=auth_service.hash_password(TEST_PASS),
        )
        await user_service.activate(db, user)
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


@pytest_asyncio.fixture
async def auth_cookies(client: AsyncClient) -> dict[str, str]:
    """Giriş yapmış kullanıcının cookie'lerini döndürür."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"email": "a@b.com", "password": TEST_PASS},
    )
    assert resp.status_code == 200
    return dict(resp.cookies)


# ── Format listesi testleri (herkese açık) ──────────────────────────────


@pytest.mark.asyncio
async def test_list_formats_ok(client: AsyncClient) -> None:
    """GET /api/v1/files/formats — desteklenen formatları listeler."""
    resp = await client.get("/api/v1/files/formats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 9
    formats = {f["format"] for f in data}
    # 4 core formats should always be present
    assert {"txt", "docx", "rtf", "pdf"}.issubset(formats)


@pytest.mark.asyncio
async def test_list_formats_has_labels(client: AsyncClient) -> None:
    """Her formatın TR ve EN etiketleri olmalı."""
    resp = await client.get("/api/v1/files/formats")
    data = resp.json()
    for f in data:
        assert f["label_tr"]
        assert f["label_en"]
        assert f["extensions"]


# ── TXT upload testleri ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_txt_success(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """POST /api/v1/files/upload — TXT dosya yükleme."""
    files = {"file": ("test.txt", b"Merhaba dunya! T\xc3\xbcrk\xc3\xa7e test.", "text/plain")}
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["input_format"] == "txt"
    assert "Merhaba" in data["text"]
    assert "Türkçe" in data["text"]
    assert data["char_count"] > 0
    assert data["original_filename"] == "test.txt"


# ── DOCX upload testleri ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_docx_success(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """POST /api/v1/files/upload — DOCX dosya yükleme."""
    docx_path = FIXTURES_DIR / "test.docx"
    docx_bytes = docx_path.read_bytes()

    files = {
        "file": (
            "belge.docx",
            docx_bytes,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["input_format"] == "docx"
    assert len(data["text"]) > 20
    assert data["original_filename"] == "belge.docx"


# ── RTF upload testleri ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_rtf_success(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """POST /api/v1/files/upload — RTF dosya yükleme."""
    rtf_path = FIXTURES_DIR / "test.rtf"
    rtf_bytes = rtf_path.read_bytes()

    files = {"file": ("belge.rtf", rtf_bytes, "application/rtf")}
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["input_format"] == "rtf"
    assert len(data["text"]) > 20


# ── PDF upload testleri ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_pdf_success(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """POST /api/v1/files/upload — PDF dosya yükleme."""
    pdf_path = FIXTURES_DIR / "test.pdf"
    pdf_bytes = pdf_path.read_bytes()

    files = {"file": ("belge.pdf", pdf_bytes, "application/pdf")}
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["input_format"] == "pdf"
    assert "Test PDF" in data["text"]
    assert "12345" in data["text"]


# ── Format tespiti testleri ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_format_from_content_type(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """Content-Type header'dan format tespiti."""
    # TXT içeriği ama RTF content-type ile
    files = {"file": ("test.rtf", b"Hello World", "text/plain")}
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    assert resp.json()["input_format"] == "txt"  # content-type öncelikli


@pytest.mark.asyncio
async def test_upload_format_from_extension(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """Content-Type bilinmeyen → uzantıdan format tespiti."""
    # PDF dosyasını content-type olmadan gönder (uzantıdan tespit edilsin)
    pdf_bytes = (FIXTURES_DIR / "test.pdf").read_bytes()
    files = {"file": ("data.pdf", pdf_bytes)}
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    # PDF uzantısından format tespiti
    assert resp.json()["input_format"] == "pdf"


@pytest.mark.asyncio
async def test_upload_docx_from_extension(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """DOCX uzantısından format tespiti."""
    docx_bytes = (FIXTURES_DIR / "test.docx").read_bytes()
    files = {"file": ("belge.docx", docx_bytes)}
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    assert resp.json()["input_format"] == "docx"


# ── Hata durumu testleri ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_no_auth(client: AsyncClient) -> None:
    """Kimlik doğrulamasız yükleme 401 döndürmeli."""
    files = {"file": ("test.txt", b"data", "text/plain")}
    resp = await client.post("/api/v1/files/upload", files=files)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_unsupported_format(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """Desteklenmeyen format 422 döndürmeli."""
    files = {"file": ("image.png", b"PNGDATA", "image/png")}
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "UNSUPPORTED_FORMAT"


@pytest.mark.asyncio
async def test_upload_no_filename(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """Dosya adı olmayan yükleme 422 döndürmeli."""
    # FastAPI, boş dosya adında Pydantic validasyon hatası döner
    files = {"file": ("", b"data", "text/plain")}
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    # Boş dosya adı: FastAPI Pydantic seviyesinde list formatında hata dönebilir
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_empty_content(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """Boş TXT dosyası 422 döndürmeli."""
    files = {"file": ("empty.txt", b"   \n  ", "text/plain")}
    resp = await client.post(
        "/api/v1/files/upload",
        files=files,
        cookies=auth_cookies,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "EMPTY_CONTENT"


# ── Birleşik translate endpoint testleri ──────────────────────────────────


@pytest.mark.asyncio
async def test_upload_and_translate_txt(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """POST /api/v1/files/translate — TXT dosyasını yükle ve çevir."""
    files = {"file": ("test.txt", b"Merhaba dunya", "text/plain")}
    params = {"table_id": "tr-g2.tbl"}
    resp = await client.post(
        "/api/v1/files/translate",
        files=files,
        params=params,
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["table_id"] == "tr-g2.tbl"
    assert data["direction"] == "text_to_braille"
    assert len(data["braille"]) > 0


@pytest.mark.asyncio
async def test_upload_and_translate_docx(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """POST /api/v1/files/translate — DOCX dosyasını yükle ve çevir."""
    docx_bytes = (FIXTURES_DIR / "test.docx").read_bytes()
    files = {
        "file": (
            "belge.docx",
            docx_bytes,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    params = {"table_id": "tr-g2.tbl"}
    resp = await client.post(
        "/api/v1/files/translate",
        files=files,
        params=params,
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["direction"] == "text_to_braille"
    assert data["char_count"] > 0


@pytest.mark.asyncio
async def test_upload_and_translate_no_auth(
    client: AsyncClient,
) -> None:
    """Birleşik translate kimlik doğrulamasız 401."""
    files = {"file": ("test.txt", b"data", "text/plain")}
    params = {"table_id": "tr-g2.tbl"}
    resp = await client.post(
        "/api/v1/files/translate",
        files=files,
        params=params,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_and_translate_invalid_table(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """Geçersiz table_id ile translate 422."""
    files = {"file": ("test.txt", b"Merhaba", "text/plain")}
    params = {"table_id": "invalid-table.xyz"}
    resp = await client.post(
        "/api/v1/files/translate",
        files=files,
        params=params,
        cookies=auth_cookies,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_and_translate_empty_file(
    client: AsyncClient, auth_cookies: dict[str, str]
) -> None:
    """Boş dosya ile translate 422."""
    files = {"file": ("empty.txt", b"   ", "text/plain")}
    params = {"table_id": "tr-g2.tbl"}
    resp = await client.post(
        "/api/v1/files/translate",
        files=files,
        params=params,
        cookies=auth_cookies,
    )
    assert resp.status_code == 422