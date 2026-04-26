"""add observational relation types

Revision ID: 025_add_observational_relation_types
Revises: 024_add_entity_categories
Create Date: 2026-04-26 16:15:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "025_add_observational_relation_types"
down_revision = "024_add_entity_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO relation_types (
            type_id, label, description, examples, aliases, is_active, is_system, category
        )
        VALUES
            (
                'associated_with',
                '{"en": "Associated With"}',
                'Explicit non-causal association, correlation, co-occurrence, or comorbidity',
                'dysautonomia associated_with fibromyalgia',
                '["correlates_with", "related_to", "linked_to", "comorbid_with"]',
                true,
                true,
                'observational'
            ),
            (
                'prevalence_in',
                '{"en": "Prevalence In"}',
                'Source-stated prevalence or incidence of a phenomenon within a population or condition',
                'dysautonomia prevalence_in chronic-musculoskeletal-pain',
                '["prevalence_of", "incidence_in", "prevalent_in"]',
                true,
                true,
                'observational'
            )
        ON CONFLICT (type_id) DO UPDATE
        SET
            label = EXCLUDED.label,
            description = EXCLUDED.description,
            examples = EXCLUDED.examples,
            aliases = EXCLUDED.aliases,
            is_active = true,
            is_system = true,
            category = EXCLUDED.category
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE relation_revisions
        SET kind = 'other'
        WHERE kind IN ('associated_with', 'prevalence_in')
        """
    )
    op.execute(
        """
        UPDATE staged_extractions
        SET extraction_data = jsonb_set(extraction_data, '{relation_type}', '"other"')
        WHERE extraction_type = 'relation'
          AND extraction_data->>'relation_type' IN ('associated_with', 'prevalence_in')
        """
    )
    op.execute(
        """
        DELETE FROM relation_types
        WHERE type_id IN ('associated_with', 'prevalence_in')
        """
    )
