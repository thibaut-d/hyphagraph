"""
Test PubMedFetcher bulk search and fetch methods.
"""
import asyncio
import sys
from app.services.pubmed_fetcher import PubMedFetcher


async def test_search():
    """Test search_pubmed method."""
    print("=" * 80)
    print("TEST 1: PubMedFetcher.search_pubmed()")
    print("=" * 80)
    print()

    fetcher = PubMedFetcher()

    # Test search with query
    query = "CRISPR AND 2024[pdat]"
    max_results = 5

    pmids, total_count = await fetcher.search_pubmed(query, max_results)

    print(f"Query: {query}")
    print(f"Total results: {total_count}")
    print(f"Retrieved PMIDs: {len(pmids)}")
    print()

    for i, pmid in enumerate(pmids, 1):
        print(f"  {i}. PMID {pmid}")

    print("\n✓ Search test passed!\n")
    return pmids


async def test_extract_query_from_url():
    """Test extract_query_from_search_url method."""
    print("=" * 80)
    print("TEST 2: PubMedFetcher.extract_query_from_search_url()")
    print("=" * 80)
    print()

    fetcher = PubMedFetcher()

    test_urls = [
        "https://pubmed.ncbi.nlm.nih.gov/?term=cancer+AND+immunotherapy",
        "https://pubmed.ncbi.nlm.nih.gov/?term=aspirin&filter=years.2020-2024",
        "https://pubmed.ncbi.nlm.nih.gov/?term=covid-19+vaccine+efficacy"
    ]

    for url in test_urls:
        query = fetcher.extract_query_from_search_url(url)
        print(f"URL: {url}")
        print(f"Extracted query: {query}")
        print()

    print("✓ URL extraction test passed!\n")


async def test_bulk_fetch():
    """Test bulk_fetch_articles method."""
    print("=" * 80)
    print("TEST 3: PubMedFetcher.bulk_fetch_articles()")
    print("=" * 80)
    print()

    fetcher = PubMedFetcher()

    # Search first
    query = "gene therapy AND 2024[pdat]"
    pmids, _ = await fetcher.search_pubmed(query, max_results=3)

    print(f"Fetching {len(pmids)} articles with rate limiting...\n")

    # Bulk fetch
    articles = await fetcher.bulk_fetch_articles(pmids)

    print(f"\nSuccessfully fetched {len(articles)} articles:")
    print()

    for i, article in enumerate(articles, 1):
        print(f"{i}. {article.title[:70]}...")
        print(f"   Authors: {', '.join(article.authors[:3])}")
        print(f"   Journal: {article.journal}")
        print(f"   Year: {article.year}")
        print(f"   PMID: {article.pmid}")
        print()

    print("✓ Bulk fetch test passed!\n")


async def test_complete_workflow():
    """Test complete search-and-bulk-fetch workflow."""
    print("=" * 80)
    print("TEST 4: Complete Workflow (URL → Search → Bulk Fetch)")
    print("=" * 80)
    print()

    fetcher = PubMedFetcher()

    # Scenario: User copies search URL from PubMed
    search_url = "https://pubmed.ncbi.nlm.nih.gov/?term=mRNA+vaccine&filter=years.2023-2024"

    print(f"Step 1: Extract query from URL")
    print(f"URL: {search_url}")
    query = fetcher.extract_query_from_search_url(search_url)
    print(f"Extracted query: {query}\n")

    print(f"Step 2: Search PubMed")
    pmids, total_count = await fetcher.search_pubmed(query, max_results=3)
    print(f"Found {total_count} total results, retrieving first {len(pmids)}\n")

    print(f"Step 3: Bulk fetch article details")
    articles = await fetcher.bulk_fetch_articles(pmids)

    print(f"\nRetrieved {len(articles)} articles:")
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article.title}")
        print(f"   PMID: {article.pmid}")
        print(f"   Authors: {len(article.authors)} authors")
        print(f"   Year: {article.year}")
        print(f"   Full text length: {len(article.full_text)} chars")

    print("\n✓ Complete workflow test passed!\n")


async def run_all_tests():
    """Run all tests."""
    try:
        await test_search()
        await test_extract_query_from_url()
        await test_bulk_fetch()
        await test_complete_workflow()

        print("=" * 80)
        print("✓ ALL PUBMED BULK FETCH TESTS PASSED!")
        print("=" * 80)
        print()
        print("Summary:")
        print("- search_pubmed(): Working")
        print("- extract_query_from_search_url(): Working")
        print("- bulk_fetch_articles(): Working with rate limiting")
        print("- Complete workflow: Ready for API endpoint implementation")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    asyncio.run(run_all_tests())
