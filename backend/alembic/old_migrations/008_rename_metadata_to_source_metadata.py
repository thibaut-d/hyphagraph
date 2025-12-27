"""Rename metadata to source_metadata in source_revisions

Revision ID: 008_rename_metadata
Revises: 007_add_password_reset
Create Date: 2024-12-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '008_rename_metadata'
down_revision = '007_add_password_reset'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename metadata column to source_metadata in source_revisions table
    op.alter_column('source_revisions', 'metadata', new_column_name='source_metadata')


def downgrade() -> None:
    # Rename source_metadata back to metadata
    op.alter_column('source_revisions', 'source_metadata', new_column_name='metadata')
