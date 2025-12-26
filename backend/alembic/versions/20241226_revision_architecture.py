"""add_revision_architecture

Revision ID: 002_revisions
Revises: 001_initial
Create Date: 2024-12-26

This migration adds the full revision architecture:
- EntityRevision, SourceRevision, RelationRevision tables
- UiCategory, EntityTerm, Attribute tables
- RelationRoleRevision and ComputedRelation tables
- Migrates existing data to first revision (is_current=true)

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '002_revisions'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================================
    # 1. CREATE UI_CATEGORIES TABLE
    # ============================================================================
    op.create_table(
        'ui_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('labels', postgresql.JSONB(), nullable=False),
        sa.Column('description', postgresql.JSONB(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ui_categories_slug', 'ui_categories', ['slug'], unique=True)
    op.create_check_constraint('ck_ui_categories_order', 'ui_categories', 'order >= 0')

    # ============================================================================
    # 2. UPDATE ENTITIES TABLE - Add created_at, make fields nullable
    # ============================================================================
    # Add created_at column (for new revision architecture)
    op.add_column('entities', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=text('now()')))

    # Make existing fields nullable (they'll be moved to revisions)
    op.alter_column('entities', 'kind', nullable=True)
    op.alter_column('entities', 'label', nullable=True)

    # Backfill created_at for existing rows
    op.execute("UPDATE entities SET created_at = now() WHERE created_at IS NULL")
    op.alter_column('entities', 'created_at', nullable=False)

    # ============================================================================
    # 3. CREATE ENTITY_REVISIONS TABLE
    # ============================================================================
    op.create_table(
        'entity_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ui_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('summary', postgresql.JSONB(), nullable=True),
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

    # ============================================================================
    # 4. CREATE ENTITY_TERMS TABLE
    # ============================================================================
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
    # 5. UPDATE SOURCES TABLE - make fields nullable
    # ============================================================================
    op.alter_column('sources', 'kind', nullable=True)
    op.alter_column('sources', 'title', nullable=True)
    op.alter_column('sources', 'year', nullable=True)
    op.alter_column('sources', 'trust_level', nullable=True)

    # ============================================================================
    # 6. CREATE SOURCE_REVISIONS TABLE
    # ============================================================================
    op.create_table(
        'source_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('authors', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('origin', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('trust_level', sa.Float(), nullable=True),
        sa.Column('summary', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
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
    # 7. UPDATE RELATIONS TABLE - make fields nullable
    # ============================================================================
    op.alter_column('relations', 'kind', nullable=True)
    op.alter_column('relations', 'direction', nullable=True)
    op.alter_column('relations', 'confidence', nullable=True)

    # ============================================================================
    # 8. CREATE RELATION_REVISIONS TABLE
    # ============================================================================
    op.create_table(
        'relation_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('relation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(), nullable=True),
        sa.Column('direction', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('scope', postgresql.JSONB(), nullable=True),
        sa.Column('notes', postgresql.JSONB(), nullable=True),
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

    # ============================================================================
    # 9. CREATE RELATION_ROLE_REVISIONS TABLE
    # ============================================================================
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
    # 10. CREATE ATTRIBUTES TABLE
    # ============================================================================
    op.create_table(
        'attributes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('owner_type', sa.Enum('entity', 'relation', name='attributeownertype'), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_attributes_owner', 'attributes', ['owner_type', 'owner_id'])
    op.create_check_constraint(
        'ck_attribute_owner_type',
        'attributes',
        "owner_type IN ('entity', 'relation')"
    )

    # ============================================================================
    # 11. CREATE COMPUTED_RELATIONS TABLE
    # ============================================================================
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

    # ============================================================================
    # 12. MIGRATE EXISTING DATA TO REVISIONS
    # ============================================================================
    # This SQL migrates existing entity data to the first revision
    op.execute("""
        INSERT INTO entity_revisions (id, entity_id, slug, created_at, is_current)
        SELECT
            gen_random_uuid() as id,
            e.id as entity_id,
            e.label as slug,
            e.created_at,
            true as is_current
        FROM entities e
        WHERE e.label IS NOT NULL
    """)

    # Migrate existing source data to the first revision
    op.execute("""
        INSERT INTO source_revisions (
            id, source_id, kind, title, year, origin, url, trust_level, created_at, is_current
        )
        SELECT
            gen_random_uuid() as id,
            s.id as source_id,
            s.kind,
            s.title,
            s.year,
            s.origin,
            COALESCE(s.url, '') as url,
            s.trust_level,
            s.created_at,
            true as is_current
        FROM sources s
        WHERE s.title IS NOT NULL
    """)

    # Migrate existing relation data to the first revision
    op.execute("""
        INSERT INTO relation_revisions (
            id, relation_id, kind, direction, confidence, created_at, is_current
        )
        SELECT
            gen_random_uuid() as id,
            r.id as relation_id,
            r.kind,
            r.direction,
            r.confidence,
            r.created_at,
            true as is_current
        FROM relations r
        WHERE r.kind IS NOT NULL
    """)

    # Migrate existing roles to relation_role_revisions
    op.execute("""
        INSERT INTO relation_role_revisions (
            id, relation_revision_id, entity_id, role_type
        )
        SELECT
            gen_random_uuid() as id,
            rr.id as relation_revision_id,
            ro.entity_id,
            ro.role_type
        FROM roles ro
        JOIN relation_revisions rr ON rr.relation_id = ro.relation_id
        WHERE rr.is_current = true
    """)


def downgrade() -> None:
    """
    Downgrade removes all revision tables.

    WARNING: This will lose revision history!
    """
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('computed_relations')
    op.drop_table('attributes')
    op.drop_table('relation_role_revisions')
    op.drop_table('relation_revisions')
    op.drop_table('source_revisions')
    op.drop_table('entity_terms')
    op.drop_table('entity_revisions')
    op.drop_table('ui_categories')

    # Restore old columns to NOT NULL (if desired)
    op.alter_column('relations', 'kind', nullable=False)
    op.alter_column('relations', 'direction', nullable=False)
    op.alter_column('relations', 'confidence', nullable=False)

    op.alter_column('sources', 'kind', nullable=False)
    op.alter_column('sources', 'title', nullable=False)
    op.alter_column('sources', 'year', nullable=False)
    op.alter_column('sources', 'trust_level', nullable=False)

    op.alter_column('entities', 'kind', nullable=False)
    op.alter_column('entities', 'label', nullable=False)

    op.drop_column('entities', 'created_at')

    # Drop enum type
    op.execute('DROP TYPE attributeownertype')
