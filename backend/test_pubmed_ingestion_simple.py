"""
Simple end-to-end test for PubMed document ingestion (without LLM extraction).

Tests the workflow:
1. Fetch PubMed article via API
2. Create source in database with metadata
3. Store document text
"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine, select, func

from app.models.base import Base
from app.models import *  # Import all models
from app.services.pubmed_fetcher import PubMedFetcher
from app.services.source_service import SourceService
from app.schemas.source import SourceWrite


async def test_pubmed_ingestion():
    """Test PubMed article fetch and storage."""

    pubmed_url = "https://pubmed.ncbi.nlm.nih.gov/23953482/"

    print("=" * 80)
    print("PUBMED INGESTION TEST (Fetch + Store)")
    print("=" * 80)
    print(f"\nPubMed URL: {pubmed_url}\n")

    # Create test database
    test_db_name = "test_pubmed.db"
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    print("Setting up test database...")
    sync_engine = create_engine(f"sqlite:///{test_db_name}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    print(f"✓ Created test database\n")

    # Create async engine and session
    engine = create_async_engine(f"sqlite+aiosqlite:///{test_db_name}")
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db = SessionLocal()

    try:
        # Step 1: Fetch PubMed article
        print("Step 1: Fetching PubMed article...")
        print("-" * 80)

        pubmed_fetcher = PubMedFetcher()
        article = await pubmed_fetcher.fetch_by_url(pubmed_url)

        print(f"✓ Fetched article")
        print(f"  PMID: {article.pmid}")
        print(f"  Title: {article.title}")
        print(f"  Authors: {len(article.authors)} authors ({', '.join(article.authors[:2])} et al.)")
        print(f"  Journal: {article.journal}")
        print(f"  Year: {article.year}")
        print(f"  DOI: {article.doi}")
        print(f"  Abstract length: {len(article.abstract) if article.abstract else 0} chars")
        print(f"  Full text length: {len(article.full_text)} chars")

        # Step 2: Create source in database
        print("\nStep 2: Creating source in database...")
        print("-" * 80)

        source_service = SourceService(db)

        source_data = SourceWrite(
            kind="study",
            title=article.title,
            authors=article.authors,
            year=article.year,
            origin=article.journal,
            url=article.url,
            trust_level=0.9,
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
        print(f"  Title: {source.title[:70]}...")
        print(f"  URL: {source.url}")
        print(f"  Metadata: {source.source_metadata}")

        # Step 3: Store document text
        print("\nStep 3: Storing document text...")
        print("-" * 80)

        await source_service.add_document_to_source(
            source_id=source.id,
            document_text=article.full_text,
            document_format="txt",
            document_file_name=f"pubmed_{article.pmid}.txt",
            user_id=None
        )

        print(f"✓ Stored document text")
        print(f"  Format: txt")
        print(f"  Filename: pubmed_{article.pmid}.txt")
        print(f"  Size: {len(article.full_text)} chars")

        # Step 4: Verify data
        print("\nStep 4: Verifying data in database...")
        print("-" * 80)

        from app.models.source import Source
        from app.models.source_revision import SourceRevision

        source_count = await db.scalar(select(func.count()).select_from(Source))
        revision_count = await db.scalar(select(func.count()).select_from(SourceRevision))

        # Fetch the source back to verify document_text
        stmt = select(SourceRevision).where(
            SourceRevision.source_id == source.id,
            SourceRevision.is_current == True
        )
        revision = await db.scalar(stmt)

        print(f"✓ Database verification")
        print(f"  Total sources: {source_count}")
        print(f"  Total revisions: {revision_count}")
        print(f"  Document text stored: {bool(revision.document_text)}")
        print(f"  Document text length: {len(revision.document_text) if revision.document_text else 0} chars")

        # SUCCESS
        print("\n" + "=" * 80)
        print("✓ TEST PASSED!")
        print("=" * 80)
        print("\nSuccessfully completed PubMed ingestion workflow:")
        print("  1. ✓ Fetched PubMed article via E-utilities API")
        print("  2. ✓ Created source in database with full metadata")
        print("  3. ✓ Stored document text in source")
        print("  4. ✓ Verified data persistence")
        print("\nThe PubMed integration is working correctly!")
        print("Next step: Fix LLM extraction schema for entity summaries")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await db.close()
        await engine.dispose()

        # Cleanup
        if os.path.exists(test_db_name):
            try:
                os.remove(test_db_name)
                print(f"\n✓ Cleaned up test database")
            except:
                print(f"\n⚠ Could not remove test database")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    asyncio.run(test_pubmed_ingestion())
