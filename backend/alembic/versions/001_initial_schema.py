"""Initial schema - Create all tables from scratch

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-12

This migration creates the complete HyphaGraph database schema from scratch:
- User authentication (users, refresh_tokens, audit_logs)
- Entity revision architecture (entities, entity_revisions, entity_terms)
- Source revision architecture (sources, source_revisions)
- Relation revision architecture (relations, relation_revisions, relation_role_revisions)
- Supporting tables (ui_categories, relation_types, computed_relations)

Also seeds initial data:
- 9 UI categories
- 13 relation types
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text
import uuid
import json

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================================
    # 1. USERS TABLE
    # ============================================================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
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

    # ============================================================================
    # 2. REFRESH_TOKENS TABLE
    # ============================================================================
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
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
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])

    # ============================================================================
    # 3. AUDIT_LOGS TABLE
    # ============================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('event_type', sa.String(length=50), nullable=False, comment="Type of event"),
        sa.Column('event_status', sa.String(length=20), nullable=False, comment="Status of the event"),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, comment="User who triggered the event"),
        sa.Column('user_email', sa.String(), nullable=True, comment="Email address used in the event"),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment="IP address of the client"),
        sa.Column('user_agent', sa.Text(), nullable=True, comment="User agent string from the request"),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Additional event-specific data"),
        sa.Column('error_message', sa.Text(), nullable=True, comment="Error message for failed events"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_event_status', 'audit_logs', ['event_status'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_ip_address', 'audit_logs', ['ip_address'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # ============================================================================
    # 4. UI_CATEGORIES TABLE
    # ============================================================================
    op.create_table(
        'ui_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('description', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ui_categories_slug', 'ui_categories', ['slug'], unique=True)
    op.create_check_constraint('ck_ui_categories_order', 'ui_categories', '"order" >= 0')

    # ============================================================================
    # 5. ENTITIES TABLE
    # ============================================================================
    op.create_table(
        'entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
    )

    # ============================================================================
    # 6. ENTITY_REVISIONS TABLE
    # ============================================================================
    op.create_table(
        'entity_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ui_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
    # Partial unique index: only one current revision can have a given slug
    op.execute("""
        CREATE UNIQUE INDEX ix_entity_revisions_slug_current_unique
        ON entity_revisions (slug)
        WHERE is_current = true
    """)

    # ============================================================================
    # 7. ENTITY_TERMS TABLE
    # ============================================================================
    op.create_table(
        'entity_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term', sa.String(), nullable=False),
        sa.Column('language', sa.String(10), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_entity_terms_entity_id', 'entity_terms', ['entity_id'])
    op.create_index('ix_entity_terms_term', 'entity_terms', ['term'])
    op.create_unique_constraint('uq_entity_term_language', 'entity_terms', ['entity_id', 'term', 'language'])
    op.create_check_constraint('ck_entity_terms_display_order', 'entity_terms', 'display_order IS NULL OR display_order >= 0')

    # ============================================================================
    # 8. SOURCES TABLE
    # ============================================================================
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
    )

    # ============================================================================
    # 9. SOURCE_REVISIONS TABLE
    # ============================================================================
    op.create_table(
        'source_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('authors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('origin', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('trust_level', sa.Float(), nullable=True),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('document_text', sa.Text(), nullable=True),
        sa.Column('document_format', sa.String(), nullable=True),
        sa.Column('document_file_name', sa.String(), nullable=True),
        sa.Column('document_extracted_at', sa.DateTime(timezone=True), nullable=True),
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
    # 10. RELATIONS TABLE
    # ============================================================================
    op.create_table(
        'relations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_relations_source_id', 'relations', ['source_id'])

    # ============================================================================
    # 11. RELATION_REVISIONS TABLE
    # ============================================================================
    op.create_table(
        'relation_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('relation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(), nullable=True),
        sa.Column('direction', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
    # 12. RELATION_ROLE_REVISIONS TABLE
    # ============================================================================
    op.create_table(
        'relation_role_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
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
    # 13. RELATION_TYPES TABLE
    # ============================================================================
    op.create_table(
        'relation_types',
        sa.Column('type_id', sa.String(50), primary_key=True),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('examples', sa.Text(), nullable=True),
        sa.Column('aliases', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_relation_type_active', 'relation_types', ['is_active'])
    op.create_index('idx_relation_type_category', 'relation_types', ['category'])

    # ============================================================================
    # 14. COMPUTED_RELATIONS TABLE
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
    # 15. SEED UI CATEGORIES
    # ============================================================================
    # 9 categories matching the extraction prompt
    categories = [
        ('drugs', {'en': 'Drugs', 'fr': 'Médicaments'}, {'en': 'Medications, pharmaceuticals, active ingredients'}, 1),
        ('diseases', {'en': 'Diseases', 'fr': 'Maladies'}, {'en': 'Medical conditions, disorders, illnesses'}, 2),
        ('symptoms', {'en': 'Symptoms', 'fr': 'Symptômes'}, {'en': 'Observable signs or symptoms of conditions'}, 3),
        ('biological-mechanisms', {'en': 'Biological Mechanisms', 'fr': 'Mécanismes biologiques'}, {'en': 'Pathways, mechanisms, physiological processes'}, 4),
        ('treatments', {'en': 'Treatments', 'fr': 'Traitements'}, {'en': 'Therapeutic interventions (non-drug)'}, 5),
        ('biomarkers', {'en': 'Biomarkers', 'fr': 'Biomarqueurs'}, {'en': 'Measurable indicators (lab values, proteins, genes)'}, 6),
        ('populations', {'en': 'Populations', 'fr': 'Populations'}, {'en': 'Patient groups, demographics'}, 7),
        ('outcomes', {'en': 'Outcomes', 'fr': 'Résultats'}, {'en': 'Clinical outcomes, endpoints'}, 8),
        ('effects', {'en': 'Effects', 'fr': 'Effets'}, {'en': 'Effects, side effects, adverse events'}, 9),
    ]

    for slug, labels, description, order in categories:
        labels_json = json.dumps(labels)
        description_json = json.dumps(description)
        op.execute(f"""
            INSERT INTO ui_categories (id, slug, labels, description, "order")
            VALUES (
                gen_random_uuid(),
                '{slug}',
                '{labels_json}'::jsonb,
                '{description_json}'::jsonb,
                {order}
            )
        """)

    # ============================================================================
    # 16. SEED RELATION TYPES
    # ============================================================================
    # 13 relation types from the extraction prompt
    relation_types = [
        ('treats', '{"en": "Treats"}', 'Drug/treatment treats disease/symptom', 'aspirin treats migraine', '["cures", "heals"]', 'therapeutic'),
        ('causes', '{"en": "Causes"}', 'Drug/disease causes symptom/outcome', 'aspirin causes stomach irritation', '["triggers", "induces"]', 'causal'),
        ('prevents', '{"en": "Prevents"}', 'Drug/treatment prevents disease/outcome', 'vaccine prevents infection', '["protects against"]', 'therapeutic'),
        ('increases_risk', '{"en": "Increases Risk"}', 'Factor increases risk of disease/outcome', 'smoking increases risk of lung cancer', '["raises risk"]', 'causal'),
        ('decreases_risk', '{"en": "Decreases Risk"}', 'Factor decreases risk of disease/outcome', 'exercise decreases risk of heart disease', '["lowers risk", "reduces risk"]', 'therapeutic'),
        ('mechanism', '{"en": "Mechanism"}', 'Biological mechanism underlying an effect', 'aspirin inhibits COX-2', '["pathway", "process"]', 'mechanistic'),
        ('contraindicated', '{"en": "Contraindicated"}', 'Drug/treatment should not be used with disease/drug', 'aspirin contraindicated in bleeding disorders', '["should not use with"]', 'therapeutic'),
        ('interacts_with', '{"en": "Interacts With"}', 'Drug interacts with another drug', 'warfarin interacts with aspirin', '["reacts with"]', 'interaction'),
        ('metabolized_by', '{"en": "Metabolized By"}', 'Drug is metabolized by enzyme/pathway', 'codeine metabolized by CYP2D6', '["processed by"]', 'mechanistic'),
        ('biomarker_for', '{"en": "Biomarker For"}', 'Biomarker indicates disease/condition', 'PSA is biomarker for prostate cancer', '["indicates", "marker for"]', 'diagnostic'),
        ('affects_population', '{"en": "Affects Population"}', 'Treatment affects specific population', 'statins affect elderly differently', '["impacts"]', 'population'),
        ('measures', '{"en": "Measures"}', 'Assessment tool/test measures condition/symptom', 'VAS measures pain intensity; MoCA measures cognitive function', '["assesses", "evaluates"]', 'diagnostic'),
        ('other', '{"en": "Other"}', 'Any other type of relationship not fitting above categories', None, None, 'other'),
    ]

    for type_id, label, description, examples, aliases, category in relation_types:
        examples_sql = f"'{examples}'" if examples else 'NULL'
        aliases_sql = f"'{aliases}'" if aliases else 'NULL'
        op.execute(f"""
            INSERT INTO relation_types (type_id, label, description, examples, aliases, is_active, is_system, category)
            VALUES (
                '{type_id}',
                '{label}',
                '{description}',
                {examples_sql},
                {aliases_sql},
                true,
                true,
                '{category}'
            )
        """)

    # ============================================================================
    # 17. CREATE SEMANTIC_ROLE_TYPES TABLE
    # ============================================================================
    op.create_table(
        'semantic_role_types',
        sa.Column('role_type', sa.String(50), primary_key=True),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('examples', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
    )

    # ============================================================================
    # 18. SEED SEMANTIC ROLE TYPES
    # ============================================================================
    # 16 semantic roles for hypergraph model
    semantic_roles = [
        # Core roles
        ('agent', '{"en": "Agent", "fr": "Agent"}', 'Entity performing action or causing effect', 'core', 'duloxetine (agent) treats fibromyalgia'),
        ('target', '{"en": "Target", "fr": "Cible"}', 'Entity receiving action or being affected', 'core', 'fibromyalgia (target) in duloxetine treats fibromyalgia'),
        ('outcome', '{"en": "Outcome", "fr": "Résultat"}', 'Result or effect produced', 'core', 'pain-relief (outcome) produced by treatment'),
        ('mechanism', '{"en": "Mechanism", "fr": "Mécanisme"}', 'Biological mechanism involved', 'core', 'serotonin-reuptake (mechanism) of duloxetine'),
        ('population', '{"en": "Population", "fr": "Population"}', 'Patient population or demographic group', 'core', 'adults, women, elderly'),
        ('condition', '{"en": "Condition", "fr": "Condition"}', 'Clinical condition or context', 'core', 'chronic-pain, depression'),
        # Measurement roles
        ('measured_by', '{"en": "Measured By", "fr": "Mesuré Par"}', 'Assessment tool or instrument', 'measurement', 'VAS, MoCA as measurement tools'),
        ('biomarker', '{"en": "Biomarker", "fr": "Biomarqueur"}', 'Diagnostic or prognostic marker', 'measurement', 'CRP, miRNA as biomarkers'),
        ('control_group', '{"en": "Control Group", "fr": "Groupe Témoin"}', 'Comparison group in study', 'measurement', 'healthy-controls, placebo'),
        ('study_group', '{"en": "Study Group", "fr": "Groupe Étude"}', 'Experimental or patient group', 'measurement', 'fibromyalgia-patients'),
        # Contextual roles
        ('location', '{"en": "Location", "fr": "Localisation"}', 'Anatomical location', 'contextual', 'brain, joints, muscles'),
        ('dosage', '{"en": "Dosage", "fr": "Dosage"}', 'Dose or quantity', 'contextual', '60mg-daily, 100mg-bid'),
        ('duration', '{"en": "Duration", "fr": "Durée"}', 'Time period or duration', 'contextual', '12-weeks, 6-months'),
        ('frequency', '{"en": "Frequency", "fr": "Fréquence"}', 'How often or frequency', 'contextual', 'daily, weekly'),
        ('severity', '{"en": "Severity", "fr": "Sévérité"}', 'Intensity or severity level', 'contextual', 'mild, moderate, severe'),
        ('effect_size', '{"en": "Effect Size", "fr": "Taille Effet"}', 'Magnitude of effect', 'contextual', '25-percent-reduction'),
    ]

    for role_type, label, description, category, examples in semantic_roles:
        examples_sql = f"'{examples}'" if examples else 'NULL'
        op.execute(f"""
            INSERT INTO semantic_role_types (role_type, label, description, category, examples, is_active, is_system)
            VALUES (
                '{role_type}',
                '{label}',
                '{description}',
                '{category}',
                {examples_sql},
                true,
                true
            )
        """)


def downgrade() -> None:
    """
    Downgrade removes all tables.

    WARNING: This will lose all data!
    """
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('computed_relations')
    op.drop_table('semantic_role_types')
    op.drop_table('relation_types')
    op.drop_table('relation_role_revisions')
    op.drop_table('relation_revisions')
    op.drop_table('relations')
    op.drop_table('source_revisions')
    op.drop_table('sources')
    op.drop_table('entity_terms')
    op.drop_table('entity_revisions')
    op.drop_table('entities')
    op.drop_table('ui_categories')
    op.drop_table('audit_logs')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
