"""Add email verification fields to users

Revision ID: 006_add_email_verification
Revises: 005_add_audit_logs
Create Date: 2024-12-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006_add_email_verification'
down_revision = '005_add_audit_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add email verification columns to users table
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('verification_token_expires_at', sa.DateTime(timezone=True), nullable=True))

    # Create indexes
    op.create_index('ix_users_verification_token', 'users', ['verification_token'], unique=True)

    # Set existing users as verified (they're already in the system)
    op.execute("UPDATE users SET is_verified = true WHERE is_verified = false")


def downgrade() -> None:
    op.drop_index('ix_users_verification_token', table_name='users')
    op.drop_column('users', 'verification_token_expires_at')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
