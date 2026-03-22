"""Add status column to revision tables for LLM draft workflow

LLM-created revisions now land as status='draft' so humans can confirm them.
Manually-entered revisions default to 'confirmed'.

Revision ID: 006_add_revision_status
Revises: 005_add_role_disagreement
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa


revision = "006_add_revision_status"
down_revision = "005_add_role_disagreement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status to entity_revisions
    op.add_column(
        "entity_revisions",
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="confirmed",
        ),
    )

    # Add status to relation_revisions
    op.add_column(
        "relation_revisions",
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="confirmed",
        ),
    )

    # Add status to source_revisions
    op.add_column(
        "source_revisions",
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="confirmed",
        ),
    )


def downgrade() -> None:
    op.drop_column("entity_revisions", "status")
    op.drop_column("relation_revisions", "status")
    op.drop_column("source_revisions", "status")
