"""seed_ui_categories

Revision ID: 005_seed_ui_categories
Revises: 004_add_entity_terms_created_at
Create Date: 2026-01-01

Adds default UI categories for entity classification.

UI categories are NOT semantic - they're purely for UX purposes.
Examples: "Drugs", "Diseases", "Biological Mechanisms", "Effects"
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import uuid

# revision identifiers, used by Alembic.
revision = '005_seed_ui_categories'
down_revision = '004_add_entity_terms_created_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Seed default UI categories.

    These categories help users navigate and filter entities.
    They do NOT carry semantic meaning for inference.
    """
    # Define default categories with i18n labels
    categories = [
        {
            'id': str(uuid.uuid4()),
            'slug': 'drug',
            'labels': {'en': 'Drugs', 'fr': 'Médicaments'},
            'description': {'en': 'Pharmaceutical drugs and medications', 'fr': 'Médicaments et produits pharmaceutiques'},
            'order': 10
        },
        {
            'id': str(uuid.uuid4()),
            'slug': 'disease',
            'labels': {'en': 'Diseases', 'fr': 'Maladies'},
            'description': {'en': 'Medical conditions and diseases', 'fr': 'Conditions médicales et maladies'},
            'order': 20
        },
        {
            'id': str(uuid.uuid4()),
            'slug': 'symptom',
            'labels': {'en': 'Symptoms', 'fr': 'Symptômes'},
            'description': {'en': 'Clinical symptoms and signs', 'fr': 'Symptômes et signes cliniques'},
            'order': 30
        },
        {
            'id': str(uuid.uuid4()),
            'slug': 'biological_mechanism',
            'labels': {'en': 'Biological Mechanisms', 'fr': 'Mécanismes biologiques'},
            'description': {'en': 'Biological processes and mechanisms', 'fr': 'Processus et mécanismes biologiques'},
            'order': 40
        },
        {
            'id': str(uuid.uuid4()),
            'slug': 'treatment',
            'labels': {'en': 'Treatments', 'fr': 'Traitements'},
            'description': {'en': 'Medical treatments and interventions', 'fr': 'Traitements et interventions médicales'},
            'order': 50
        },
        {
            'id': str(uuid.uuid4()),
            'slug': 'biomarker',
            'labels': {'en': 'Biomarkers', 'fr': 'Biomarqueurs'},
            'description': {'en': 'Biological markers and indicators', 'fr': 'Marqueurs et indicateurs biologiques'},
            'order': 60
        },
        {
            'id': str(uuid.uuid4()),
            'slug': 'population',
            'labels': {'en': 'Populations', 'fr': 'Populations'},
            'description': {'en': 'Patient populations and demographics', 'fr': 'Populations de patients et démographies'},
            'order': 70
        },
        {
            'id': str(uuid.uuid4()),
            'slug': 'outcome',
            'labels': {'en': 'Outcomes', 'fr': 'Résultats'},
            'description': {'en': 'Clinical outcomes and effects', 'fr': 'Résultats cliniques et effets'},
            'order': 80
        },
        {
            'id': str(uuid.uuid4()),
            'slug': 'other',
            'labels': {'en': 'Other', 'fr': 'Autre'},
            'description': {'en': 'Other entities not fitting specific categories', 'fr': 'Autres entités ne correspondant pas aux catégories spécifiques'},
            'order': 999
        },
    ]

    # Insert categories
    import json
    connection = op.get_bind()
    for cat in categories:
        # Use CAST() instead of :: to avoid asyncpg parameter parsing issues
        connection.execute(
            text("""
                INSERT INTO ui_categories (id, slug, labels, description, "order", created_at)
                VALUES (:id, :slug, CAST(:labels AS jsonb), CAST(:description AS jsonb), :order, now())
            """),
            {
                'id': cat['id'],
                'slug': cat['slug'],
                'labels': json.dumps(cat['labels']),
                'description': json.dumps(cat['description']),
                'order': cat['order']
            }
        )


def downgrade() -> None:
    """Remove seeded categories."""
    connection = op.get_bind()

    # Delete all seeded categories by slug
    slugs = ['drug', 'disease', 'symptom', 'biological_mechanism', 'treatment',
             'biomarker', 'population', 'outcome', 'other']

    for slug in slugs:
        connection.execute(
            text("DELETE FROM ui_categories WHERE slug = :slug"),
            {'slug': slug}
        )
