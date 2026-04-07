"""Add term kind to entity terms

Revision ID: 022_add_entity_term_kind
Revises: 021_add_bug_report_status
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa


revision = "022_add_entity_term_kind"
down_revision = "021_add_bug_report_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entity_terms",
        sa.Column(
            "term_kind",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'alias'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("entity_terms", "term_kind")
