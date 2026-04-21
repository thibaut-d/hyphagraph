"""Add resolved status fields to bug_reports

Revision ID: 021_add_bug_report_status
Revises: 020_entity_term_display_flag
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = "021_add_bug_report_status"
down_revision = "020_entity_term_display_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bug_reports",
        sa.Column(
            "resolved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "bug_reports",
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "bug_reports",
        sa.Column(
            "resolved_by",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_bug_reports_resolved", "bug_reports", ["resolved"])


def downgrade() -> None:
    op.drop_index("ix_bug_reports_resolved", table_name="bug_reports")
    op.drop_column("bug_reports", "resolved_by")
    op.drop_column("bug_reports", "resolved_at")
    op.drop_column("bug_reports", "resolved")
