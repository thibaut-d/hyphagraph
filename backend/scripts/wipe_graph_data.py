"""
Wipe all knowledge graph data while preserving users, sessions, and seed data.

Safe to run repeatedly during development and testing. Leaves intact:
  - users, refresh_tokens          (accounts and sessions)
  - relation_types, semantic_role_types, ui_categories  (migration-seeded config)
  - alembic_version                (schema state)

Wipes:
  - entities and all their terms, revisions, and merge records
  - relations and all their revisions and role revisions
  - sources and their revisions
  - staged_extractions
  - computed_relations
  - audit_logs
  - bug_reports

Usage:
  uv run python scripts/wipe_graph_data.py          # prompts for confirmation
  uv run python scripts/wipe_graph_data.py --yes    # skips confirmation
"""

import asyncio
import sys

from sqlalchemy import text

sys.path.insert(0, "/app")
from app.database import AsyncSessionLocal


# Truncated in dependency order so foreign-key constraints are satisfied.
# CASCADE handles any remaining cross-table references automatically.
WIPE_TABLES = [
    "computed_relations",
    "staged_extractions",
    "entity_merge_records",
    "relation_role_revisions",
    "relation_revisions",
    "source_revisions",
    "entity_revisions",
    "entity_terms",
    "relations",
    "entities",
    "sources",
    "audit_logs",
    "bug_reports",
]

KEEP_TABLES = [
    "users",
    "refresh_tokens",
    "relation_types",
    "semantic_role_types",
    "ui_categories",
    "alembic_version",
]


async def wipe(skip_confirm: bool = False) -> None:
    if not skip_confirm:
        print("Tables that will be WIPED:")
        for t in WIPE_TABLES:
            print(f"  - {t}")
        print("\nTables that will be KEPT:")
        for t in KEEP_TABLES:
            print(f"  - {t}")
        print()
        answer = input("Wipe all knowledge graph data? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    async with AsyncSessionLocal() as db:
        tables = ", ".join(WIPE_TABLES)
        await db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        await db.commit()

        # Print confirmation counts
        print("\nPost-wipe counts:")
        for table in WIPE_TABLES:
            row = await db.execute(text(f"SELECT count(*) FROM {table}"))
            count = row.scalar()
            print(f"  {table}: {count}")

        row = await db.execute(text("SELECT count(*) FROM users"))
        print(f"\n  users (preserved): {row.scalar()}")

    print("\nGraph data wiped. Users and seed data preserved.")


if __name__ == "__main__":
    skip_confirm = "--yes" in sys.argv
    asyncio.run(wipe(skip_confirm=skip_confirm))
