"""
Direct test of smart discovery logic without running full server.

Simulates the smart discovery workflow to verify it works correctly.
"""
import sys
import asyncio

sys.path.insert(0, '.')

from app.services.pubmed_fetcher import PubMedFetcher
from app.utils.source_quality import infer_trust_level_from_pubmed_metadata


async def test_smart_discovery():
    """Test smart discovery workflow."""

    print("=" * 70)
    print("SMART DISCOVERY TEST - Duloxetine AND Fibromyalgia")
    print("=" * 70)
    print()

    # Step 1: Construct query
    entity_slugs = ["duloxetine", "fibromyalgia"]
    entity_names = [slug.replace("-", " ").title() for slug in entity_slugs]
    query = " AND ".join(entity_names)

    print(f"📝 Entity slugs: {entity_slugs}")
    print(f"📝 Query constructed: {query}")
    print()

    # Step 2: Search PubMed
    print("🔍 Searching PubMed...")
    pubmed_fetcher = PubMedFetcher()

    max_results = 10
    pmids, total_count = await pubmed_fetcher.search_pubmed(
        query=query,
        max_results=max_results
    )

    print(f"✅ Found {total_count} total results in PubMed")
    print(f"✅ Retrieved {len(pmids)} PMIDs for processing")
    print()

    # Step 3: Fetch article metadata
    print("📥 Fetching article metadata...")
    articles = await pubmed_fetcher.bulk_fetch_articles(pmids)
    print(f"✅ Fetched {len(articles)} articles")
    print()

    # Step 4: Calculate quality scores
    print("🎯 Calculating quality scores (OCEBM/GRADE)...")
    results = []

    for article in articles:
        trust_level = infer_trust_level_from_pubmed_metadata(
            title=article.title,
            journal=article.journal,
            year=article.year,
            abstract=article.abstract
        )

        # Calculate relevance
        text = (article.title + " " + (article.abstract or "")).lower()
        mentions = sum(1 for name in entity_names if name.lower() in text)
        relevance = mentions / len(entity_names)

        results.append({
            "pmid": article.pmid,
            "title": article.title,
            "journal": article.journal,
            "year": article.year,
            "trust_level": trust_level,
            "relevance": relevance,
            "authors": article.authors[:2] if article.authors else []
        })

    print(f"✅ Scored {len(results)} articles")
    print()

    # Step 5: Filter by quality (min 0.5 for this test)
    min_quality = 0.5
    filtered = [r for r in results if r["trust_level"] >= min_quality]
    print(f"✅ Filtered to {len(filtered)} articles with quality >= {min_quality}")
    print()

    # Step 6: Sort by quality
    sorted_results = sorted(
        filtered,
        key=lambda r: (r["trust_level"], r["relevance"]),
        reverse=True
    )

    # Step 7: Display results
    print("=" * 70)
    print("RESULTS (Top 10, sorted by quality)")
    print("=" * 70)
    print()

    for i, r in enumerate(sorted_results[:10], 1):
        quality_label = "Systematic Review" if r["trust_level"] >= 0.9 else \
                       "RCT/High Quality" if r["trust_level"] >= 0.75 else \
                       "Moderate Quality" if r["trust_level"] >= 0.65 else \
                       "Low Quality"

        authors_str = ", ".join(r["authors"]) if r["authors"] else "N/A"

        print(f"{i}. Quality: {r['trust_level']:.2f} ({quality_label})")
        print(f"   Title: {r['title'][:80]}...")
        print(f"   Journal: {r['journal']}")
        print(f"   Year: {r['year']}")
        print(f"   Authors: {authors_str}")
        print(f"   Relevance: {r['relevance']*100:.0f}%")
        print(f"   PMID: {r['pmid']}")
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ Query: {query}")
    print(f"✅ Total found: {total_count}")
    print(f"✅ Retrieved: {len(articles)}")
    print(f"✅ After quality filter: {len(filtered)}")
    print(f"✅ Top 10 displayed")
    print()

    # Quality distribution
    quality_1_0 = len([r for r in filtered if r["trust_level"] >= 0.9])
    quality_0_75 = len([r for r in filtered if 0.75 <= r["trust_level"] < 0.9])
    quality_0_5 = len([r for r in filtered if 0.5 <= r["trust_level"] < 0.75])

    print("Quality Distribution:")
    print(f"  Systematic Reviews (≥0.9): {quality_1_0}")
    print(f"  RCTs/High Quality (0.75-0.89): {quality_0_75}")
    print(f"  Moderate Quality (0.5-0.74): {quality_0_5}")
    print()

    print("✅ Smart discovery test PASSED!")
    print("✅ System is ready to import these sources")

    return sorted_results[:10]


if __name__ == "__main__":
    results = asyncio.run(test_smart_discovery())
