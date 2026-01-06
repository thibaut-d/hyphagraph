"""
Test script for PubMed E-utilities API integration.

Tests fetching PubMed articles using the official NCBI API.
"""
import asyncio
import sys
from app.services.pubmed_fetcher import PubMedFetcher


async def test_pubmed_by_pmid():
    """Test fetching a PubMed article by PMID."""
    # PMID for a research article with abstract (aspirin study)
    pmid = "23953482"

    print(f"Testing PubMed fetch by PMID: {pmid}")
    print("=" * 80)

    fetcher = PubMedFetcher()

    try:
        article = await fetcher.fetch_by_pmid(pmid)

        print(f"\n✓ Successfully fetched article")
        print(f"  PMID: {article.pmid}")
        print(f"  Title: {article.title}")
        print(f"  Authors: {', '.join(article.authors[:3])}{' et al.' if len(article.authors) > 3 else ''}")
        print(f"  Journal: {article.journal}")
        print(f"  Year: {article.year}")
        print(f"  DOI: {article.doi}")
        print(f"  URL: {article.url}")

        if article.abstract:
            print(f"\nAbstract (first 300 chars):")
            print("-" * 80)
            print(article.abstract[:300])
            if len(article.abstract) > 300:
                print("...")
            print("-" * 80)

        print(f"\nFull text for extraction ({len(article.full_text)} chars)")

        return article

    except Exception as e:
        print(f"\n✗ Error fetching article: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def test_pubmed_by_url():
    """Test fetching a PubMed article by URL."""
    url = "https://pubmed.ncbi.nlm.nih.gov/23953482/"

    print(f"\n\nTesting PubMed fetch by URL: {url}")
    print("=" * 80)

    fetcher = PubMedFetcher()

    try:
        article = await fetcher.fetch_by_url(url)

        print(f"\n✓ Successfully fetched article from URL")
        print(f"  PMID: {article.pmid}")
        print(f"  Title: {article.title}")

        return article

    except Exception as e:
        print(f"\n✗ Error fetching article from URL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def test_with_extraction():
    """Test PubMed fetch + knowledge extraction."""
    # Fetch the article
    article = await test_pubmed_by_pmid()

    print("\n" + "=" * 80)
    print("Testing knowledge extraction from PubMed article...")
    print("=" * 80)

    # Now test extraction
    from app.services.extraction_service import ExtractionService

    extraction_service = ExtractionService()
    entities, relations, warnings = await extraction_service.extract_batch(
        text=article.full_text,
        min_confidence="medium"
    )

    print(f"\n✓ Extraction complete:")
    print(f"  Entities extracted: {len(entities)}")
    print(f"  Relations extracted: {len(relations)}")

    if warnings:
        print(f"  Warnings: {warnings}")

    if entities:
        print(f"\nSample entities:")
        for entity in entities[:5]:
            print(f"  - {entity.slug} ({entity.category})")

    if relations:
        print(f"\nSample relations:")
        for relation in relations[:3]:
            roles = ", ".join([f"{r.entity_slug} ({r.role_type})" for r in relation.roles])
            print(f"  - {relation.kind}: {roles}")


async def test_url_extraction():
    """Test extracting PMID from various URL formats."""
    print("\n" + "=" * 80)
    print("Testing PMID extraction from URLs...")
    print("=" * 80)

    fetcher = PubMedFetcher()

    test_urls = [
        "https://pubmed.ncbi.nlm.nih.gov/30280642/",
        "https://pubmed.ncbi.nlm.nih.gov/30280642",
        "https://www.ncbi.nlm.nih.gov/pubmed/30280642",
        "pubmed/30280642",
    ]

    for url in test_urls:
        pmid = fetcher.extract_pmid_from_url(url)
        print(f"  {url}")
        print(f"    → PMID: {pmid}")


if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    # Run all tests
    async def run_all_tests():
        await test_url_extraction()
        await test_pubmed_by_pmid()
        await test_pubmed_by_url()
        print("\n" + "=" * 80)
        print("All PubMed API tests passed! ✓")
        print("=" * 80)

    asyncio.run(run_all_tests())
