"""Add confirmed_by_user_id and confirmed_at to revision tables

Adds confirmation provenance to entity_revisions, source_revisions,
and relation_revisions so that the reviewer identity and time are
recorded when a draft revision is promoted to confirmed.

Also adds partial unique indexes to enforce the is_current invariant
at the database level (only one current revision per parent).

Revision ID: 010_add_rev_confirm_fields
Revises: 009_add_entity_merge_flag
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = "010_add_rev_confirm_fields"
down_revision = "009_add_entity_merge_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # entity_revisions
    op.add_column(
        "entity_revisions",
        sa.Column("confirmed_by_user_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "entity_revisions",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_entity_revisions_confirmed_by_user",
        "entity_revisions", "users",
        ["confirmed_by_user_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_entity_revisions_current_unique",
        "entity_revisions",
        ["entity_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    # source_revisions
    op.add_column(
        "source_revisions",
        sa.Column("confirmed_by_user_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "source_revisions",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_source_revisions_confirmed_by_user",
        "source_revisions", "users",
        ["confirmed_by_user_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_source_revisions_current_unique",
        "source_revisions",
        ["source_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    # relation_revisions
    op.add_column(
        "relation_revisions",
        sa.Column("confirmed_by_user_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "relation_revisions",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_relation_revisions_confirmed_by_user",
        "relation_revisions", "users",
        ["confirmed_by_user_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_relation_revisions_current_unique",
        "relation_revisions",
        ["relation_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_relation_revisions_current_unique", table_name="relation_revisions")
    op.drop_constraint("fk_relation_revisions_confirmed_by_user", "relation_revisions", type_="foreignkey")
    op.drop_column("relation_revisions", "confirmed_at")
    op.drop_column("relation_revisions", "confirmed_by_user_id")

    op.drop_index("ix_source_revisions_current_unique", table_name="source_revisions")
    op.drop_constraint("fk_source_revisions_confirmed_by_user", "source_revisions", type_="foreignkey")
    op.drop_column("source_revisions", "confirmed_at")
    op.drop_column("source_revisions", "confirmed_by_user_id")

    op.drop_index("ix_entity_revisions_current_unique", table_name="entity_revisions")
    op.drop_constraint("fk_entity_revisions_confirmed_by_user", "entity_revisions", type_="foreignkey")
    op.drop_column("entity_revisions", "confirmed_at")
    op.drop_column("entity_revisions", "confirmed_by_user_id")
