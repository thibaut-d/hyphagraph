"""add pg_trgm GIN indexes for substring search

Revision ID: 019_add_trgm_indexes
Revises: 018_add_role_confidence
Create Date: 2026-04-05

Adds GIN trigram indexes on the columns used by substring search (.contains()
queries) so table scans are replaced by fast index lookups.

PostgreSQL only — skipped on other dialects (e.g. SQLite for tests).
CREATE INDEX CONCURRENTLY runs outside the implicit transaction block.
"""
from alembic import op

revision = "019_add_trgm_indexes"
down_revision = "018_add_role_confidence"
branch_labels = None
depends_on = None

_INDEXES = [
    ("ix_er_slug_trgm",    "entity_revisions",   "slug gin_trgm_ops"),
    ("ix_er_summary_trgm", "entity_revisions",   "(summary::text) gin_trgm_ops"),
    ("ix_sr_title_trgm",   "source_revisions",   "title gin_trgm_ops"),
    ("ix_sr_authors_trgm", "source_revisions",   "(authors::text) gin_trgm_ops"),
    ("ix_sr_origin_trgm",  "source_revisions",   "origin gin_trgm_ops"),
    ("ix_et_term_trgm",    "entity_terms",        "term gin_trgm_ops"),
    ("ix_rr_kind_trgm",    "relation_revisions",  "kind gin_trgm_ops"),
]


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        for idx_name, table, expr in _INDEXES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {idx_name} "
                f"ON {table} USING GIN ({expr})"
            )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    with op.get_context().autocommit_block():
        for idx_name, _, _ in reversed(_INDEXES):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {idx_name}")
