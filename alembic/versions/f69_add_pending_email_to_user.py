"""add pending_email to users

Revision ID: f69_add_pending_email
Revises: 57505cae72c6
Create Date: 2026-09-06 16:00:00+03:00

ADR-021 — Hosted modda e-posta değişikliği onayı için pending_email alanı.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f69_add_pending_email"
down_revision: Union[str, None] = "57505cae72c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("pending_email", sa.String(254), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("pending_email")
