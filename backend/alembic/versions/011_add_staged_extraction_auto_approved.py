"""Add auto_approved column to staged_extractions

Records whether a staged extraction was approved by the automated pipeline
(no human reviewer). Allows operators to filter auto-approved items separately
from human-approved ones in the review UI.

Revision ID: 011_add_staged_extraction_auto_approved
Revises: 010_add_revision_confirmation_fields
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


revision = "011_add_staged_extraction_auto_approved"
down_revision = "010_add_revision_confirmation_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "staged_extractions",
        sa.Column(
            "auto_approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True when status was set to APPROVED by the automated pipeline (no human reviewer)",
        ),
    )


def downgrade() -> None:
    op.drop_column("staged_extractions", "auto_approved")
