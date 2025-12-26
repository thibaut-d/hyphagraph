"""Add audit logs table

Revision ID: 005_add_audit_logs
Revises: 004_add_refresh_tokens
Create Date: 2024-12-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '005_add_audit_logs'
down_revision = '004_add_refresh_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False, comment="Type of event"),
        sa.Column('event_status', sa.String(length=20), nullable=False, comment="Status of the event"),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, comment="User who triggered the event"),
        sa.Column('user_email', sa.String(), nullable=True, comment="Email address used in the event"),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment="IP address of the client"),
        sa.Column('user_agent', sa.Text(), nullable=True, comment="User agent string from the request"),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Additional event-specific data"),
        sa.Column('error_message', sa.Text(), nullable=True, comment="Error message for failed events"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes for common queries
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_event_status', 'audit_logs', ['event_status'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_ip_address', 'audit_logs', ['ip_address'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_ip_address', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_event_status', table_name='audit_logs')
    op.drop_index('ix_audit_logs_event_type', table_name='audit_logs')
    op.drop_table('audit_logs')
