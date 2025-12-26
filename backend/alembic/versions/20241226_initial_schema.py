"""initial_schema

Revision ID: 001_initial
Revises:
Create Date: 2024-12-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table (FastAPI Users)
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('hashed_password', sa.String(length=1024), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create entities table
    op.create_table(
        'entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('synonyms', postgresql.ARRAY(sa.String()), nullable=True, server_default='{}'),
        sa.Column('ontology_ref', sa.String(), nullable=True),
    )

    # Create sources table
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('origin', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('trust_level', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Add check constraint for trust_level
    op.create_check_constraint(
        'ck_sources_trust_level',
        'sources',
        'trust_level >= 0 AND trust_level <= 1'
    )

    # Create relations table
    op.create_table(
        'relations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
    )
    # Add check constraint for confidence
    op.create_check_constraint(
        'ck_relations_confidence',
        'relations',
        'confidence >= 0 AND confidence <= 1'
    )
    # Add index for source_id (for finding relations by source)
    op.create_index('ix_relations_source_id', 'relations', ['source_id'])

    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('relation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_type', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['relation_id'], ['relations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
    )
    # Add indexes for lookups
    op.create_index('ix_roles_relation_id', 'roles', ['relation_id'])
    op.create_index('ix_roles_entity_id', 'roles', ['entity_id'])

    # Create inference_cache table
    op.create_table(
        'inference_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scope_hash', sa.String(), nullable=False),
        sa.Column('result', postgresql.JSON(), nullable=False),
        sa.Column('uncertainty', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Add unique constraint and index for scope_hash
    op.create_index('ix_inference_cache_scope_hash', 'inference_cache', ['scope_hash'], unique=True)
    # Add check constraint for uncertainty
    op.create_check_constraint(
        'ck_inference_cache_uncertainty',
        'inference_cache',
        'uncertainty IS NULL OR (uncertainty >= 0 AND uncertainty <= 1)'
    )


def downgrade() -> None:
    op.drop_table('inference_cache')
    op.drop_table('roles')
    op.drop_table('relations')
    op.drop_table('sources')
    op.drop_table('entities')
    op.drop_table('users')
