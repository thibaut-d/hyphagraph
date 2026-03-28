"""Add is_merged flag to entities table

Revision ID: 009_add_entity_merge_flag
Revises: 008_fix_rel_type_json_cols
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


revision = "009_add_entity_merge_flag"
down_revision = "008_fix_rel_type_json_cols"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entities",
        sa.Column("is_merged", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("entities", "is_merged")
