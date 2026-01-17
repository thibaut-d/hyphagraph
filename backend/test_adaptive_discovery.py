"""
Test adaptive fetching for smart discovery with fibromyalgia.

This test simulates the adaptive fetching algorithm to verify it works correctly.
"""
import sys
import asyncio

sys.path.insert(0, '.')

from app.services.pubmed_fetcher import PubMedFetcher
from app.utils.source_quality import infer_trust_level_from_pubmed_metadata


async def test_adaptive_discovery():
    """Test adaptive discovery workflow for fibromyalgia."""

    print("=" * 80)
    print("ADAPTIVE DISCOVERY TEST - Fibromyalgia")
    print("=" * 80)
    print()

    # Configuration (matching what user would set in UI)
    query = "Fibromyalgia"
    target_results = 20  # What user requested
    min_quality = 0.75  # Default UI setting (RCT+ only)
    batch_size = 50
    max_fetch_limit = 500

    print(f"📝 Query: {query}")
    print(f"📝 Target results: {target_results}")
    print(f"📝 Minimum quality: {min_quality}")
    print(f"📝 Batch size: {batch_size}")
    print(f"📝 Max fetch limit: {max_fetch_limit}")
    print()

    pubmed_fetcher = PubMedFetcher()

    # Adaptive fetching
    offset = 0
    total_count = 0
    high_quality_results = []
    batches_fetched = 0

    print("🔍 Starting adaptive fetch...")
    print()

    while len(high_quality_results) < target_results and offset < max_fetch_limit:
        batches_fetched += 1

        # Search for next batch
        print(f"📥 Batch {batches_fetched}: Searching (offset={offset}, batch_size={batch_size})")
        pmids, total_count = await pubmed_fetcher.search_pubmed(
            query=query,
            max_results=batch_size,
            retstart=offset
        )

        if not pmids:
            print(f"   ⚠️  No more results available")
            break

        print(f"   ✅ Found {len(pmids)} PMIDs (total available: {total_count:,})")

        # Fetch article metadata
        print(f"   📥 Fetching metadata for {len(pmids)} articles...")
        articles = await pubmed_fetcher.bulk_fetch_articles(pmids)
        print(f"   ✅ Fetched {len(articles)} articles")

        # Calculate quality scores
        batch_high_quality = 0
        for article in articles:
            trust_level = infer_trust_level_from_pubmed_metadata(
                title=article.title,
                journal=article.journal,
                year=article.year,
                abstract=article.abstract
            )

            if trust_level >= min_quality:
                batch_high_quality += 1
                high_quality_results.append({
                    "pmid": article.pmid,
                    "title": article.title[:60] + "...",
                    "journal": article.journal,
                    "year": article.year,
                    "trust_level": trust_level
                })

        print(f"   ✅ Quality filter: {batch_high_quality}/{len(articles)} passed (>= {min_quality})")
        print(f"   📊 Total high-quality: {len(high_quality_results)}/{target_results}")
        print()

        # Check if we have enough
        if len(high_quality_results) >= target_results:
            print(f"✅ Target reached! Found {len(high_quality_results)} high-quality sources")
            print(f"   📊 Searched {offset + len(pmids)} articles out of {total_count:,} available")
            break

        # Check if we've exhausted results
        if offset + len(pmids) >= total_count:
            print(f"⚠️  Exhausted all {total_count:,} results")
            print(f"   📊 Found only {len(high_quality_results)} high-quality sources (target was {target_results})")
            break

        # Move to next batch
        offset += batch_size

    # Display results
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    print(f"🎯 Target: {target_results} sources with quality >= {min_quality}")
    print(f"✅ Found: {len(high_quality_results)} sources")
    print(f"📊 Batches fetched: {batches_fetched}")
    print(f"📊 Total articles searched: {min(offset + batch_size, total_count)}")
    print(f"📊 Total available in PubMed: {total_count:,}")
    print()

    if high_quality_results:
        print(f"Top {min(10, len(high_quality_results))} high-quality sources:")
        print()
        for i, result in enumerate(high_quality_results[:10], 1):
            print(f"{i}. [{result['trust_level']:.2f}] {result['title']}")
            print(f"   Journal: {result['journal']}")
            print(f"   Year: {result['year']}, PMID: {result['pmid']}")
            print()

    # Analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()

    if len(high_quality_results) >= target_results:
        efficiency = (len(high_quality_results) / (offset + batch_size)) * 100
        print(f"✅ SUCCESS: Adaptive fetching found enough high-quality sources")
        print(f"   Efficiency: {efficiency:.1f}% of searched articles passed quality filter")
    elif len(high_quality_results) > 0:
        print(f"⚠️  PARTIAL: Found {len(high_quality_results)}/{target_results} sources")
        print(f"   Suggestion: Lower min_quality threshold to {0.5} to get more results")
    else:
        print(f"❌ FAILED: No sources found with quality >= {min_quality}")
        print(f"   Suggestion: Try min_quality=0.5 or different search query")

    print()
    return high_quality_results


if __name__ == "__main__":
    results = asyncio.run(test_adaptive_discovery())
