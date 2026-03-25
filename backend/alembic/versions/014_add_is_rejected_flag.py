"""Add is_rejected flag to entities and relations tables

When a human reviewer rejects a staged extraction, the materialized entity
or relation is soft-deleted by setting is_rejected=True.  Rejected records
are excluded from listings, search, and export but remain accessible by
direct ID for audit purposes.

Revision ID: 014_add_is_rejected_flag
Revises: 013_add_llm_review_status
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "014_add_is_rejected_flag"
down_revision = "013_add_llm_review_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entities",
        sa.Column(
            "is_rejected",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="True when the staged extraction that created this entity was rejected by a human reviewer",
        ),
    )
    op.add_column(
        "relations",
        sa.Column(
            "is_rejected",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="True when the staged extraction that created this relation was rejected by a human reviewer",
        ),
    )


def downgrade() -> None:
    op.drop_column("entities", "is_rejected")
    op.drop_column("relations", "is_rejected")
