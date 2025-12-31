"""add_entity_terms_created_at

Revision ID: 004
Revises: 003
Create Date: 2025-12-31

Adds created_at column to entity_terms table to match EntityTerm model's TimestampMixin.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_add_entity_terms_created_at'
down_revision: Union[str, None] = '003_fix_audit_logs_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_at column with a default value for existing rows
    op.add_column(
        'entity_terms',
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now()
        )
    )


def downgrade() -> None:
    # Remove created_at column
    op.drop_column('entity_terms', 'created_at')
