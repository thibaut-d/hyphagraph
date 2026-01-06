"""initial_clean

Revision ID: 001_initial_clean
Revises:
Create Date: 2024-12-27

Consolidated initial migration with clean schema:
- Complete revision architecture (entities, sources, relations)
- User authentication with JWT tokens
- Audit logging
- No deprecated fields

This replaces all previous migrations with a single clean migration.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '001_initial_clean'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================================
    # USERS & AUTHENTICATION
    # ============================================================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_token', sa.String(), nullable=True),
        sa.Column('verification_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reset_token', sa.String(), nullable=True),
        sa.Column('reset_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_verification_token', 'users', ['verification_token'], unique=True)
    op.create_index('ix_users_reset_token', 'users', ['reset_token'], unique=True)

    # Refresh tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)

    # ============================================================================
    # AUDIT LOGS
    # ============================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])

    # ============================================================================
    # ENTITIES
    # ============================================================================
    op.create_table(
        'entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
    )

    # UI Categories
    op.create_table(
        'ui_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('labels', sa.JSON(), nullable=False),
        sa.Column('description', sa.JSON(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('"order" >= 0', name='ck_ui_categories_order'),
    )
    op.create_index('ix_ui_categories_slug', 'ui_categories', ['slug'], unique=True)

    # Entity Revisions
    op.create_table(
        'entity_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ui_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('created_with_llm', sa.String(), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ui_category_id'], ['ui_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_entity_revisions_entity_id', 'entity_revisions', ['entity_id'])
    op.create_index('ix_entity_revisions_is_current', 'entity_revisions', ['entity_id', 'is_current'])

    # Entity Terms
    op.create_table(
        'entity_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term', sa.String(), nullable=False),
        sa.Column('language', sa.String(10), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_entity_terms_entity_id', 'entity_terms', ['entity_id'])
    op.create_index('ix_entity_terms_term', 'entity_terms', ['term'])
    op.create_unique_constraint('uq_entity_term_language', 'entity_terms', ['entity_id', 'term', 'language'])
    op.create_check_constraint('ck_entity_terms_display_order', 'entity_terms', 'display_order IS NULL OR display_order >= 0')

    # ============================================================================
    # SOURCES
    # ============================================================================
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
    )

    # Source Revisions
    op.create_table(
        'source_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('authors', sa.JSON(), nullable=True),  # Array of strings stored as JSON
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('origin', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('trust_level', sa.Float(), nullable=True),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('source_metadata', sa.JSON(), nullable=True),
        sa.Column('created_with_llm', sa.String(), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_source_revisions_source_id', 'source_revisions', ['source_id'])
    op.create_index('ix_source_revisions_is_current', 'source_revisions', ['source_id', 'is_current'])
    op.create_check_constraint(
        'ck_source_revisions_trust_level',
        'source_revisions',
        'trust_level IS NULL OR (trust_level >= 0 AND trust_level <= 1)'
    )

    # ============================================================================
    # RELATIONS
    # ============================================================================
    op.create_table(
        'relations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_relations_source_id', 'relations', ['source_id'])

    # Relation Revisions
    op.create_table(
        'relation_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('relation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(), nullable=True),
        sa.Column('direction', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('scope', sa.JSON(), nullable=True),
        sa.Column('notes', sa.JSON(), nullable=True),
        sa.Column('created_with_llm', sa.String(), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['relation_id'], ['relations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_relation_revisions_relation_id', 'relation_revisions', ['relation_id'])
    op.create_index('ix_relation_revisions_is_current', 'relation_revisions', ['relation_id', 'is_current'])
    op.create_check_constraint(
        'ck_relation_revisions_confidence',
        'relation_revisions',
        'confidence IS NULL OR (confidence >= 0 AND confidence <= 1)'
    )

    # Relation Role Revisions
    op.create_table(
        'relation_role_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('relation_revision_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_type', sa.String(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('coverage', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['relation_revision_id'], ['relation_revisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_relation_role_revisions_relation_revision_id', 'relation_role_revisions', ['relation_revision_id'])
    op.create_index('ix_relation_role_revisions_entity_id', 'relation_role_revisions', ['entity_id'])
    op.create_check_constraint(
        'ck_relation_role_revisions_weight',
        'relation_role_revisions',
        'weight IS NULL OR (weight >= -1 AND weight <= 1)'
    )
    op.create_check_constraint(
        'ck_relation_role_revisions_coverage',
        'relation_role_revisions',
        'coverage IS NULL OR coverage >= 0'
    )

    # ============================================================================
    # ATTRIBUTES & COMPUTED RELATIONS
    # ============================================================================
    op.create_table(
        'attributes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('owner_type', sa.Enum('entity', 'relation', name='attributeownertype'), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_attributes_owner', 'attributes', ['owner_type', 'owner_id'])
    op.create_check_constraint(
        'ck_attribute_owner_type',
        'attributes',
        "owner_type IN ('entity', 'relation')"
    )

    op.create_table(
        'computed_relations',
        sa.Column('relation_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scope_hash', sa.String(), nullable=False),
        sa.Column('model_version', sa.String(), nullable=False),
        sa.Column('uncertainty', sa.Float(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.ForeignKeyConstraint(['relation_id'], ['relations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_computed_relations_scope_hash', 'computed_relations', ['scope_hash'])
    op.create_check_constraint(
        'ck_computed_relations_uncertainty',
        'computed_relations',
        'uncertainty >= 0 AND uncertainty <= 1'
    )

    # Inference Cache
    op.create_table(
        'inference_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scope_hash', sa.String(), nullable=False),
        sa.Column('result', postgresql.JSON(), nullable=False),
        sa.Column('uncertainty', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_inference_cache_scope_hash', 'inference_cache', ['scope_hash'], unique=True)
    op.create_check_constraint(
        'ck_inference_cache_uncertainty',
        'inference_cache',
        'uncertainty IS NULL OR (uncertainty >= 0 AND uncertainty <= 1)'
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('inference_cache')
    op.drop_table('computed_relations')
    op.drop_table('attributes')
    op.drop_table('relation_role_revisions')
    op.drop_table('relation_revisions')
    op.drop_table('relations')
    op.drop_table('source_revisions')
    op.drop_table('sources')
    op.drop_table('entity_terms')
    op.drop_table('entity_revisions')
    op.drop_table('ui_categories')
    op.drop_table('entities')
    op.drop_table('audit_logs')
    op.drop_table('refresh_tokens')
    op.drop_table('users')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS attributeownertype')
