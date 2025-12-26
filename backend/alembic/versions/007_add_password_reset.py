"""Add password reset fields to users

Revision ID: 007_add_password_reset
Revises: 006_add_email_verification
Create Date: 2024-12-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '007_add_password_reset'
down_revision = '006_add_email_verification'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password reset columns to users table
    op.add_column('users', sa.Column('reset_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(timezone=True), nullable=True))

    # Create indexes
    op.create_index('ix_users_reset_token', 'users', ['reset_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_reset_token', table_name='users')
    op.drop_column('users', 'reset_token_expires_at')
    op.drop_column('users', 'reset_token')
