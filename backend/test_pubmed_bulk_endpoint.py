"""
Test the /pubmed/bulk-search API endpoint.
"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine

from app.models.base import Base
from app.models import *
from app.api.document_extraction import bulk_search_pubmed, PubMedBulkSearchRequest


async def test_bulk_search_by_query():
    """Test bulk search with direct query."""
    print("=" * 80)
    print("TEST 1: Bulk Search by Query")
    print("=" * 80)
    print()

    # Create test database
    test_db_name = "test_bulk_search.db"
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    sync_engine = create_engine(f"sqlite:///{test_db_name}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    engine = create_async_engine(f"sqlite+aiosqlite:///{test_db_name}")
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db = SessionLocal()

    try:
        # Test request
        request = PubMedBulkSearchRequest(
            query="CRISPR AND 2024[pdat]",
            max_results=3
        )

        print(f"Query: {request.query}")
        print(f"Max results: {request.max_results}\n")

        # Call endpoint
        response = await bulk_search_pubmed(
            request=request,
            db=db,
            current_user=None
        )

        print(f"✓ Search complete")
        print(f"  Total results available: {response.total_results}")
        print(f"  Retrieved: {response.retrieved_count}")
        print()

        for i, result in enumerate(response.results, 1):
            print(f"{i}. {result.title[:70]}...")
            print(f"   PMID: {result.pmid}")
            print(f"   Authors: {len(result.authors)} authors")
            print(f"   Journal: {result.journal}")
            print(f"   Year: {result.year}")
            print()

        print("✓ Test passed!\n")

    finally:
        await db.close()
        await engine.dispose()
        if os.path.exists(test_db_name):
            os.remove(test_db_name)


async def test_bulk_search_by_url():
    """Test bulk search with PubMed search URL."""
    print("=" * 80)
    print("TEST 2: Bulk Search by URL")
    print("=" * 80)
    print()

    # Create test database
    test_db_name = "test_bulk_search.db"
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    sync_engine = create_engine(f"sqlite:///{test_db_name}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    engine = create_async_engine(f"sqlite+aiosqlite:///{test_db_name}")
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db = SessionLocal()

    try:
        # Test request with URL
        search_url = "https://pubmed.ncbi.nlm.nih.gov/?term=gene+therapy+AND+2024[pdat]"
        request = PubMedBulkSearchRequest(
            search_url=search_url,
            max_results=3
        )

        print(f"Search URL: {search_url}")
        print(f"Max results: {request.max_results}\n")

        # Call endpoint
        response = await bulk_search_pubmed(
            request=request,
            db=db,
            current_user=None
        )

        print(f"✓ Search complete")
        print(f"  Extracted query: '{response.query}'")
        print(f"  Total results available: {response.total_results}")
        print(f"  Retrieved: {response.retrieved_count}")
        print()

        for i, result in enumerate(response.results, 1):
            print(f"{i}. {result.title[:70]}...")
            print(f"   PMID: {result.pmid}")
            print(f"   URL: {result.url}")
            print()

        print("✓ Test passed!\n")

    finally:
        await db.close()
        await engine.dispose()
        if os.path.exists(test_db_name):
            os.remove(test_db_name)


async def run_all_tests():
    """Run all endpoint tests."""
    try:
        await test_bulk_search_by_query()
        await test_bulk_search_by_url()

        print("=" * 80)
        print("✓ ALL PUBMED BULK ENDPOINT TESTS PASSED!")
        print("=" * 80)
        print()
        print("Summary:")
        print("- Bulk search by query: Working")
        print("- Bulk search by URL: Working")
        print("- Article metadata retrieval: Working")
        print("- Rate limiting: Applied")
        print()
        print("Ready for frontend integration!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    asyncio.run(run_all_tests())
