"""add calculated_trust_level to source_revisions

Revision ID: 017_add_calculated_trust_level
Revises: 016_entity_term_role_guards
Create Date: 2026-04-05

Moves calculated_trust_level from the source_metadata JSON blob to a typed
Float column on source_revisions so it is queryable and type-safe.
"""
from alembic import op
import sqlalchemy as sa

revision = "017_add_calculated_trust_level"
down_revision = "016_entity_term_role_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "source_revisions",
        sa.Column("calculated_trust_level", sa.Float(), nullable=True),
    )

    # Backfill from source_metadata JSON blob where present.
    # Uses a SQL CASE so it is dialect-agnostic (PostgreSQL + SQLite).
    op.execute(
        """
        UPDATE source_revisions
        SET calculated_trust_level = CAST(
            source_metadata->>'calculated_trust_level' AS FLOAT
        )
        WHERE source_metadata IS NOT NULL
          AND source_metadata->>'calculated_trust_level' IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("source_revisions", "calculated_trust_level")
