"""remove_deprecated_fields

Revision ID: 009_remove_deprecated_fields
Revises: 008_rename_metadata
Create Date: 2024-12-27

This migration removes deprecated fields after the revision architecture migration:
- Drops the old 'roles' table (replaced by relation_role_revisions)
- Removes deprecated fields from entities (kind, label, synonyms, ontology_ref)
- Removes deprecated fields from sources (kind, title, year, origin, url, trust_level, updated_at)
- Removes deprecated fields from relations (kind, direction, confidence, notes, updated_at)

All data should have been migrated to the revision tables in migration 002.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_remove_deprecated_fields'
down_revision = '008_rename_metadata'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove deprecated fields and tables."""

    # ============================================================================
    # 1. DROP OLD ROLES TABLE
    # ============================================================================
    # This table was replaced by relation_role_revisions in migration 002
    op.drop_table('roles')

    # ============================================================================
    # 2. REMOVE DEPRECATED FIELDS FROM ENTITIES
    # ============================================================================
    # These fields were moved to entity_revisions
    op.drop_column('entities', 'ontology_ref')
    op.drop_column('entities', 'synonyms')
    op.drop_column('entities', 'label')
    op.drop_column('entities', 'kind')

    # ============================================================================
    # 3. REMOVE DEPRECATED FIELDS FROM SOURCES
    # ============================================================================
    # These fields were moved to source_revisions
    # First drop the check constraint
    try:
        op.drop_constraint('ck_sources_trust_level', 'sources', type_='check')
    except Exception:
        # Constraint might not exist in SQLite or may have different name
        pass

    op.drop_column('sources', 'updated_at')
    op.drop_column('sources', 'trust_level')
    op.drop_column('sources', 'url')
    op.drop_column('sources', 'origin')
    op.drop_column('sources', 'year')
    op.drop_column('sources', 'title')
    op.drop_column('sources', 'kind')

    # ============================================================================
    # 4. REMOVE DEPRECATED FIELDS FROM RELATIONS
    # ============================================================================
    # These fields were moved to relation_revisions
    # First drop the check constraint
    try:
        op.drop_constraint('ck_relations_confidence', 'relations', type_='check')
    except Exception:
        # Constraint might not exist in SQLite or may have different name
        pass

    op.drop_column('relations', 'updated_at')
    op.drop_column('relations', 'notes')
    op.drop_column('relations', 'confidence')
    op.drop_column('relations', 'direction')
    op.drop_column('relations', 'kind')


def downgrade() -> None:
    """
    Restore deprecated fields and tables.

    WARNING: This will NOT restore data! Data was migrated to revision tables
    and cannot be automatically restored to the old schema.
    """

    # ============================================================================
    # 1. RESTORE RELATIONS FIELDS
    # ============================================================================
    op.add_column('relations', sa.Column('kind', sa.String(), nullable=True))
    op.add_column('relations', sa.Column('direction', sa.String(), nullable=True))
    op.add_column('relations', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column('relations', sa.Column('notes', sa.String(), nullable=True))
    op.add_column('relations', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # Restore check constraint
    op.create_check_constraint(
        'ck_relations_confidence',
        'relations',
        'confidence IS NULL OR (confidence >= 0 AND confidence <= 1)'
    )

    # ============================================================================
    # 2. RESTORE SOURCES FIELDS
    # ============================================================================
    op.add_column('sources', sa.Column('kind', sa.String(), nullable=True))
    op.add_column('sources', sa.Column('title', sa.String(), nullable=True))
    op.add_column('sources', sa.Column('year', sa.Integer(), nullable=True))
    op.add_column('sources', sa.Column('origin', sa.String(), nullable=True))
    op.add_column('sources', sa.Column('url', sa.String(), nullable=True))
    op.add_column('sources', sa.Column('trust_level', sa.Float(), nullable=True))
    op.add_column('sources', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # Restore check constraint
    op.create_check_constraint(
        'ck_sources_trust_level',
        'sources',
        'trust_level IS NULL OR (trust_level >= 0 AND trust_level <= 1)'
    )

    # ============================================================================
    # 3. RESTORE ENTITIES FIELDS
    # ============================================================================
    op.add_column('entities', sa.Column('kind', sa.String(), nullable=True))
    op.add_column('entities', sa.Column('label', sa.String(), nullable=True))
    op.add_column('entities', sa.Column('synonyms', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('entities', sa.Column('ontology_ref', sa.String(), nullable=True))

    # ============================================================================
    # 4. RESTORE ROLES TABLE
    # ============================================================================
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('relation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_type', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['relation_id'], ['relations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_roles_relation_id', 'roles', ['relation_id'])
    op.create_index('ix_roles_entity_id', 'roles', ['entity_id'])
