# Security headers middleware — HTTP güvenlik başlıkları
#
# OWASP 2026 ve Mozilla Observatory önerilerine uygun güvenlik başlıkları.
# Tüm HTML ve JSON yanıtlarına eklenir.
#
# Self-hosted notu: HSTS yalnızca HTTPS üzerinden erişiliyorsa eklenir.
#   Self-hosted kullanıcıları genellikle reverse proxy (nginx/Caddy) arkasında
#   çalıştırır; bu middleware defense-in-depth katmanıdır.

from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Tüm yanıtlara OWASP önerilen güvenlik başlıklarını ekler.

    Eklenen başlıklar:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: microphone=(), camera=(), geolocation=()
    - Cross-Origin-Opener-Policy: same-origin
    - Strict-Transport-Security: yalnızca HTTPS isteklerde
    - Content-Security-Policy: yalnızca HTML yanıtlarda
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        headers = response.headers

        # Her zaman eklenen başlıklar
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault(
            "Permissions-Policy",
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()",
        )
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        # HSTS — yalnızca HTTPS isteklerde
        if request.url.scheme == "https":
            headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        # CSP — yalnızca HTML yanıtlarda
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            headers.setdefault(
                "Content-Security-Policy",
                (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data:; "
                    "connect-src 'self'; "
                    "font-src 'self'; "
                    "object-src 'none'; "
                    "frame-ancestors 'none'; "
                    "base-uri 'self'; "
                    "form-action 'self'"
                ),
            )

        return response

    @classmethod
    def create(cls) -> SecurityHeadersMiddleware:
        """Fabrika — FastAPI app.add_middleware() için uygun."""
        return cls(app=None)  # type: ignore[arg-type]
