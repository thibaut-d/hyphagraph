"""Add indexes on entity_merge_records FK columns for query performance

source_entity_id and target_entity_id are used in WHERE clauses when looking
up merge history for an entity but have no indexes, causing full-table scans.

Revision ID: 007_add_entity_merge_indexes
Revises: 006_add_revision_status
Create Date: 2026-03-22
"""

from alembic import op


revision = "007_add_entity_merge_indexes"
down_revision = "006_add_revision_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_entity_merge_records_source_entity_id",
        "entity_merge_records",
        ["source_entity_id"],
    )
    op.create_index(
        "idx_entity_merge_records_target_entity_id",
        "entity_merge_records",
        ["target_entity_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_entity_merge_records_target_entity_id", table_name="entity_merge_records")
    op.drop_index("idx_entity_merge_records_source_entity_id", table_name="entity_merge_records")
