"""Add llm_review_status column to revision tables

Tracks the LLM provenance review pipeline outcome independently of the
revision visibility status ('draft'/'confirmed').

Values (NULL for human-authored rows):
  'pending_review' — LLM-created, awaiting human confirmation
  'auto_verified'  — LLM-created, passed automated quality check
  'confirmed'      — LLM-created, explicitly confirmed by a human

Revision ID: 013_add_llm_review_status
Revises: 012_add_user_token_version
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "013_add_llm_review_status"
down_revision = "012_add_user_token_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entity_revisions",
        sa.Column(
            "llm_review_status",
            sa.String(),
            nullable=True,
            comment="LLM provenance review outcome: pending_review, auto_verified, confirmed, or NULL for human-authored",
        ),
    )
    op.add_column(
        "relation_revisions",
        sa.Column(
            "llm_review_status",
            sa.String(),
            nullable=True,
            comment="LLM provenance review outcome: pending_review, auto_verified, confirmed, or NULL for human-authored",
        ),
    )
    op.add_column(
        "source_revisions",
        sa.Column(
            "llm_review_status",
            sa.String(),
            nullable=True,
            comment="LLM provenance review outcome: pending_review, auto_verified, confirmed, or NULL for human-authored",
        ),
    )


def downgrade() -> None:
    op.drop_column("entity_revisions", "llm_review_status")
    op.drop_column("relation_revisions", "llm_review_status")
    op.drop_column("source_revisions", "llm_review_status")
