"""Add token_lookup_hash column to refresh_tokens for performance

Revision ID: 003_add_token_lookup_hash
Revises: 002_add_staged_extractions
Create Date: 2026-03-08

Adds token_lookup_hash column (SHA256) to refresh_tokens table to enable
O(1) token lookups instead of O(n) bcrypt verifications.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '003_add_token_lookup_hash'
down_revision = '002_add_staged_extractions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add token_lookup_hash column and index."""
    # Add the new column (nullable to allow existing rows)
    op.add_column('refresh_tokens',
        sa.Column('token_lookup_hash', sa.String(64), nullable=True)
    )

    # Revoke all existing tokens (we can't recreate lookup hashes from bcrypt hashes)
    op.execute(text("UPDATE refresh_tokens SET is_revoked = true WHERE token_lookup_hash IS NULL"))

    # Create unique index on token_lookup_hash for fast lookups
    # Note: SQLite will allow NULL values in unique index
    op.create_index(
        'ix_refresh_tokens_lookup_hash',
        'refresh_tokens',
        ['token_lookup_hash'],
        unique=True
    )

    # Drop unique constraint and index from token_hash
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        # SQLite doesn't have named unique constraints, so we skip dropping it
        # The index is what matters for SQLite
        try:
            batch_op.drop_index('ix_refresh_tokens_token_hash')
        except:
            pass  # May not exist in all environments


def downgrade() -> None:
    """Remove token_lookup_hash column and restore old constraints."""
    # Restore old constraints on token_hash
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])
    op.create_unique_constraint('refresh_tokens_token_hash_key', 'refresh_tokens', ['token_hash'])

    # Remove the lookup_hash index and column
    op.drop_index('ix_refresh_tokens_lookup_hash', 'refresh_tokens')
    op.drop_column('refresh_tokens', 'token_lookup_hash')
