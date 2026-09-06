# Security headers middleware tests — güvenlik başlıkları doğrulaması
#
# OWASP 2026 önerilen başlıkların tüm yanıtlarda bulunduğunu doğrular.

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.main import app


@pytest.mark.asyncio
async def test_security_headers_on_html():
    """HTML sayfalarında tüm güvenlik başlıkları mevcut olmalı."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        # Doğrudan HTML dönen bir sayfa iste
        resp = await client.get("/public/index.html")

    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in resp.headers.get("permissions-policy", "")
    assert resp.headers.get("cross-origin-opener-policy") == "same-origin"
    # CSP yalnızca HTML yanıtlarda
    assert "default-src" in resp.headers.get("content-security-policy", "")


@pytest.mark.asyncio
async def test_security_headers_on_json():
    """JSON API yanıtlarında CSP olmamalı, diğer başlıklar olmalı."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        resp = await client.get("/health")

    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert resp.headers.get("cross-origin-opener-policy") == "same-origin"
    # CSP JSON yanıtlarda olmamalı
    assert resp.headers.get("content-security-policy") is None


@pytest.mark.asyncio
async def test_hsts_not_on_http():
    """HTTP isteklerde HSTS başlığı olmamalı."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        resp = await client.get("/")

    assert resp.headers.get("strict-transport-security") is None


@pytest.mark.asyncio
async def test_csp_has_frame_ancestors():
    """CSP'de frame-ancestors 'none' olmalı (clickjacking koruması)."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        resp = await client.get("/public/index.html")

    csp = resp.headers.get("content-security-policy", "")
    assert "frame-ancestors 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "form-action 'self'" in csp
    assert "object-src 'none'" in csp
