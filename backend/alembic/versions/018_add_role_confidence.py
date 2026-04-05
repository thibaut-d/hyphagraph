"""add confidence to relation_role_revisions

Revision ID: 018_add_role_confidence
Revises: 017_add_calculated_trust_level
Create Date: 2026-04-05

Adds a typed confidence column to relation_role_revisions so that the
per-role confidence value is persisted alongside weight/coverage/disagreement
rather than recomputed on every read.
"""
from alembic import op
import sqlalchemy as sa

revision = "018_add_role_confidence"
down_revision = "017_add_calculated_trust_level"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "relation_role_revisions",
        sa.Column("confidence", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("relation_role_revisions", "confidence")
