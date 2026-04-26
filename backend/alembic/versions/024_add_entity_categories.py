"""Add entity_categories table with built-in seed data

Revision ID: 024
Revises: 023_rm_legacy_claim_extractions
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
import json

revision = "024"
down_revision = "023_rm_legacy_claim_extractions"
branch_labels = None
depends_on = None

_SEED = [
    {
        "category_id": "drug",
        "label": {"en": "Drug", "fr": "Médicament"},
        "description": "A pharmacological substance used for treatment, prevention, or diagnosis. Includes small molecules, biologics, and supplements.",
        "examples": "aspirin, metformin, adalimumab, vitamin D",
    },
    {
        "category_id": "disease",
        "label": {"en": "Disease", "fr": "Maladie"},
        "description": "A medical condition, disorder, or pathology with defined clinical features. Includes syndromes, infections, and chronic conditions.",
        "examples": "type 2 diabetes, rheumatoid arthritis, major depressive disorder",
    },
    {
        "category_id": "symptom",
        "label": {"en": "Symptom", "fr": "Symptôme"},
        "description": "A subjective or objective clinical sign reported by patients or observed by clinicians. Distinct from a diagnosed disease.",
        "examples": "fatigue, pain, dyspnea, nausea",
    },
    {
        "category_id": "biological_mechanism",
        "label": {"en": "Biological Mechanism", "fr": "Mécanisme Biologique"},
        "description": "A molecular, cellular, or physiological process that mediates a biological effect. Includes pathways, receptors, and enzymes.",
        "examples": "COX-2 inhibition, NF-κB signalling, apoptosis, oxidative stress",
    },
    {
        "category_id": "treatment",
        "label": {"en": "Treatment", "fr": "Traitement"},
        "description": "A non-pharmacological intervention, procedure, or therapy. Use 'drug' for pharmacological agents.",
        "examples": "cognitive behavioural therapy, surgery, radiation therapy, acupuncture",
    },
    {
        "category_id": "biomarker",
        "label": {"en": "Biomarker", "fr": "Biomarqueur"},
        "description": "A measurable biological indicator used for diagnosis, prognosis, or monitoring. Includes lab values and imaging findings.",
        "examples": "HbA1c, CRP, TNF-alpha, LVEF on echocardiogram",
    },
    {
        "category_id": "population",
        "label": {"en": "Population", "fr": "Population"},
        "description": "A defined group of patients or subjects characterised by demographics, disease status, or study criteria.",
        "examples": "elderly patients, postmenopausal women, treatment-naive HIV patients",
    },
    {
        "category_id": "outcome",
        "label": {"en": "Outcome", "fr": "Résultat"},
        "description": "A measured endpoint or result assessed in a study. Includes clinical outcomes, quality-of-life measures, and safety endpoints.",
        "examples": "all-cause mortality, WOMAC pain score, hospitalisation rate",
    },
    {
        "category_id": "other",
        "label": {"en": "Other", "fr": "Autre"},
        "description": "An entity that does not clearly fit any of the above categories. Use sparingly.",
        "examples": None,
    },
]


def upgrade() -> None:
    op.create_table(
        "entity_categories",
        sa.Column("category_id", sa.String(50), primary_key=True),
        sa.Column("label", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("examples", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_entity_category_active", "entity_categories", ["is_active"])

    # Seed built-in categories
    entity_categories = sa.table(
        "entity_categories",
        sa.column("category_id", sa.String),
        sa.column("label", sa.JSON),
        sa.column("description", sa.String),
        sa.column("examples", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("is_system", sa.Boolean),
        sa.column("usage_count", sa.Integer),
    )
    op.bulk_insert(
        entity_categories,
        [
            {
                "category_id": row["category_id"],
                "label": row["label"],
                "description": row["description"],
                "examples": row["examples"],
                "is_active": True,
                "is_system": True,
                "usage_count": 0,
            }
            for row in _SEED
        ],
    )


def downgrade() -> None:
    op.drop_index("idx_entity_category_active", table_name="entity_categories")
    op.drop_table("entity_categories")
