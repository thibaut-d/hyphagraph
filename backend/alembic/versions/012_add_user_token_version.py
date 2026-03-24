"""Add token_version column to users

Embeds a monotonically-increasing version number in access tokens so that
deleting or deactivating a user immediately invalidates all outstanding
access tokens without relying solely on the DB-presence check in
get_current_user.

Revision ID: 012_add_user_token_version
Revises: 011_add_staged_extraction_auto_approved
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa


revision = "012_add_user_token_version"
down_revision = "011_add_staged_extraction_auto_approved"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="Incremented on delete/deactivate to invalidate outstanding access tokens",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
