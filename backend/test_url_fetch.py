"""
Test script for URL fetching from PubMed.

Tests the UrlFetcher service with a real PubMed article.
"""
import asyncio
import sys
from app.services.url_fetcher import UrlFetcher


async def test_pubmed_fetch():
    """Test fetching a medical article from web."""
    # Test with example.com first to verify fetcher works
    test_url = "http://example.com"

    print(f"Testing URL fetch from: {test_url}")
    print("-" * 80)

    fetcher = UrlFetcher()

    try:
        result = await fetcher.fetch_url(test_url)

        print(f"\n✓ Successfully fetched URL")
        print(f"  Title: {result.title}")
        print(f"  URL: {result.url}")
        print(f"  Characters: {result.char_count}")
        print(f"  Truncated: {result.truncated}")

        if result.warnings:
            print(f"  Warnings: {', '.join(result.warnings)}")

        print(f"\nExtracted text preview (first 500 chars):")
        print("-" * 80)
        print(result.text[:500])
        print("-" * 80)

        if len(result.text) > 500:
            print("\n[... text continues ...]")

        return result

    except Exception as e:
        print(f"\n✗ Error fetching URL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def test_with_extraction():
    """Test URL fetch + knowledge extraction."""
    # Fetch the document
    result = await test_pubmed_fetch()

    print("\n" + "=" * 80)
    print("Testing knowledge extraction from fetched content...")
    print("=" * 80)

    # Now test extraction
    from app.services.extraction_service import ExtractionService

    extraction_service = ExtractionService()
    entities, relations, warnings = await extraction_service.extract_batch(
        text=result.text,
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


if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    # Run the test
    asyncio.run(test_with_extraction())
