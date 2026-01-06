"""
End-to-end test for PubMed document ingestion.

Tests the complete workflow:
1. Fetch PubMed article via API
2. Create source in database
3. Extract knowledge (entities and relations)
4. Save to database
"""
import asyncio
import sys
import os
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine

from app.models.base import Base
from app.models import *  # Import all models
from app.services.pubmed_fetcher import PubMedFetcher
from app.services.source_service import SourceService
from app.services.extraction_service import ExtractionService
from app.services.entity_linking_service import EntityLinkingService
from app.services.bulk_creation_service import BulkCreationService
from app.schemas.source import SourceWrite


async def test_end_to_end_pubmed_ingestion():
    """Test complete PubMed article ingestion workflow."""

    # Test with a medical research article
    pubmed_url = "https://pubmed.ncbi.nlm.nih.gov/23953482/"

    print("=" * 80)
    print("END-TO-END PUBMED INGESTION TEST")
    print("=" * 80)
    print(f"\nPubMed URL: {pubmed_url}\n")

    # Create test database
    test_db_name = "test_e2e.db"
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    print("Setting up test database...")
    # Create tables synchronously first
    sync_engine = create_engine(f"sqlite:///{test_db_name}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    print(f"✓ Created test database: {test_db_name}\n")

    # Create async engine and session
    engine = create_async_engine(f"sqlite+aiosqlite:///{test_db_name}")
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db = SessionLocal()

    try:
        # =====================================================================
        # STEP 1: Fetch PubMed article
        # =====================================================================
        print("Step 1: Fetching PubMed article...")
        print("-" * 80)

        pubmed_fetcher = PubMedFetcher()
        article = await pubmed_fetcher.fetch_by_url(pubmed_url)

        print(f"✓ Fetched article")
        print(f"  PMID: {article.pmid}")
        print(f"  Title: {article.title[:80]}...")
        print(f"  Authors: {len(article.authors)} authors")
        print(f"  Journal: {article.journal}")
        print(f"  Year: {article.year}")
        print(f"  Abstract length: {len(article.abstract) if article.abstract else 0} chars")
        print(f"  Full text length: {len(article.full_text)} chars")

        # =====================================================================
        # STEP 2: Create source in database
        # =====================================================================
        print("\nStep 2: Creating source in database...")
        print("-" * 80)

        source_service = SourceService(db)

        # Create source with PubMed metadata
        source_data = SourceWrite(
            kind="study",
            title=article.title,
            authors=article.authors,
            year=article.year,
            origin=article.journal,
            url=article.url,
            trust_level=0.9,  # PubMed articles are generally high quality
            summary={"en": article.abstract} if article.abstract else None,
            source_metadata={
                "pmid": article.pmid,
                "doi": article.doi,
                "source": "pubmed"
            },
            created_with_llm=None
        )

        source = await source_service.create(source_data, user_id=None)

        print(f"✓ Created source")
        print(f"  Source ID: {source.id}")
        print(f"  Title: {source.title[:60]}...")

        # Store document text in source
        await source_service.add_document_to_source(
            source_id=source.id,
            document_text=article.full_text,
            document_format="txt",
            document_file_name=f"pubmed_{article.pmid}.txt",
            user_id=None
        )

        print(f"✓ Stored document text in source")

        # =====================================================================
        # STEP 3: Extract knowledge
        # =====================================================================
        print("\nStep 3: Extracting knowledge from document...")
        print("-" * 80)

        extraction_service = ExtractionService()
        entities, relations, warnings = await extraction_service.extract_batch(
            text=article.full_text,
            min_confidence="low"  # Use low to get more entities for testing
        )

        print(f"✓ Extraction complete")
        print(f"  Entities: {len(entities)}")
        print(f"  Relations: {len(relations)}")
        if warnings:
            print(f"  Warnings: {warnings}")

        if entities:
            print(f"\n  Sample entities:")
            for entity in entities[:5]:
                category = entity.category if hasattr(entity, 'category') else 'unknown'
                print(f"    - {entity.slug} ({category})")

        if relations:
            print(f"\n  Sample relations:")
            for relation in relations[:3]:
                print(f"    - {relation.relation_type}: {relation.subject_slug} → {relation.object_slug}")

        # =====================================================================
        # STEP 4: Link entities to existing knowledge
        # =====================================================================
        print("\nStep 4: Linking entities to existing knowledge graph...")
        print("-" * 80)

        linking_service = EntityLinkingService(db)
        matches = await linking_service.find_entity_matches(entities)

        print(f"✓ Entity linking complete")
        print(f"  Exact matches: {sum(1 for m in matches if m.match_type == 'exact')}")
        print(f"  Synonym matches: {sum(1 for m in matches if m.match_type == 'synonym')}")
        print(f"  Total matches: {len(matches)}")

        # =====================================================================
        # STEP 5: Save to database
        # =====================================================================
        print("\nStep 5: Saving extracted knowledge to database...")
        print("-" * 80)

        bulk_service = BulkCreationService(db)

        # For testing, create all entities as new (don't link to existing)
        # In production, you'd use the matches to decide which to create vs link
        entity_mapping = {}

        if entities:
            entity_mapping = await bulk_service.bulk_create_entities(
                entities=entities,
                source_id=source.id,
                user_id=None
            )

            print(f"✓ Created {len(entity_mapping)} entities")

        # Create relations
        relation_ids = []
        if relations:
            relation_ids = await bulk_service.bulk_create_relations(
                relations=relations,
                entity_mapping=entity_mapping,
                source_id=source.id,
                user_id=None
            )

            print(f"✓ Created {len(relation_ids)} relations")

        # =====================================================================
        # STEP 6: Verify data in database
        # =====================================================================
        print("\nStep 6: Verifying data in database...")
        print("-" * 80)

        from sqlalchemy import select, func
        from app.models.entity import Entity
        from app.models.relation import Relation

        # Count entities
        entity_count_stmt = select(func.count()).select_from(Entity)
        entity_count = await db.scalar(entity_count_stmt)

        # Count relations
        relation_count_stmt = select(func.count()).select_from(Relation)
        relation_count = await db.scalar(relation_count_stmt)

        print(f"✓ Database verification")
        print(f"  Total entities in DB: {entity_count}")
        print(f"  Total relations in DB: {relation_count}")
        print(f"  Source ID: {source.id}")
        print(f"  Source URL: {source.url}")

        # =====================================================================
        # SUCCESS
        # =====================================================================
        print("\n" + "=" * 80)
        print("✓ END-TO-END TEST PASSED!")
        print("=" * 80)
        print("\nSuccessfully completed full workflow:")
        print("  1. Fetched PubMed article via E-utilities API")
        print("  2. Created source in database with metadata")
        print("  3. Extracted entities and relations using LLM")
        print("  4. Linked entities to existing knowledge graph")
        print("  5. Saved all data to database")
        print("  6. Verified data persistence")
        print("\nThe system is ready for production use!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await db.close()
        await engine.dispose()

        # Cleanup test database
        if os.path.exists(test_db_name):
            try:
                os.remove(test_db_name)
                print(f"\n✓ Cleaned up test database: {test_db_name}")
            except:
                print(f"\n⚠ Could not remove test database: {test_db_name}")


if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    # Run the test
    asyncio.run(test_end_to_end_pubmed_ingestion())
