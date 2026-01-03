"""Add unique constraint for entity slugs on current revisions

Revision ID: 006
Revises: 005
Create Date: 2026-01-03

Adds a unique constraint to ensure entity slugs are unique among current revisions.
This prevents duplicate entities while preserving revision history.

Constraint: UNIQUE (slug) WHERE is_current = TRUE
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_entity_slug_unique_constraint'
down_revision = '005_seed_ui_categories'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add unique partial index on entity_revisions.slug where is_current = TRUE.

    Uses a partial index instead of a constraint for PostgreSQL compatibility.
    This ensures only one current revision can have a given slug.
    """
    # PostgreSQL partial unique index
    op.create_index(
        'ix_entity_revisions_slug_current_unique',
        'entity_revisions',
        ['slug'],
        unique=True,
        postgresql_where=sa.text('is_current = true')
    )


def downgrade() -> None:
    """Remove the unique constraint on entity slugs."""
    op.drop_index(
        'ix_entity_revisions_slug_current_unique',
        table_name='entity_revisions'
    )
