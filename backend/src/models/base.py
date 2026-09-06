# SQLAlchemy ORM declarative base
#
# All models inherit from this single base for Alembic autogenerate support.

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass