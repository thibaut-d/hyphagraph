"""add long running jobs

Revision ID: 027_add_long_running_jobs
Revises: 026_add_graph_cleaning_decisions
Create Date: 2026-05-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "027_add_long_running_jobs"
down_revision = "026_add_graph_cleaning_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "long_running_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_long_running_jobs_kind", "long_running_jobs", ["kind"])
    op.create_index("ix_long_running_jobs_status", "long_running_jobs", ["status"])
    op.create_index("ix_long_running_jobs_user_id", "long_running_jobs", ["user_id"])
    op.create_index("ix_long_running_jobs_source_id", "long_running_jobs", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_long_running_jobs_source_id", table_name="long_running_jobs")
    op.drop_index("ix_long_running_jobs_user_id", table_name="long_running_jobs")
    op.drop_index("ix_long_running_jobs_status", table_name="long_running_jobs")
    op.drop_index("ix_long_running_jobs_kind", table_name="long_running_jobs")
    op.drop_table("long_running_jobs")
