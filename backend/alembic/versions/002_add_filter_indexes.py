"""Add indexes for filter performance

Revision ID: 002_add_filter_indexes
Revises: 001_initial_clean
Create Date: 2025-01-01

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '002_add_filter_indexes'
down_revision = '001_initial_clean'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes on frequently filtered columns for better query performance."""

    # Indexes on entity_revisions for entity filtering
    op.create_index(
        'ix_entity_revisions_is_current_only',
        'entity_revisions',
        ['is_current'],
        unique=False
    )
    op.create_index(
        'ix_entity_revisions_ui_category_id',
        'entity_revisions',
        ['ui_category_id'],
        unique=False
    )
    op.create_index(
        'ix_entity_revisions_slug',
        'entity_revisions',
        ['slug'],
        unique=False
    )

    # Indexes on source_revisions for source filtering
    op.create_index(
        'ix_source_revisions_is_current_only',
        'source_revisions',
        ['is_current'],
        unique=False
    )
    op.create_index(
        'ix_source_revisions_kind',
        'source_revisions',
        ['kind'],
        unique=False
    )
    op.create_index(
        'ix_source_revisions_year',
        'source_revisions',
        ['year'],
        unique=False
    )
    op.create_index(
        'ix_source_revisions_trust_level',
        'source_revisions',
        ['trust_level'],
        unique=False
    )
    op.create_index(
        'ix_source_revisions_title',
        'source_revisions',
        ['title'],
        unique=False
    )

    # Composite indexes for common filter combinations
    op.create_index(
        'ix_entity_revisions_current_category',
        'entity_revisions',
        ['is_current', 'ui_category_id'],
        unique=False
    )
    op.create_index(
        'ix_source_revisions_current_kind',
        'source_revisions',
        ['is_current', 'kind'],
        unique=False
    )
    op.create_index(
        'ix_source_revisions_current_year',
        'source_revisions',
        ['is_current', 'year'],
        unique=False
    )


def downgrade() -> None:
    """Remove indexes."""

    # Drop composite indexes
    op.drop_index('ix_source_revisions_current_year', table_name='source_revisions')
    op.drop_index('ix_source_revisions_current_kind', table_name='source_revisions')
    op.drop_index('ix_entity_revisions_current_category', table_name='entity_revisions')

    # Drop source_revisions indexes
    op.drop_index('ix_source_revisions_title', table_name='source_revisions')
    op.drop_index('ix_source_revisions_trust_level', table_name='source_revisions')
    op.drop_index('ix_source_revisions_year', table_name='source_revisions')
    op.drop_index('ix_source_revisions_kind', table_name='source_revisions')
    op.drop_index('ix_source_revisions_is_current_only', table_name='source_revisions')

    # Drop entity_revisions indexes
    op.drop_index('ix_entity_revisions_slug', table_name='entity_revisions')
    op.drop_index('ix_entity_revisions_ui_category_id', table_name='entity_revisions')
    op.drop_index('ix_entity_revisions_is_current_only', table_name='entity_revisions')
