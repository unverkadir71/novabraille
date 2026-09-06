# Integration tests for the translation API endpoints (F2.1.4)
#
# Tests GET /api/v1/tables, /api/v1/tables/languages, /api/v1/tables/{id}
# Plan v9 referansı: Faz 2.1.4

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Parametresiz async client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestListTables:
    """GET /api/v1/tables"""

    async def test_returns_200_with_data(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0

    async def test_each_item_has_required_fields(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?priority_only=true")
        data = r.json()
        required = {"id", "language", "grade", "type", "supports_back_translation"}
        for item in data:
            assert required.issubset(set(item.keys()))

    async def test_filter_by_language_tr(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?language=tr")
        data = r.json()
        assert len(data) >= 2
        for item in data:
            assert item["language"] == "tr"

    async def test_filter_by_grade_g2(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?grade=grade2")
        data = r.json()
        assert len(data) > 0
        for item in data:
            assert item["grade"] == "grade2"

    async def test_filter_by_grade_g1(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?grade=grade1")
        data = r.json()
        assert len(data) > 0
        for item in data:
            assert item["grade"] == "grade1"

    async def test_filter_by_type_literary(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?type=literary")
        data = r.json()
        assert len(data) > 0
        for item in data:
            assert item["type"] == "literary"

    async def test_filter_by_type_computer(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?type=computer")
        data = r.json()
        assert len(data) > 0
        for item in data:
            assert item["type"] == "computer"

    async def test_priority_only(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?priority_only=true")
        data = r.json()
        priority_langs = {"tr", "en", "de", "fr", "es", "ar", "ru", "pt"}
        for item in data:
            assert item["language"] in priority_langs, (
                f"{item['id']} language={item['language']}"
            )

    async def test_combined_filters(self, client: AsyncClient) -> None:
        r = await client.get(
            "/api/v1/tables?language=tr&grade=grade2&priority_only=true"
        )
        data = r.json()
        for item in data:
            assert item["language"] == "tr"
            assert item["grade"] == "grade2"

    async def test_human_names_present_for_priority(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?priority_only=true")
        data = r.json()
        named = sum(1 for item in data if item.get("name_tr") or item.get("name_en"))
        assert named > 0  # En az bir tablo ismi olmalı

    async def test_invalid_grade_rejected(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?grade=invalid")
        assert r.status_code == 422

    async def test_invalid_type_rejected(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables?type=invalid")
        assert r.status_code == 422


class TestListLanguages:
    """GET /api/v1/tables/languages"""

    async def test_returns_all_languages(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables/languages")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 8

    async def test_priority_only(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables/languages?priority_only=true")
        data = r.json()
        assert len(data) == 8
        codes = {item["code"] for item in data}
        assert codes == {"tr", "en", "de", "fr", "es", "ar", "ru", "pt"}

    async def test_each_item_format(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables/languages")
        data = r.json()
        for item in data:
            assert "code" in item
            assert "name" in item
            assert len(item["code"]) >= 2


class TestGetTable:
    """GET /api/v1/tables/{table_id}"""

    async def test_existing_table(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables/tr-g2.tbl")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "tr-g2.tbl"
        assert data["language"] == "tr"
        assert data["grade"] == "grade2"
        assert data["supports_back_translation"] is True

    async def test_human_name(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables/tr-g2.tbl")
        data = r.json()
        assert "Türkçe" in data["name_tr"]
        assert "Turkish" in data["name_en"]

    async def test_nonexistent_table_404(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/tables/nonexistent.xxx")
        assert r.status_code == 404
        data = r.json()
        assert data["detail"]["code"] == "TABLE_NOT_FOUND"

    async def test_path_traversal_404(self, client: AsyncClient) -> None:
        # FastAPI/Starlette path normalizasyonu path traversal'ı catch eder
        r = await client.get("/api/v1/tables/../../../etc/passwd")
        assert r.status_code == 404

    async def test_all_priority_tables_accessible(self, client: AsyncClient) -> None:
        """Öncelikli dillerin tüm tablolarına erişilebilmeli."""
        r = await client.get("/api/v1/tables?priority_only=true")
        data = r.json()
        for item in data:
            dr = await client.get(f"/api/v1/tables/{item['id']}")
            assert dr.status_code == 200, f"Failed for {item['id']}"
            assert dr.json()["id"] == item["id"]