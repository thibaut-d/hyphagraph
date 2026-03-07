"""Add staged_extractions table for human-in-the-loop review

Revision ID: 002_add_staged_extractions
Revises: 001_initial_schema
Create Date: 2026-03-07

Adds staged_extractions table to support human review of LLM extractions
before materializing them into the knowledge graph.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text
import uuid

# revision identifiers, used by Alembic.
revision = '002_add_staged_extractions'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create staged_extractions table."""
    op.create_table(
        'staged_extractions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('extraction_type', sa.String(50), nullable=False),  # entity, relation, claim
        sa.Column('status', sa.String(50), nullable=False),  # pending, approved, rejected, materialized

        # Source tracking
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),

        # LLM extraction data (JSON/JSONB depending on database)
        sa.Column('extraction_data', sa.JSON, nullable=False),

        # Validation metadata
        sa.Column('validation_score', sa.Float(), nullable=False),
        sa.Column('confidence_adjustment', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('validation_flags', sa.JSON, nullable=False, server_default='[]'),
        sa.Column('matched_span', sa.Text(), nullable=True),

        # LLM metadata
        sa.Column('llm_model', sa.String(100), nullable=True),
        sa.Column('llm_provider', sa.String(50), nullable=True),

        # Review metadata
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),

        # Materialization tracking
        sa.Column('materialized_entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('materialized_relation_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Auto-commit metadata
        sa.Column('auto_commit_eligible', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_commit_threshold', sa.Float(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['materialized_entity_id'], ['entities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['materialized_relation_id'], ['relations.id'], ondelete='SET NULL'),
    )

    # Create indexes
    op.create_index('ix_staged_extractions_extraction_type', 'staged_extractions', ['extraction_type'])
    op.create_index('ix_staged_extractions_status', 'staged_extractions', ['status'])
    op.create_index('ix_staged_extractions_source_id', 'staged_extractions', ['source_id'])
    op.create_index('ix_staged_extractions_validation_score', 'staged_extractions', ['validation_score'])


def downgrade() -> None:
    """Drop staged_extractions table."""
    op.drop_index('ix_staged_extractions_validation_score', table_name='staged_extractions')
    op.drop_index('ix_staged_extractions_source_id', table_name='staged_extractions')
    op.drop_index('ix_staged_extractions_status', table_name='staged_extractions')
    op.drop_index('ix_staged_extractions_extraction_type', table_name='staged_extractions')
    op.drop_table('staged_extractions')
