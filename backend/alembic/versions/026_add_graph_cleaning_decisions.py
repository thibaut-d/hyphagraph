"""add graph cleaning decisions

Revision ID: 026_add_graph_cleaning_decisions
Revises: 025_add_observational_relation_types
Create Date: 2026-04-27 19:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "026_add_graph_cleaning_decisions"
down_revision = "025_add_observational_relation_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_cleaning_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_type", sa.String(length=64), nullable=False),
        sa.Column("candidate_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decision_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("action_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "candidate_type",
            "candidate_fingerprint",
            name="uq_graph_cleaning_decision_candidate",
        ),
    )
    op.create_index(
        "ix_graph_cleaning_decisions_candidate_type",
        "graph_cleaning_decisions",
        ["candidate_type"],
    )
    op.create_index(
        "ix_graph_cleaning_decisions_candidate_fingerprint",
        "graph_cleaning_decisions",
        ["candidate_fingerprint"],
    )
    op.create_index(
        "ix_graph_cleaning_decisions_reviewed_by_user_id",
        "graph_cleaning_decisions",
        ["reviewed_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_graph_cleaning_decisions_reviewed_by_user_id", table_name="graph_cleaning_decisions")
    op.drop_index("ix_graph_cleaning_decisions_candidate_fingerprint", table_name="graph_cleaning_decisions")
    op.drop_index("ix_graph_cleaning_decisions_candidate_type", table_name="graph_cleaning_decisions")
    op.drop_table("graph_cleaning_decisions")
