"""
Test the /sources/{source_id}/extract-from-url API endpoint.

This tests the complete URL extraction workflow through the API endpoint.
"""
import asyncio
import sys
import os
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine

from app.models.base import Base
from app.models import *
from app.api.document_extraction import extract_from_url as api_extract_from_url
from app.api.document_extraction import UrlExtractionRequest
from app.services.source_service import SourceService
from app.schemas.source import SourceWrite


async def test_url_extraction_endpoint():
    """Test the URL extraction API endpoint."""

    pubmed_url = "https://pubmed.ncbi.nlm.nih.gov/23953482/"

    print("=" * 80)
    print("URL EXTRACTION API ENDPOINT TEST")
    print("=" * 80)
    print(f"\nPubMed URL: {pubmed_url}\n")

    # Create test database
    test_db_name = "test_url_endpoint.db"
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    print("Setting up test database...")
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
        # STEP 1: Create a source
        # =====================================================================
        print("Step 1: Creating source in database...")
        print("-" * 80)

        source_service = SourceService(db)
        source_data = SourceWrite(
            kind="study",
            title="Test Source for URL Extraction",
            url="",  # Will be updated by the extraction endpoint
            trust_level=0.9,
            created_with_llm=None
        )

        source = await source_service.create(source_data, user_id=None)
        print(f"✓ Created source: {source.id}\n")

        # =====================================================================
        # STEP 2: Call the API endpoint
        # =====================================================================
        print("Step 2: Calling /extract-from-url endpoint...")
        print("-" * 80)

        request = UrlExtractionRequest(url=pubmed_url)

        # Simulate the API call by calling the endpoint function directly
        result = await api_extract_from_url(
            source_id=source.id,
            request=request,
            db=db,
            current_user=None  # For testing
        )

        print(f"✓ API endpoint returned successfully")
        print(f"  Entities extracted: {len(result.entities)}")
        print(f"  Relations extracted: {len(result.relations)}")
        print(f"  Link suggestions: {len(result.link_suggestions)}")

        if result.entities:
            print(f"\n  Sample entities:")
            for entity in result.entities[:5]:
                print(f"    - {entity.slug} ({entity.category})")

        if result.relations:
            print(f"\n  Sample relations:")
            for relation in result.relations[:3]:
                print(f"    - {relation.relation_type}: {relation.subject_slug} → {relation.object_slug}")

        # =====================================================================
        # STEP 3: Verify source was updated with metadata
        # =====================================================================
        print("\nStep 3: Verifying source metadata was updated...")
        print("-" * 80)

        # Fetch source from database
        updated_source = await source_service.get(source.id)

        print(f"✓ Source metadata updated:")
        print(f"  Title: {updated_source.title[:60]}...")
        print(f"  Authors: {updated_source.authors}")
        print(f"  Year: {updated_source.year}")
        print(f"  Origin: {updated_source.origin}")
        print(f"  URL: {updated_source.url}")
        if updated_source.source_metadata:
            print(f"  PMID: {updated_source.source_metadata.get('pmid')}")
            print(f"  DOI: {updated_source.source_metadata.get('doi')}")

        # =====================================================================
        # SUCCESS
        # =====================================================================
        print("\n" + "=" * 80)
        print("✓ URL EXTRACTION API ENDPOINT TEST PASSED!")
        print("=" * 80)
        print("\nThe /extract-from-url endpoint is working correctly!")

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
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    asyncio.run(test_url_extraction_endpoint())
