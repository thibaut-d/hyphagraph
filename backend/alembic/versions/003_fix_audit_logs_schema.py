"""fix_audit_logs_schema

Revision ID: 003
Revises: 002
Create Date: 2024-12-31

Fixes audit_logs table schema to match the AuditLog model.
The old schema had columns: action, resource_type, resource_id, timestamp
The new schema has columns: event_type, event_status, user_email, error_message, created_at
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_fix_audit_logs_schema'
down_revision: Union[str, None] = '002_add_filter_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old audit_logs table if it exists
    op.execute('DROP TABLE IF EXISTS audit_logs CASCADE')

    # Create new audit_logs table with correct schema
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(length=50), nullable=False, index=True, comment="Type of event (e.g., 'login', 'password_change', 'account_deletion')"),
        sa.Column('event_status', sa.String(length=20), nullable=False, index=True, comment="Status of the event ('success' or 'failure')"),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True, comment="User who triggered the event (nullable for failed login attempts)"),
        sa.Column('user_email', sa.String(), nullable=True, comment="Email address used in the event (stored separately in case user is deleted)"),
        sa.Column('ip_address', sa.String(length=45), nullable=True, index=True, comment="IP address of the client (supports IPv6)"),
        sa.Column('user_agent', sa.Text(), nullable=True, comment="User agent string from the request"),
        sa.Column('details', postgresql.JSONB(), nullable=True, comment="Additional event-specific data in JSON format"),
        sa.Column('error_message', sa.Text(), nullable=True, comment="Error message for failed events"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )


def downgrade() -> None:
    # Drop the new table
    op.drop_table('audit_logs')

    # Recreate the old table (for reference, but this is destructive)
    # Note: This downgrade will lose all audit log data
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
    )

    # Recreate old indexes
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
