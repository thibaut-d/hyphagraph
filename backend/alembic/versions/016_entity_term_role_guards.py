"""Add uniqueness guards for null-language entity terms and relation participants

Revision ID: 016_entity_term_role_guards
Revises: 015_add_bug_reports
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa


revision = "016_entity_term_role_guards"
down_revision = "015_add_bug_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_entity_terms_entity_term_null_language_unique",
        "entity_terms",
        ["entity_id", "term"],
        unique=True,
        postgresql_where=sa.text("language IS NULL"),
    )
    op.create_unique_constraint(
        "uq_relation_role_revision_participant",
        "relation_role_revisions",
        ["relation_revision_id", "entity_id", "role_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_relation_role_revision_participant",
        "relation_role_revisions",
        type_="unique",
    )
    op.drop_index(
        "ix_entity_terms_entity_term_null_language_unique",
        table_name="entity_terms",
    )
