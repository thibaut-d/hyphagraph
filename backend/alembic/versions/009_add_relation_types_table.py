"""Add relation_types table for dynamic relation vocabulary

Revision ID: 009
Revises: 008
Create Date: 2026-01-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
import json


# revision identifiers
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create relation_types table and seed with initial types."""

    # Create table
    op.create_table(
        'relation_types',
        sa.Column('type_id', sa.String(50), primary_key=True),
        sa.Column('label', JSON, nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('examples', sa.Text, nullable=True),
        sa.Column('aliases', sa.Text, nullable=True),  # JSON array as text
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('is_system', sa.Boolean, nullable=False, default=False),
        sa.Column('usage_count', sa.Integer, nullable=False, default=0),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    # Create indexes
    op.create_index('idx_relation_type_active', 'relation_types', ['is_active'])
    op.create_index('idx_relation_type_category', 'relation_types', ['category'])

    # Seed initial relation types (migrated from RelationType Literal)
    relation_types = [
        {
            'type_id': 'treats',
            'label': json.dumps({'en': 'Treats', 'fr': 'Traite'}),
            'description': 'Drug, treatment, or intervention that treats a disease, symptom, or condition',
            'examples': 'aspirin treats migraine; duloxetine treats fibromyalgia',
            'aliases': json.dumps(['cures', 'heals', 'ameliorates']),
            'category': 'therapeutic',
            'is_system': True,
        },
        {
            'type_id': 'causes',
            'label': json.dumps({'en': 'Causes', 'fr': 'Cause'}),
            'description': 'Drug, disease, or factor that causes a symptom, outcome, or condition',
            'examples': 'duloxetine causes nausea; smoking causes cancer',
            'aliases': json.dumps(['induces', 'leads to', 'results in']),
            'category': 'causal',
            'is_system': True,
        },
        {
            'type_id': 'prevents',
            'label': json.dumps({'en': 'Prevents', 'fr': 'Prévient'}),
            'description': 'Drug or intervention that prevents a disease or outcome',
            'examples': 'aspirin prevents heart attack; vaccine prevents infection',
            'aliases': json.dumps(['protects from', 'reduces risk of']),
            'category': 'therapeutic',
            'is_system': True,
        },
        {
            'type_id': 'increases_risk',
            'label': json.dumps({'en': 'Increases Risk', 'fr': 'Augmente le Risque'}),
            'description': 'Factor that increases the risk of a disease or outcome',
            'examples': 'smoking increases_risk lung cancer',
            'aliases': json.dumps(['elevates risk', 'predisposes to']),
            'category': 'causal',
            'is_system': True,
        },
        {
            'type_id': 'decreases_risk',
            'label': json.dumps({'en': 'Decreases Risk', 'fr': 'Diminue le Risque'}),
            'description': 'Factor that decreases the risk of a disease or outcome',
            'examples': 'exercise decreases_risk cardiovascular disease',
            'aliases': json.dumps(['lowers risk', 'protective against']),
            'category': 'therapeutic',
            'is_system': True,
        },
        {
            'type_id': 'mechanism',
            'label': json.dumps({'en': 'Mechanism', 'fr': 'Mécanisme'}),
            'description': 'Biological or chemical mechanism underlying an effect',
            'examples': 'aspirin mechanism COX-inhibition',
            'aliases': json.dumps(['works via', 'acts through']),
            'category': 'mechanistic',
            'is_system': True,
        },
        {
            'type_id': 'contraindicated',
            'label': json.dumps({'en': 'Contraindicated', 'fr': 'Contre-indiqué'}),
            'description': 'Drug or treatment that should not be used in a specific condition or with another drug',
            'examples': 'warfarin contraindicated pregnancy',
            'aliases': json.dumps(['should not use', 'avoid in']),
            'category': 'safety',
            'is_system': True,
        },
        {
            'type_id': 'interacts_with',
            'label': json.dumps({'en': 'Interacts With', 'fr': 'Interagit Avec'}),
            'description': 'Drug that interacts with another drug or substance',
            'examples': 'warfarin interacts_with aspirin',
            'aliases': json.dumps(['drug interaction', 'affects']),
            'category': 'safety',
            'is_system': True,
        },
        {
            'type_id': 'metabolized_by',
            'label': json.dumps({'en': 'Metabolized By', 'fr': 'Métabolisé Par'}),
            'description': 'Drug that is metabolized by a specific enzyme or pathway',
            'examples': 'duloxetine metabolized_by CYP2D6',
            'aliases': json.dumps(['processed by', 'broken down by']),
            'category': 'mechanistic',
            'is_system': True,
        },
        {
            'type_id': 'biomarker_for',
            'label': json.dumps({'en': 'Biomarker For', 'fr': 'Biomarqueur De'}),
            'description': 'Biomarker or test that indicates a disease or condition',
            'examples': 'CRP biomarker_for inflammation',
            'aliases': json.dumps(['indicates', 'marker of']),
            'category': 'diagnostic',
            'is_system': True,
        },
        {
            'type_id': 'affects_population',
            'label': json.dumps({'en': 'Affects Population', 'fr': 'Affecte Population'}),
            'description': 'Treatment or condition that affects a specific population group',
            'examples': 'fibromyalgia affects_population women',
            'aliases': json.dumps(['prevalent in', 'common in']),
            'category': 'epidemiological',
            'is_system': True,
        },
        {
            'type_id': 'measures',
            'label': json.dumps({'en': 'Measures', 'fr': 'Mesure'}),
            'description': 'Assessment tool, test, or scale that measures a condition, symptom, or outcome',
            'examples': 'VAS measures pain; MoCA measures cognitive-function; BDI measures depression',
            'aliases': json.dumps(['assesses', 'evaluates', 'quantifies']),
            'category': 'diagnostic',
            'is_system': True,
        },
        {
            'type_id': 'other',
            'label': json.dumps({'en': 'Other', 'fr': 'Autre'}),
            'description': 'Any other type of relationship not covered by specific types',
            'examples': 'Various domain-specific relationships',
            'aliases': json.dumps([]),
            'category': 'general',
            'is_system': True,
        },
    ]

    # Insert seed data
    from datetime import datetime
    now = datetime.utcnow()

    for rt in relation_types:
        op.execute(f"""
            INSERT INTO relation_types (
                type_id, label, description, examples, aliases,
                is_active, is_system, usage_count, category, created_at
            ) VALUES (
                '{rt['type_id']}',
                '{rt['label']}',
                '{rt['description']}',
                '{rt.get('examples', '')}',
                '{rt.get('aliases', 'null')}',
                true,
                {rt['is_system']},
                0,
                '{rt.get('category', 'general')}',
                '{now.isoformat()}'
            )
        """)


def downgrade() -> None:
    """Drop relation_types table."""
    op.drop_index('idx_relation_type_category', 'relation_types')
    op.drop_index('idx_relation_type_active', 'relation_types')
    op.drop_table('relation_types')
