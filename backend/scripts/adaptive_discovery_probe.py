"""
Manual probe for adaptive PubMed discovery behavior.

This is developer tooling, not an automated test. It can be run when you want
to inspect how many high-quality PubMed sources a query yields under the
current adaptive-fetch settings.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.pubmed_fetcher import PubMedFetcher
from app.utils.source_quality import infer_trust_level_from_pubmed_metadata


async def run_probe(
    *,
    query: str,
    target_results: int,
    min_quality: float,
    batch_size: int,
    max_fetch_limit: int,
) -> list[dict[str, object]]:
    print("=" * 80)
    print("ADAPTIVE DISCOVERY PROBE")
    print("=" * 80)
    print(f"Query: {query}")
    print(f"Target results: {target_results}")
    print(f"Minimum quality: {min_quality}")
    print(f"Batch size: {batch_size}")
    print(f"Max fetch limit: {max_fetch_limit}")
    print()

    pubmed_fetcher = PubMedFetcher()
    offset = 0
    total_count = 0
    high_quality_results: list[dict[str, object]] = []
    batches_fetched = 0

    while len(high_quality_results) < target_results and offset < max_fetch_limit:
        batches_fetched += 1
        print(f"Batch {batches_fetched}: searching offset={offset}, batch_size={batch_size}")

        pmids, total_count = await pubmed_fetcher.search_pubmed(
            query=query,
            max_results=batch_size,
            retstart=offset,
        )

        if not pmids:
            print("No more results available.")
            break

        print(f"Found {len(pmids)} PMIDs (total available: {total_count:,})")

        articles = await pubmed_fetcher.bulk_fetch_articles(pmids)
        print(f"Fetched metadata for {len(articles)} articles")

        batch_high_quality = 0
        for article in articles:
            trust_level = infer_trust_level_from_pubmed_metadata(
                title=article.title,
                journal=article.journal,
                year=article.year,
                abstract=article.abstract,
            )
            if trust_level < min_quality:
                continue

            batch_high_quality += 1
            high_quality_results.append(
                {
                    "pmid": article.pmid,
                    "title": article.title[:60] + "...",
                    "journal": article.journal,
                    "year": article.year,
                    "trust_level": trust_level,
                }
            )

        print(f"Quality filter: {batch_high_quality}/{len(articles)} passed")
        print(f"Total high-quality: {len(high_quality_results)}/{target_results}")
        print()

        if len(high_quality_results) >= target_results:
            print("Target reached.")
            break

        if offset + len(pmids) >= total_count:
            print(f"Exhausted all {total_count:,} search results.")
            break

        offset += batch_size

    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Found {len(high_quality_results)} high-quality sources")
    print(f"Batches fetched: {batches_fetched}")
    print(f"Articles searched: {min(offset + batch_size, total_count) if total_count else 0}")
    print(f"Total available in PubMed: {total_count:,}")
    print()

    for index, result in enumerate(high_quality_results[:10], start=1):
        print(f"{index}. [{result['trust_level']:.2f}] {result['title']}")
        print(f"   Journal: {result['journal']}")
        print(f"   Year: {result['year']}, PMID: {result['pmid']}")
        print()

    return high_quality_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe adaptive discovery quality filtering.")
    parser.add_argument("--query", default="Fibromyalgia", help="PubMed search query")
    parser.add_argument("--target-results", type=int, default=20, help="Desired number of results")
    parser.add_argument("--min-quality", type=float, default=0.75, help="Minimum trust level")
    parser.add_argument("--batch-size", type=int, default=50, help="PubMed batch size")
    parser.add_argument("--max-fetch-limit", type=int, default=500, help="Maximum articles to inspect")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(
        run_probe(
            query=args.query,
            target_results=args.target_results,
            min_quality=args.min_quality,
            batch_size=args.batch_size,
            max_fetch_limit=args.max_fetch_limit,
        )
    )


if __name__ == "__main__":
    main()
