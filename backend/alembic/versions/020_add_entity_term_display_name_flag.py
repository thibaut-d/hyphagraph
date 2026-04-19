"""Add display-name flag to entity terms

Revision ID: 020_entity_term_display_flag
Revises: 019_add_trgm_indexes
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa


revision = "020_entity_term_display_flag"
down_revision = "019_add_trgm_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entity_terms",
        sa.Column(
            "is_display_name",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_entity_terms_display_name_per_entity_language",
        "entity_terms",
        ["entity_id", "language"],
        unique=True,
        postgresql_where=sa.text("is_display_name = true AND language IS NOT NULL"),
        sqlite_where=sa.text("is_display_name = 1 AND language IS NOT NULL"),
    )
    op.create_index(
        "ix_entity_terms_display_name_per_entity_international",
        "entity_terms",
        ["entity_id"],
        unique=True,
        postgresql_where=sa.text("is_display_name = true AND language IS NULL"),
        sqlite_where=sa.text("is_display_name = 1 AND language IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_entity_terms_display_name_per_entity_international",
        table_name="entity_terms",
    )
    op.drop_index(
        "ix_entity_terms_display_name_per_entity_language",
        table_name="entity_terms",
    )
    op.drop_column("entity_terms", "is_display_name")
