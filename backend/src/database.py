# SQLAlchemy async engine and session factory
#
# Provides async database connectivity via SQLAlchemy 2.0+ async API.
# Uses the database URL from config.py.
# Plan v9 referansı: Bölüm 1.13 (Teknik Mimari)

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.log_level == "debug",
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()