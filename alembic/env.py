# Alembic async environment configuration
#
# Supports both offline (SQL script) and online (direct DB) migration modes.
# Database URL is read from backend.src.config.settings at runtime.
# All SQLAlchemy models in backend.src.models are auto-discovered.

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Alembic Config object
config = context.config

# Logger setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import settings and all models for autogenerate
from src.config import settings  # noqa: E402
from src.models import Base  # noqa: E402, F401

target_metadata = Base.metadata


def get_url() -> str:
    """Return the database URL from application config."""
    return settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generate SQL without connecting."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite ALTER support
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations inside a transaction."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # SQLite ALTER support
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connect and apply."""
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())