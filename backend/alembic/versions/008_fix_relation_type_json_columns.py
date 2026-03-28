"""Convert relation_types text columns to JSONB for native JSON storage

label and aliases were stored as Text with manual json.dumps/loads in the
service layer. Switching to JSONB removes that indirection and ensures the
DB enforces valid JSON.

The data migration casts each column's current text value to JSONB; rows
that already contain valid JSON will convert transparently.

Revision ID: 008_fix_rel_type_json_cols
Revises: 007_add_entity_merge_indexes
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "008_fix_rel_type_json_cols"
down_revision = "007_add_entity_merge_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cast existing text values to JSONB using USING clause
    op.execute(
        "ALTER TABLE relation_types "
        "ALTER COLUMN label TYPE JSONB USING label::jsonb"
    )
    op.execute(
        "ALTER TABLE relation_types "
        "ALTER COLUMN description TYPE JSONB USING to_jsonb(description)"
    )
    op.execute(
        "ALTER TABLE relation_types "
        "ALTER COLUMN examples TYPE JSONB USING to_jsonb(examples)"
    )
    op.execute(
        "ALTER TABLE relation_types "
        "ALTER COLUMN aliases TYPE JSONB USING aliases::jsonb"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE relation_types "
        "ALTER COLUMN label TYPE TEXT USING label::text"
    )
    op.execute(
        "ALTER TABLE relation_types "
        "ALTER COLUMN description TYPE TEXT USING description#>>'{}'"
    )
    op.execute(
        "ALTER TABLE relation_types "
        "ALTER COLUMN examples TYPE TEXT USING examples#>>'{}'"
    )
    op.execute(
        "ALTER TABLE relation_types "
        "ALTER COLUMN aliases TYPE TEXT USING aliases::text"
    )
