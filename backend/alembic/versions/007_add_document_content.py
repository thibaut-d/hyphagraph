"""Add document content fields to source_revisions

Revision ID: 007
Revises: 006
Create Date: 2026-01-05

Adds support for storing uploaded document content in source_revisions table.
This enables re-extraction capability and keeps document text with source metadata.

New fields:
- document_text: Full extracted text content (TEXT)
- document_format: File format (VARCHAR) - pdf, txt, etc.
- document_file_name: Original filename (VARCHAR)
- document_extracted_at: Timestamp of text extraction (TIMESTAMP WITH TIME ZONE)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_document_content'
down_revision = '006_entity_slug_unique'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add document content fields to source_revisions table.

    All fields are nullable to maintain compatibility with existing sources
    that don't have uploaded documents.
    """
    # Add document text field
    op.add_column(
        'source_revisions',
        sa.Column('document_text', sa.Text(), nullable=True)
    )

    # Add document format field (pdf, txt, etc.)
    op.add_column(
        'source_revisions',
        sa.Column('document_format', sa.String(), nullable=True)
    )

    # Add original filename field
    op.add_column(
        'source_revisions',
        sa.Column('document_file_name', sa.String(), nullable=True)
    )

    # Add extraction timestamp field
    op.add_column(
        'source_revisions',
        sa.Column('document_extracted_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove document content fields from source_revisions table."""
    op.drop_column('source_revisions', 'document_extracted_at')
    op.drop_column('source_revisions', 'document_file_name')
    op.drop_column('source_revisions', 'document_format')
    op.drop_column('source_revisions', 'document_text')
