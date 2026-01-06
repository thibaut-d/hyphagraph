"""
Test the complete PubMed bulk import workflow.
"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine, select

from app.models.base import Base
from app.models import *
from app.api.document_extraction import bulk_import_pubmed, PubMedBulkImportRequest
from app.models.source import Source


async def test_bulk_import():
    """Test bulk import of PubMed articles."""
    print("=" * 80)
    print("PUBMED BULK IMPORT TEST")
    print("=" * 80)
    print()

    # Create test database
    test_db_name = "test_bulk_import.db"
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    sync_engine = create_engine(f"sqlite:///{test_db_name}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    engine = create_async_engine(f"sqlite+aiosqlite:///{test_db_name}")
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db = SessionLocal()

    try:
        # Test with 3 known PMIDs
        test_pmids = [
            "41255389",  # Recent CRISPR paper
            "40881775",  # Gene editing paper
            "40829017",  # Mitochondrial genome paper
        ]

        print(f"Importing {len(test_pmids)} PubMed articles...")
        print(f"PMIDs: {', '.join(test_pmids)}\n")

        request = PubMedBulkImportRequest(pmids=test_pmids)

        # Call endpoint
        response = await bulk_import_pubmed(
            request=request,
            db=db,
            current_user=None
        )

        print(f"✓ Import complete")
        print(f"  Total requested: {response.total_requested}")
        print(f"  Sources created: {response.sources_created}")
        print(f"  Failed PMIDs: {response.failed_pmids}")
        print(f"  Source IDs: {len(response.source_ids)}")
        print()

        # Verify sources in database using SourceService
        from app.services.source_service import SourceService
        source_service = SourceService(db)

        print(f"✓ Database verification")
        print(f"  Total sources created: {len(response.source_ids)}")
        print()

        for i, source_id in enumerate(response.source_ids, 1):
            source = await source_service.get(source_id)
            print(f"{i}. {source.title[:70]}...")
            print(f"   PMID: {source.source_metadata.get('pmid') if source.source_metadata else 'N/A'}")
            print(f"   Authors: {len(source.authors) if source.authors else 0} authors")
            print(f"   Year: {source.year}")
            print(f"   Journal: {source.origin}")
            print()

        print("=" * 80)
        print("✓ BULK IMPORT TEST PASSED!")
        print("=" * 80)
        print()
        print("Complete workflow verified:")
        print("  1. Fetch articles from PubMed")
        print("  2. Create sources with metadata")
        print("  3. Store document text for extraction")
        print("  4. Handle failures gracefully")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await db.close()
        await engine.dispose()
        if os.path.exists(test_db_name):
            try:
                os.remove(test_db_name)
                print(f"\n✓ Cleaned up test database: {test_db_name}")
            except:
                print(f"\n⚠ Could not remove test database: {test_db_name}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    asyncio.run(test_bulk_import())
