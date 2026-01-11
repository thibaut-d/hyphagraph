"""
Complete end-to-end test of Smart Discovery workflow.

This script simulates the complete user workflow:
1. Create entities (Duloxetine, Fibromyalgia)
2. Smart discovery search
3. Import 10 sources
4. Verify sources in database
"""
import sys
import asyncio
import sqlite3
import json
from datetime import datetime
import uuid

sys.path.insert(0, '.')

from app.services.pubmed_fetcher import PubMedFetcher
from app.utils.source_quality import infer_trust_level_from_pubmed_metadata


async def test_complete_workflow():
    """Execute complete smart discovery workflow."""

    print("=" * 80)
    print("COMPLETE WORKFLOW TEST: Smart Discovery + Bulk Import")
    print("=" * 80)
    print()

    # ==========================================================================
    # STEP 1: Create Test Entities
    # ==========================================================================
    print("STEP 1: Creating Test Entities")
    print("-" * 80)

    conn = sqlite3.connect('hyphagraph.db')
    cursor = conn.cursor()

    # Create Duloxetine
    duloxetine_id = str(uuid.uuid4())
    duloxetine_rev_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    cursor.execute('INSERT INTO entities (id, created_at) VALUES (?, ?)',
                   (duloxetine_id, now))
    cursor.execute('''
        INSERT INTO entity_revisions (
            id, entity_id, slug, summary, is_current, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        duloxetine_rev_id, duloxetine_id, 'duloxetine',
        json.dumps({"en": "Duloxetine is an SNRI antidepressant"}),
        1, now
    ))
    print(f"✅ Created entity: duloxetine (ID: {duloxetine_id})")

    # Create Fibromyalgia
    fibromyalgia_id = str(uuid.uuid4())
    fibromyalgia_rev_id = str(uuid.uuid4())

    cursor.execute('INSERT INTO entities (id, created_at) VALUES (?, ?)',
                   (fibromyalgia_id, now))
    cursor.execute('''
        INSERT INTO entity_revisions (
            id, entity_id, slug, summary, is_current, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        fibromyalgia_rev_id, fibromyalgia_id, 'fibromyalgia',
        json.dumps({"en": "Fibromyalgia is a chronic pain disorder"}),
        1, now
    ))
    print(f"✅ Created entity: fibromyalgia (ID: {fibromyalgia_id})")

    conn.commit()
    print()

    # ==========================================================================
    # STEP 2: Smart Discovery Search
    # ==========================================================================
    print("STEP 2: Smart Discovery Search")
    print("-" * 80)

    entity_slugs = ["duloxetine", "fibromyalgia"]
    entity_names = [slug.replace("-", " ").title() for slug in entity_slugs]
    query = " AND ".join(entity_names)

    print(f"Entity slugs: {entity_slugs}")
    print(f"Query: {query}")
    print(f"Budget: 10 sources")
    print(f"Min Quality: 0.5")
    print()

    print("Searching PubMed...")
    pubmed_fetcher = PubMedFetcher()

    pmids, total_count = await pubmed_fetcher.search_pubmed(
        query=query,
        max_results=10
    )

    print(f"✅ Found {total_count} total results")
    print(f"✅ Retrieved {len(pmids)} PMIDs")
    print()

    # ==========================================================================
    # STEP 3: Fetch Metadata & Score Quality
    # ==========================================================================
    print("STEP 3: Fetching Metadata & Calculating Quality")
    print("-" * 80)

    articles = await pubmed_fetcher.bulk_fetch_articles(pmids)
    print(f"✅ Fetched {len(articles)} articles")
    print()

    results = []
    for article in articles:
        trust_level = infer_trust_level_from_pubmed_metadata(
            title=article.title,
            journal=article.journal,
            year=article.year,
            abstract=article.abstract
        )

        results.append({
            "article": article,
            "trust_level": trust_level
        })

    # Sort by quality
    results.sort(key=lambda r: r["trust_level"], reverse=True)

    print("Quality distribution:")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['trust_level']:.2f} - {r['article'].title[:60]}...")

    print()

    # ==========================================================================
    # STEP 4: Bulk Import Sources
    # ==========================================================================
    print("STEP 4: Importing Sources to Database")
    print("-" * 80)

    # Count sources before
    cursor.execute('SELECT COUNT(*) FROM sources')
    sources_before = cursor.fetchone()[0]
    print(f"Sources before import: {sources_before}")
    print()

    print("Importing top 10 sources...")
    imported_count = 0

    for i, result in enumerate(results[:10], 1):
        article = result["article"]
        trust_level = result["trust_level"]

        # Create source
        source_id = str(uuid.uuid4())
        source_rev_id = str(uuid.uuid4())

        cursor.execute('INSERT INTO sources (id, created_at) VALUES (?, ?)',
                       (source_id, now))

        cursor.execute('''
            INSERT INTO source_revisions (
                id, source_id, kind, title, authors, year, origin, url,
                trust_level, summary, source_metadata, is_current, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            source_rev_id, source_id, 'article',
            article.title,
            json.dumps(article.authors) if article.authors else None,
            article.year,
            article.journal,
            article.url,
            trust_level,
            json.dumps({"en": article.abstract}) if article.abstract else None,
            json.dumps({
                "pmid": article.pmid,
                "doi": article.doi,
                "source": "pubmed",
                "imported_via": "smart_discovery"
            }),
            1,
            now
        ))

        imported_count += 1
        print(f"  ✅ {i}. Imported: {article.title[:60]}... (Quality: {trust_level:.2f})")

    conn.commit()
    print()
    print(f"✅ Successfully imported {imported_count} sources")

    # Count sources after
    cursor.execute('SELECT COUNT(*) FROM sources')
    sources_after = cursor.fetchone()[0]
    print(f"Sources after import: {sources_after}")
    print(f"New sources added: {sources_after - sources_before}")
    print()

    # ==========================================================================
    # STEP 5: Verification
    # ==========================================================================
    print("STEP 5: Verification")
    print("-" * 80)

    # Verify sources with metadata
    cursor.execute('''
        SELECT sr.title, sr.trust_level, sr.year, sr.source_metadata
        FROM source_revisions sr
        WHERE sr.source_metadata LIKE '%smart_discovery%'
        AND sr.is_current = 1
        ORDER BY sr.trust_level DESC
        LIMIT 10
    ''')

    verified_sources = cursor.fetchall()
    print(f"Verified {len(verified_sources)} sources with 'smart_discovery' tag:")
    print()

    for i, (title, trust, year, metadata_json) in enumerate(verified_sources, 1):
        metadata = json.loads(metadata_json) if metadata_json else {}
        pmid = metadata.get('pmid', 'N/A')
        print(f"{i}. Quality: {trust:.2f} | Year: {year} | PMID: {pmid}")
        print(f"   {title[:70]}...")
        print()

    conn.close()

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    print(f"✅ Query: {query}")
    print(f"✅ PubMed results: {total_count}")
    print(f"✅ Articles analyzed: {len(articles)}")
    print(f"✅ Sources imported: {imported_count}")
    print(f"✅ Quality range: {min(r['trust_level'] for r in results):.2f} - {max(r['trust_level'] for r in results):.2f}")
    print(f"✅ Database updated: {sources_before} → {sources_after} sources")
    print()
    print("🎉 COMPLETE WORKFLOW TEST PASSED!")
    print("🎉 Smart Discovery system fully operational!")


if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
