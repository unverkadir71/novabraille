"""add_legal_documents_table

Revision ID: d4e91c2f7a30
Revises: bcaa75c38a55
Create Date: 2026-08-29 19:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'd4e91c2f7a30'
down_revision: Union[str, None] = 'bcaa75c38a55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'legal_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('title_tr', sa.String(length=200), nullable=False),
        sa.Column('title_en', sa.String(length=200), nullable=False),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='draft', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('legal_documents', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_legal_documents_slug'), ['slug'], unique=True
        )


def downgrade() -> None:
    with op.batch_alter_table('legal_documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_legal_documents_slug'))

    op.drop_table('legal_documents')
