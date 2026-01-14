"""
Script to merge fibromyalgia duplicate entities.

Merges:
- fibromyalgia-syndrome → fibromyalgia
- Moves all relations
- Adds 'fibromyalgia-syndrome' as term to fibromyalgia entity
"""
import asyncio
import sys

sys.path.insert(0, '.')

from app.database import AsyncSessionLocal
from app.services.entity_merge_service import EntityMergeService
from sqlalchemy import select
from app.models.entity_revision import EntityRevision


async def merge_fibromyalgia():
    """Merge fibromyalgia duplicate entities."""

    async with AsyncSessionLocal() as db:
        print("=" * 80)
        print("MERGING FIBROMYALGIA DUPLICATES")
        print("=" * 80)
        print()

        # Find fibromyalgia entities
        stmt = select(EntityRevision).where(
            EntityRevision.slug.in_(['fibromyalgia', 'fibromyalgia-syndrome']),
            EntityRevision.is_current == True
        )
        result = await db.execute(stmt)
        entities = {rev.slug: rev.entity_id for rev in result.scalars()}

        print(f"Found entities:")
        for slug, entity_id in entities.items():
            print(f"  - {slug}: {entity_id}")
        print()

        if 'fibromyalgia' not in entities:
            print("❌ fibromyalgia entity not found")
            return

        if 'fibromyalgia-syndrome' not in entities:
            print("ℹ️  fibromyalgia-syndrome not found (nothing to merge)")
            return

        # Merge syndrome into main
        merge_service = EntityMergeService(db)

        print(f"Merging 'fibromyalgia-syndrome' into 'fibromyalgia'...")
        result = await merge_service.merge_entities(
            source_entity_id=entities['fibromyalgia-syndrome'],
            target_entity_id=entities['fibromyalgia'],
            preserve_source_slug_as_term=True
        )

        print()
        print("✅ Merge complete!")
        print(f"  Relations moved: {result['relations_moved']}")
        print(f"  Term added: {result['term_added']}")
        print(f"  Target slug: {result['target_slug']}")
        print()
        print("'fibromyalgia' now includes all relations from 'fibromyalgia-syndrome'")
        print("'fibromyalgia-syndrome' is searchable as a term of fibromyalgia")


if __name__ == "__main__":
    asyncio.run(merge_fibromyalgia())
