"""add smtp_config table

Revision ID: f70c_add_smtp_config
Revises: f69_add_pending_email
Create Date: 2026-09-06 16:20:00+03:00

ADR-023 — Admin panelinden SMTP ayarları yönetimi.
Tek satırlı model (id=1), şifre Fernet ile şifrelenir.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f70c_add_smtp_config"
down_revision: Union[str, None] = "f69_add_pending_email"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "smtp_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("host", sa.String(255), server_default="localhost", nullable=False),
        sa.Column("port", sa.Integer(), server_default="587", nullable=False),
        sa.Column("username", sa.String(255), server_default="", nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        sa.Column("from_name", sa.String(100), server_default="Nova Braille", nullable=False),
        sa.Column("from_email", sa.String(254), server_default="noreply@novabraille.example.com", nullable=False),
        sa.Column("use_tls", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("smtp_config")
