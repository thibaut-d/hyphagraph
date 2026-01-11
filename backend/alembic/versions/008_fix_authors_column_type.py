"""Fix authors column type from VARCHAR[] to JSON

Revision ID: 008
Revises: 007
Create Date: 2026-01-09

The authors column in source_revisions was incorrectly defined as VARCHAR[]
(PostgreSQL array) instead of JSON/JSONB. This migration fixes the type to match
the SQLAlchemy model definition and ensures compatibility with the codebase.

The change:
- From: character varying[] (PostgreSQL array)
- To: jsonb (PostgreSQL JSONB for better performance)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '008_fix_authors_column_type'
down_revision = '007_add_document_content'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Convert authors column from VARCHAR[] to JSONB.

    Uses ALTER TYPE with USING clause to convert array data to JSON format.
    Example: ['Author 1', 'Author 2'] -> ["Author 1", "Author 2"]
    """
    # Convert VARCHAR[] to JSONB using array_to_json()
    op.execute("""
        ALTER TABLE source_revisions
        ALTER COLUMN authors TYPE jsonb
        USING CASE
            WHEN authors IS NULL THEN NULL
            ELSE array_to_json(authors)::jsonb
        END
    """)


def downgrade() -> None:
    """
    Convert authors column from JSONB back to VARCHAR[].

    Uses JSONB to array conversion. Note: This assumes the JSONB contains a valid
    JSON array of strings.
    """
    op.execute("""
        ALTER TABLE source_revisions
        ALTER COLUMN authors TYPE character varying[]
        USING CASE
            WHEN authors IS NULL THEN NULL
            ELSE ARRAY(SELECT jsonb_array_elements_text(authors))
        END
    """)
