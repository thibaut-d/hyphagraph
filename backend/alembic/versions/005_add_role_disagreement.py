"""Add disagreement column to relation_role_revisions for per-role contradiction measure

Revision ID: 005_add_role_disagreement
Revises: 004_add_entity_merge_records
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa


revision = "005_add_role_disagreement"
down_revision = "004_add_entity_merge_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "relation_role_revisions",
        sa.Column("disagreement", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("relation_role_revisions", "disagreement")
