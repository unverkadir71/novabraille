# FastAPI application entry point
#
# Application factory pattern — creates and configures the FastAPI app instance
# with middleware, routers, and lifespan event handlers.
# Plan v9 referansı: Bölüm 1.13.1 (Backend), 1.16 (API Sınırları)

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.v1.router import router as v1_router
from .config import settings
from .database import async_session
from .services.entitlement import entitlement_service


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Hosted modda varsayılan planları seed et
        if not settings.is_self_hosted:
            async with async_session() as db:
                await entitlement_service.seed_default_plans(db)
                await db.commit()

        # Admin bootstrap: NOVA_ADMIN_EMAIL/PASSWORD tanımlıysa ve admin yoksa oluştur
        if settings.nova_admin_email and settings.nova_admin_password:
            async with async_session() as db:
                import structlog
                from sqlalchemy import func, select

                from .models.user import User
                from .services.auth import auth_service
                from .services.user import user_service

                logger = structlog.get_logger("nova_braille.bootstrap")

                try:
                    result = await db.execute(
                        select(func.count())
                        .select_from(User)
                        .where(User.role.in_(["super_admin", "admin"]))
                    )
                    admin_count = result.scalar()
                except Exception:
                    # Tablolar henüz oluşturulmamış (ilk başlatma)
                    logger.info(
                        "bootstrap.skipped",
                        reason="tables_not_ready",
                    )
                    admin_count = -1

                if admin_count == 0:
                    user = await user_service.create(
                        db,
                        email=settings.nova_admin_email,
                        password_hash=auth_service.hash_password(
                            settings.nova_admin_password
                        ),
                        display_name="Admin",
                    )
                    user.role = "super_admin" if settings.is_hosted else "admin"
                    await user_service.activate(db, user)
                    await db.commit()

                    logger.info(
                        "bootstrap.admin_created",
                        email=settings.nova_admin_email[:3] + "***",
                        role=user.role,
                    )

        yield

    app = FastAPI(
        title="Nova Braille",
        description="Braille çeviri web uygulaması — API",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # CORS — development only, production'da same-origin
    if settings.is_development:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Security headers — OWASP 2026 önerileri
    # CSP yalnızca HTML sayfalara eklenir; JSON API yanıtlarını etkilemez
    from .middleware import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)

    # Routers
    app.include_router(v1_router)

    # Static files — shared CSS/JS ve dashboard/public dizinleri
    app.mount("/shared", StaticFiles(directory="frontend/shared"), name="shared")
    app.mount("/dashboard", StaticFiles(directory="frontend/dashboard", html=True), name="dashboard")
    app.mount("/public", StaticFiles(directory="frontend/public", html=True), name="public")
    # Root redirect — mode'a göre public site veya login sayfası
    from starlette.responses import RedirectResponse

    @app.get("/", include_in_schema=False)
    async def root():
        if settings.is_self_hosted:
            return RedirectResponse(url="/dashboard/login.html")
        return RedirectResponse(url="/public/index.html")

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        """Minimum health endpoint — public."""
        return {"status": "ok"}

    return app


app = create_app()