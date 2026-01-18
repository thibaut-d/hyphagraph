#!/usr/bin/env python3
"""
Complete Fibromyalgia Knowledge Graph Workflow
Extracts knowledge from all 19 sources and generates final report
"""

import sqlite3
import json
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.extraction_service import ExtractionService
from app.services.url_fetcher import UrlFetcher
from app.services.pubmed_fetcher import PubMedFetcher

# Database path
DB_PATH = Path(__file__).parent / "hyphagraph.db"
FIBROMYALGIA_ENTITY_ID = "de334806-3edc-40c3-8b82-8e4c05f29481"

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

def get_all_sources():
    """Get all fibromyalgia sources from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, sr.title, sr.url, sr.trust_level, sr.created_at
        FROM sources s
        JOIN source_revisions sr ON s.id = sr.source_id
        WHERE sr.is_current = 1
        ORDER BY sr.trust_level DESC
    """)
    sources = []
    for row in cursor.fetchall():
        sources.append({
            'id': row[0],
            'title': row[1],
            'url': row[2],
            'trust_level': row[3],
            'created_at': row[4]
        })
    conn.close()
    return sources

async def extract_from_source(source_id, url):
    """Extract knowledge from a source URL"""
    print(f"\n{'='*80}")
    print(f"Extracting from source: {source_id}")
    print(f"URL: {url}")
    print(f"{'='*80}")

    try:
        # Step 1: Fetch content from URL
        pubmed_fetcher = PubMedFetcher()
        pmid = pubmed_fetcher.extract_pmid_from_url(url)

        if pmid:
            # Use PubMed API
            print(f"  Fetching PubMed article (PMID: {pmid})...")
            article = await pubmed_fetcher.fetch_by_pmid(pmid)
            document_text = article.full_text
            print(f"  Fetched {len(document_text)} characters")
        else:
            # Use general URL fetcher
            print(f"  Fetching from URL...")
            url_fetcher = UrlFetcher()
            fetch_result = await url_fetcher.fetch_url(url)
            document_text = fetch_result.text
            print(f"  Fetched {len(document_text)} characters")

        # Step 2: Extract entities and relations
        print(f"  Extracting knowledge with LLM...")
        extraction_service = ExtractionService()
        entities, relations, _ = await extraction_service.extract_batch(
            text=document_text,
            min_confidence="medium"
        )

        print(f"✓ Extracted {len(entities)} entities and {len(relations)} relations")

        # Convert to dict format
        entities_dict = [
            {
                'id': str(hash(e.slug + source_id)),  # Generate consistent ID
                'name': e.slug.replace('-', ' ').title(),
                'slug': e.slug,
                'type': e.category,
                'description': e.summary
            }
            for e in entities
        ]

        relations_dict = [
            {
                'id': str(hash(f"{r.source_slug}-{r.relation_type}-{r.target_slug}" + source_id)),
                'source_entity_id': str(hash(r.source_slug + source_id)),
                'target_entity_id': str(hash(r.target_slug + source_id)),
                'relation_type': r.relation_type,
                'source_slug': r.source_slug,
                'target_slug': r.target_slug
            }
            for r in relations
        ]

        return {
            'success': True,
            'entities': entities_dict,
            'relations': relations_dict
        }

    except Exception as e:
        print(f"✗ Exception during extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'entities': [],
            'relations': []
        }

def save_extraction(source_id, extraction_data):
    """Save extraction to database"""
    print(f"Saving extraction for source {source_id}...")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        entities = extraction_data.get('entities', [])
        relations = extraction_data.get('relations', [])

        # Save entities
        entity_count = 0
        for entity in entities:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO entities (id, name, type, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    entity['id'],
                    entity['name'],
                    entity['type'],
                    entity.get('description', ''),
                    datetime.utcnow().isoformat()
                ))
                if cursor.rowcount > 0:
                    entity_count += 1
            except Exception as e:
                print(f"  Warning: Could not save entity {entity.get('name')}: {e}")

        # Save relations
        relation_count = 0
        for relation in relations:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO relations (id, source_entity_id, target_entity_id, relation_type, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    relation['id'],
                    relation['source_entity_id'],
                    relation['target_entity_id'],
                    relation['relation_type'],
                    datetime.utcnow().isoformat()
                ))
                if cursor.rowcount > 0:
                    relation_count += 1
            except Exception as e:
                print(f"  Warning: Could not save relation: {e}")

        # Link source to entities
        for entity in entities:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO source_entities (source_id, entity_id)
                    VALUES (?, ?)
                """, (source_id, entity['id']))
            except Exception as e:
                print(f"  Warning: Could not link source to entity: {e}")

        conn.commit()
        conn.close()

        print(f"✓ Saved {entity_count} new entities and {relation_count} new relations")
        return True

    except Exception as e:
        print(f"✗ Failed to save extraction: {str(e)}")
        return False

def get_database_stats():
    """Get current database statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total entities
    cursor.execute("SELECT COUNT(*) FROM entities")
    total_entities = cursor.fetchone()[0]

    # Total relations
    cursor.execute("SELECT COUNT(*) FROM relations")
    total_relations = cursor.fetchone()[0]

    # Total sources
    cursor.execute("SELECT COUNT(*) FROM sources")
    total_sources = cursor.fetchone()[0]

    # Top entities by connection count
    cursor.execute("""
        SELECT e.name, e.type, COUNT(DISTINCT r.id) as connection_count
        FROM entities e
        LEFT JOIN relations r ON e.id = r.source_entity_id OR e.id = r.target_entity_id
        GROUP BY e.id
        ORDER BY connection_count DESC
        LIMIT 10
    """)
    top_entities = [{'name': row[0], 'type': row[1], 'connections': row[2]} for row in cursor.fetchall()]

    # Relation type distribution
    cursor.execute("""
        SELECT relation_type, COUNT(*) as count
        FROM relations
        GROUP BY relation_type
        ORDER BY count DESC
    """)
    relation_types = [{'type': row[0], 'count': row[1]} for row in cursor.fetchall()]

    # Entity type distribution
    cursor.execute("""
        SELECT type, COUNT(*) as count
        FROM entities
        GROUP BY type
        ORDER BY count DESC
    """)
    entity_types = [{'type': row[0], 'count': row[1]} for row in cursor.fetchall()]

    conn.close()

    return {
        'total_entities': total_entities,
        'total_relations': total_relations,
        'total_sources': total_sources,
        'top_entities': top_entities,
        'relation_types': relation_types,
        'entity_types': entity_types
    }

def calculate_inference(entity_id):
    """Calculate inference scores for an entity"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get entity info
    cursor.execute("SELECT name, type, description FROM entities WHERE id = ?", (entity_id,))
    entity_row = cursor.fetchone()
    if not entity_row:
        return None

    entity_name, entity_type, entity_description = entity_row

    # Get all relations
    cursor.execute("""
        SELECT r.relation_type, e.name, e.type
        FROM relations r
        JOIN entities e ON r.target_entity_id = e.id
        WHERE r.source_entity_id = ?

        UNION ALL

        SELECT r.relation_type, e.name, e.type
        FROM relations r
        JOIN entities e ON r.source_entity_id = e.id
        WHERE r.target_entity_id = ?
    """, (entity_id, entity_id))

    relations = [{'type': row[0], 'entity': row[1], 'entity_type': row[2]} for row in cursor.fetchall()]

    # Count by relation type
    relation_counts = {}
    for rel in relations:
        rel_type = rel['type']
        relation_counts[rel_type] = relation_counts.get(rel_type, 0) + 1

    # Get source quality for this entity
    cursor.execute("""
        SELECT AVG(s.quality_score) as avg_quality, COUNT(DISTINCT s.id) as source_count
        FROM source_entities se
        JOIN sources s ON se.source_id = s.id
        WHERE se.entity_id = ?
    """, (entity_id,))
    quality_row = cursor.fetchone()
    avg_quality = quality_row[0] or 0
    source_count = quality_row[1] or 0

    conn.close()

    return {
        'entity_name': entity_name,
        'entity_type': entity_type,
        'total_connections': len(relations),
        'relation_counts': relation_counts,
        'avg_source_quality': round(avg_quality, 2),
        'source_count': source_count,
        'connections': relations[:20]  # Limit to first 20 for report
    }

def generate_report(sources, results, stats, inference):
    """Generate comprehensive markdown report"""
    report = []
    report.append("# Fibromyalgia Knowledge Graph - Complete Workflow Results")
    report.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n**Total Sources Processed**: {len(sources)}")
    report.append(f"**Successful Extractions**: {sum(1 for r in results if r['success'])}")
    report.append(f"**Failed Extractions**: {sum(1 for r in results if not r['success'])}")

    # Execution summary
    report.append("\n## Execution Summary")
    report.append("\n| Source | Status | Entities | Relations | Time |")
    report.append("|--------|--------|----------|-----------|------|")
    for result in results:
        status = "✓" if result['success'] else "✗"
        entities = result.get('entities_extracted', 0)
        relations = result.get('relations_extracted', 0)
        duration = result.get('duration', 0)
        title = result['title'][:50]
        report.append(f"| {title}... | {status} | {entities} | {relations} | {duration:.1f}s |")

    # Database statistics
    report.append("\n## Database Statistics")
    report.append(f"\n- **Total Entities**: {stats['total_entities']}")
    report.append(f"- **Total Relations**: {stats['total_relations']}")
    report.append(f"- **Total Sources**: {stats['total_sources']}")

    # Entity types
    report.append("\n### Entity Type Distribution")
    report.append("\n| Entity Type | Count |")
    report.append("|-------------|-------|")
    for et in stats['entity_types']:
        report.append(f"| {et['type']} | {et['count']} |")

    # Relation types
    report.append("\n### Relation Type Distribution")
    report.append("\n| Relation Type | Count |")
    report.append("|---------------|-------|")
    for rt in stats['relation_types']:
        report.append(f"| {rt['type']} | {rt['count']} |")

    # Top entities
    report.append("\n### Top 10 Most Connected Entities")
    report.append("\n| Entity | Type | Connections |")
    report.append("|--------|------|-------------|")
    for ent in stats['top_entities']:
        report.append(f"| {ent['name']} | {ent['type']} | {ent['connections']} |")

    # Inference results
    report.append("\n## Fibromyalgia Entity Inference Analysis")
    if inference:
        report.append(f"\n- **Entity**: {inference['entity_name']}")
        report.append(f"- **Type**: {inference['entity_type']}")
        report.append(f"- **Total Connections**: {inference['total_connections']}")
        report.append(f"- **Average Source Quality**: {inference['avg_source_quality']}/5.0")
        report.append(f"- **Source Count**: {inference['source_count']}")

        report.append("\n### Connection Types")
        report.append("\n| Relation Type | Count |")
        report.append("|---------------|-------|")
        for rel_type, count in sorted(inference['relation_counts'].items(), key=lambda x: x[1], reverse=True):
            report.append(f"| {rel_type} | {count} |")

        report.append("\n### Sample Connections (First 20)")
        report.append("\n| Relation Type | Connected Entity | Entity Type |")
        report.append("|---------------|------------------|-------------|")
        for conn in inference['connections']:
            report.append(f"| {conn['type']} | {conn['entity']} | {conn['entity_type']} |")

    # Errors section
    failed = [r for r in results if not r['success']]
    if failed:
        report.append("\n## Extraction Errors")
        for result in failed:
            report.append(f"\n### {result['title']}")
            report.append(f"**URL**: {result['url']}")
            report.append(f"**Error**: {result.get('error', 'Unknown error')}")

    # Conclusion
    report.append("\n## Conclusion")
    success_rate = (sum(1 for r in results if r['success']) / len(results)) * 100
    report.append(f"\nSuccessfully extracted knowledge from **{success_rate:.1f}%** of sources.")
    report.append(f"The knowledge graph now contains **{stats['total_entities']} entities** and **{stats['total_relations']} relations**.")
    report.append(f"\nThe fibromyalgia entity has **{inference['total_connections']} connections** across the knowledge graph,")
    report.append(f"with an average source quality score of **{inference['avg_source_quality']}/5.0**.")

    return "\n".join(report)

async def main():
    """Main execution"""
    print("="*80)
    print("FIBROMYALGIA KNOWLEDGE GRAPH - COMPLETE WORKFLOW")
    print("="*80)

    start_time = time.time()

    # Step 1: Get all sources
    print("\n[1/5] Retrieving sources from database...")
    sources = get_all_sources()
    print(f"Found {len(sources)} sources")

    # Step 2: Extract and save from each source
    print("\n[2/5] Extracting knowledge from all sources...")
    results = []

    for i, source in enumerate(sources, 1):
        print(f"\n--- Processing {i}/{len(sources)} ---")

        extraction_start = time.time()
        extraction = await extract_from_source(source['id'], source['url'])
        extraction_time = time.time() - extraction_start

        if extraction and extraction.get('success'):
            saved = save_extraction(source['id'], extraction)
            results.append({
                'source_id': source['id'],
                'title': source['title'],
                'url': source['url'],
                'success': saved,
                'entities_extracted': len(extraction.get('entities', [])),
                'relations_extracted': len(extraction.get('relations', [])),
                'duration': extraction_time
            })
        else:
            results.append({
                'source_id': source['id'],
                'title': source['title'],
                'url': source['url'],
                'success': False,
                'entities_extracted': 0,
                'relations_extracted': 0,
                'duration': extraction_time,
                'error': extraction.get('error', 'Extraction failed') if extraction else 'Extraction returned None'
            })

        # Brief pause between requests
        await asyncio.sleep(2)

    # Step 3: Get database statistics
    print("\n[3/5] Calculating database statistics...")
    stats = get_database_stats()
    print(f"Total Entities: {stats['total_entities']}")
    print(f"Total Relations: {stats['total_relations']}")

    # Step 4: Calculate inference
    print("\n[4/5] Calculating inference for fibromyalgia entity...")
    inference = calculate_inference(FIBROMYALGIA_ENTITY_ID)
    if inference:
        print(f"Fibromyalgia has {inference['total_connections']} connections")

    # Step 5: Generate report
    print("\n[5/5] Generating final report...")
    report = generate_report(sources, results, stats, inference)

    report_path = Path(__file__).parent.parent / "FIBROMYALGIA_FINAL_RESULTS.md"
    with open(report_path, 'w') as f:
        f.write(report)

    total_time = time.time() - start_time

    print("\n" + "="*80)
    print("WORKFLOW COMPLETE")
    print("="*80)
    print(f"Total execution time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"Report saved to: {report_path}")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
