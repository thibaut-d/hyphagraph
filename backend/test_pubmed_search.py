"""
Test PubMed search API (esearch) functionality.

This script demonstrates:
1. Searching PubMed with a query string
2. Extracting query from PubMed search URL
3. Retrieving multiple PMIDs from search results
4. Fetching article details for each PMID
"""
import asyncio
import sys
import re
from urllib.parse import urlparse, parse_qs
import httpx
import xml.etree.ElementTree as ET


async def extract_query_from_url(url: str) -> str | None:
    """
    Extract search query from PubMed search URL.

    Example URLs:
    - https://pubmed.ncbi.nlm.nih.gov/?term=cancer+AND+2024[pdat]
    - https://pubmed.ncbi.nlm.nih.gov/?term=aspirin&filter=years.2020-2024
    """
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # The 'term' parameter contains the search query
        if 'term' in params:
            return params['term'][0]

        return None
    except Exception as e:
        print(f"Error parsing URL: {e}")
        return None


async def search_pubmed(query: str, max_results: int = 10) -> list[str]:
    """
    Search PubMed using esearch API.

    Args:
        query: PubMed search query (e.g., "cancer AND 2024[pdat]")
        max_results: Maximum number of results to return (default 10, max 10000)

    Returns:
        List of PMIDs matching the query
    """
    # Build esearch URL
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    params = {
        "db": "pubmed",
        "term": query,
        "retmax": min(max_results, 10000),  # NCBI limit
        "retmode": "xml",
        "usehistory": "y"  # Store results on history server for large result sets
    }

    # Build query string
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{base_url}?{query_string}"

    print(f"Searching PubMed: {query}")
    print(f"API URL: {url}\n")

    # Make API request
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        # Parse XML response
        xml_content = response.text
        root = ET.fromstring(xml_content)

        # Extract PMIDs
        pmids = []
        for id_elem in root.findall('.//Id'):
            pmids.append(id_elem.text)

        # Get result count
        count_elem = root.find('.//Count')
        total_count = int(count_elem.text) if count_elem is not None else 0

        print(f"Found {total_count} total results")
        print(f"Returning first {len(pmids)} PMIDs\n")

        return pmids


async def test_search_by_query():
    """Test searching PubMed with a direct query."""
    print("=" * 80)
    print("TEST 1: Search PubMed by Query")
    print("=" * 80)
    print()

    # Search for aspirin studies from 2020-2024
    query = "aspirin AND (2020:2024[pdat])"
    max_results = 5

    pmids = await search_pubmed(query, max_results)

    print(f"Retrieved PMIDs:")
    for i, pmid in enumerate(pmids, 1):
        print(f"  {i}. PMID {pmid} - https://pubmed.ncbi.nlm.nih.gov/{pmid}/")

    print("\n✓ Search by query successful!\n")
    return pmids


async def test_search_by_url():
    """Test extracting query from PubMed URL and searching."""
    print("=" * 80)
    print("TEST 2: Search PubMed by URL")
    print("=" * 80)
    print()

    # Example: User copies this URL from PubMed website
    search_url = "https://pubmed.ncbi.nlm.nih.gov/?term=vitamin+d+AND+covid-19&filter=years.2020-2024"

    print(f"PubMed search URL: {search_url}")

    # Extract query from URL
    query = await extract_query_from_url(search_url)

    if not query:
        print("✗ Could not extract query from URL")
        return []

    print(f"Extracted query: {query}\n")

    # Search with extracted query
    pmids = await search_pubmed(query, max_results=5)

    print(f"Retrieved PMIDs:")
    for i, pmid in enumerate(pmids, 1):
        print(f"  {i}. PMID {pmid} - https://pubmed.ncbi.nlm.nih.gov/{pmid}/")

    print("\n✓ Search by URL successful!\n")
    return pmids


async def test_fetch_article_metadata(pmid: str):
    """
    Test fetching article metadata using efetch.
    This demonstrates what we'd get for each PMID in bulk download.
    """
    print("=" * 80)
    print(f"TEST 3: Fetch Article Metadata for PMID {pmid}")
    print("=" * 80)
    print()

    # Build efetch URL
    url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={pmid}&retmode=xml&rettype=abstract"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        # Parse XML
        root = ET.fromstring(response.text)
        article_elem = root.find('.//PubmedArticle')

        if article_elem is None:
            print(f"✗ Article not found for PMID {pmid}")
            return

        # Extract title
        title_elem = article_elem.find('.//ArticleTitle')
        title = title_elem.text if title_elem is not None else "Untitled"

        # Extract authors
        authors = []
        author_list = article_elem.find('.//AuthorList')
        if author_list is not None:
            for author in author_list.findall('.//Author')[:3]:  # First 3 authors
                last_name = author.find('LastName')
                fore_name = author.find('ForeName')
                if last_name is not None:
                    if fore_name is not None:
                        authors.append(f"{fore_name.text} {last_name.text}")
                    else:
                        authors.append(last_name.text)

        # Extract year
        year_elem = article_elem.find('.//PubDate/Year')
        year = year_elem.text if year_elem is not None else "Unknown"

        # Extract journal
        journal_elem = article_elem.find('.//Journal/Title')
        journal = journal_elem.text if journal_elem is not None else "Unknown"

        print(f"Title: {title[:80]}...")
        print(f"Authors: {', '.join(authors)}{' et al.' if len(authors) == 3 else ''}")
        print(f"Journal: {journal}")
        print(f"Year: {year}")
        print(f"URL: https://pubmed.ncbi.nlm.nih.gov/{pmid}/")

        print("\n✓ Metadata fetch successful!\n")


async def test_bulk_workflow():
    """
    Test complete bulk download workflow:
    1. Search for articles
    2. Get PMIDs
    3. Fetch metadata for each
    """
    print("=" * 80)
    print("TEST 4: Complete Bulk Workflow")
    print("=" * 80)
    print()

    # Search
    query = "CRISPR AND gene editing AND (2023:2024[pdat])"
    max_results = 3

    print(f"Step 1: Search for '{query}'")
    pmids = await search_pubmed(query, max_results)

    if not pmids:
        print("✗ No results found")
        return

    # Fetch metadata for each PMID with rate limiting
    print(f"\nStep 2: Fetch metadata for {len(pmids)} articles")
    print("(Rate limiting: 3 requests/second per NCBI guidelines)\n")

    for i, pmid in enumerate(pmids, 1):
        print(f"Article {i}/{len(pmids)}:")
        print("-" * 80)
        await test_fetch_article_metadata(pmid)

        # Rate limiting: NCBI allows 3 requests/second without API key
        if i < len(pmids):
            await asyncio.sleep(0.34)  # ~3 requests/second

    print("✓ Bulk workflow complete!\n")


async def run_all_tests():
    """Run all PubMed search tests."""
    try:
        # Test 1: Search by query
        pmids1 = await test_search_by_query()

        # Test 2: Search by URL
        pmids2 = await test_search_by_url()

        # Test 3: Fetch single article metadata
        if pmids1:
            await test_fetch_article_metadata(pmids1[0])

        # Test 4: Complete bulk workflow
        await test_bulk_workflow()

        print("=" * 80)
        print("✓ ALL PUBMED SEARCH TESTS PASSED!")
        print("=" * 80)
        print()
        print("Summary:")
        print("- esearch API: Query and URL extraction working")
        print("- efetch API: Metadata retrieval working")
        print("- Rate limiting: Implemented (3 req/sec)")
        print("- Bulk workflow: Ready for implementation")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    asyncio.run(run_all_tests())
