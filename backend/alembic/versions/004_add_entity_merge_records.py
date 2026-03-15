"""Add entity merge records for auditable entity merge provenance

Revision ID: 004_add_entity_merge_records
Revises: 003_add_token_lookup_hash
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004_add_entity_merge_records"
down_revision = "003_add_token_lookup_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_merge_records",
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merged_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_slug", sa.String(), nullable=False),
        sa.Column("target_slug", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["merged_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("entity_merge_records")
