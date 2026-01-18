"""
Batch auto-extraction for ALL Smart Discovery sources.

Extracts entities and relations from all Smart Discovery sources
that haven't been extracted yet.
"""
import sys
import asyncio
import sqlite3
import json
import os
from datetime import datetime
import uuid
from dotenv import load_dotenv

sys.path.insert(0, '.')

# Load environment
load_dotenv('.env')

# Check for OpenAI key
if not os.getenv('OPENAI_API_KEY'):
    print("ERROR: OPENAI_API_KEY not found in .env")
    sys.exit(1)

from app.services.pubmed_fetcher import PubMedFetcher
from app.services.extraction_service import ExtractionService


async def extract_source(source_id, title, pmid, existing_entities, conn):
    """Extract knowledge from a single source."""
    cursor = conn.cursor()

    print(f"\n{'='*80}")
    print(f"PROCESSING: {title}")
    print(f"PMID: {pmid}")
    print(f"{'='*80}\n")

    try:
        # Fetch document
        print("  [1/3] Fetching document from PubMed...")
        pubmed_fetcher = PubMedFetcher()
        article = await pubmed_fetcher.fetch_by_pmid(pmid)
        document_text = article.full_text
        print(f"        Retrieved: {len(document_text)} characters")

        # Extract with LLM
        print("  [2/3] Extracting knowledge with GPT-4 (~20 seconds)...")
        extraction_service = ExtractionService()
        entities, relations, claims = await extraction_service.extract_batch(document_text)

        print(f"        Extracted: {len(entities)} entities, {len(relations)} relations")

        # Save to database
        print("  [3/3] Saving to database...")

        entity_id_map = {}
        entities_created = 0
        entities_linked = 0
        now = datetime.utcnow().isoformat()

        # Process entities
        for entity in entities:
            # Check if entity already exists (exact slug match)
            if entity.slug in existing_entities:
                entity_id_map[entity.slug] = existing_entities[entity.slug]
                entities_linked += 1
            else:
                # Create new entity
                entity_id = str(uuid.uuid4())
                entity_rev_id = str(uuid.uuid4())

                cursor.execute('INSERT INTO entities (id, created_at) VALUES (?, ?)',
                               (entity_id, now))
                cursor.execute('''
                    INSERT INTO entity_revisions (
                        id, entity_id, slug, summary, is_current, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    entity_rev_id, entity_id, entity.slug,
                    json.dumps({"en": entity.summary}),
                    1, now
                ))

                entity_id_map[entity.slug] = entity_id
                existing_entities[entity.slug] = entity_id  # Update for next sources
                entities_created += 1

        # Process relations
        relations_created = 0
        relations_skipped = 0

        for relation in relations:
            # Get entity IDs
            subject_id = entity_id_map.get(relation.subject_slug)
            object_id = entity_id_map.get(relation.object_slug)

            if not subject_id or not object_id:
                relations_skipped += 1
                continue

            # Create relation
            relation_id = str(uuid.uuid4())
            relation_rev_id = str(uuid.uuid4())

            cursor.execute('INSERT INTO relations (id, source_id, created_at) VALUES (?, ?, ?)',
                           (relation_id, source_id, now))

            cursor.execute('''
                INSERT INTO relation_revisions (
                    id, relation_id, kind, direction, confidence, is_current, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                relation_rev_id, relation_id, relation.relation_type,
                "supports", 0.8, 1, now
            ))

            # Create roles
            role_subject_id = str(uuid.uuid4())
            role_object_id = str(uuid.uuid4())

            cursor.execute('''
                INSERT INTO relation_role_revisions (
                    id, relation_revision_id, entity_id, role_type
                ) VALUES (?, ?, ?, ?)
            ''', (role_subject_id, relation_rev_id, subject_id, "subject"))

            cursor.execute('''
                INSERT INTO relation_role_revisions (
                    id, relation_revision_id, entity_id, role_type
                ) VALUES (?, ?, ?, ?)
            ''', (role_object_id, relation_rev_id, object_id, "object"))

            relations_created += 1

        conn.commit()

        print(f"        SUCCESS!")
        print(f"        - Entities: {entities_created} created, {entities_linked} linked")
        print(f"        - Relations: {relations_created} created")
        if relations_skipped > 0:
            print(f"        - Relations skipped: {relations_skipped}")

        return {
            'success': True,
            'entities_created': entities_created,
            'entities_linked': entities_linked,
            'relations_created': relations_created,
            'relations_skipped': relations_skipped
        }

    except Exception as e:
        print(f"        ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


async def batch_extract():
    """Extract all Smart Discovery sources."""

    print("\n" + "="*80)
    print("BATCH AUTO-EXTRACTION FOR ALL SMART DISCOVERY SOURCES")
    print("="*80 + "\n")

    conn = sqlite3.connect('hyphagraph.db')
    cursor = conn.cursor()

    # Get current state
    cursor.execute('SELECT COUNT(*) FROM entities')
    entities_before = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM relations')
    relations_before = cursor.fetchone()[0]

    print(f"Database state BEFORE extraction:")
    print(f"  Entities: {entities_before}")
    print(f"  Relations: {relations_before}")
    print()

    # Get existing entity IDs for linking
    cursor.execute('''
        SELECT e.id, er.slug
        FROM entities e
        JOIN entity_revisions er ON e.id = er.entity_id
        WHERE er.is_current = 1
    ''')
    existing_entities = {row[1]: row[0] for row in cursor.fetchall()}
    print(f"Existing entities for linking: {len(existing_entities)}")
    print()

    # Get all Smart Discovery sources without extractions
    cursor.execute('''
        SELECT s.id, sr.title, sr.source_metadata
        FROM sources s
        JOIN source_revisions sr ON s.id = sr.source_id
        LEFT JOIN relations r ON s.id = r.source_id
        WHERE sr.source_metadata LIKE '%smart_discovery%'
        AND sr.is_current = 1
        GROUP BY s.id, sr.title, sr.source_metadata
        HAVING COUNT(r.id) = 0
        ORDER BY sr.title
    ''')

    sources_to_extract = []
    for row in cursor.fetchall():
        source_id, title, metadata_json = row
        metadata = json.loads(metadata_json) if metadata_json else {}
        pmid = metadata.get('pmid')
        if pmid:
            sources_to_extract.append((source_id, title, pmid))

    print(f"Found {len(sources_to_extract)} sources to extract:")
    for i, (_, title, pmid) in enumerate(sources_to_extract, 1):
        print(f"  {i}. PMID {pmid}: {title[:70]}...")
    print()

    if not sources_to_extract:
        print("All sources already extracted!")
        conn.close()
        return

    # Extract each source
    results = []
    for i, (source_id, title, pmid) in enumerate(sources_to_extract, 1):
        print(f"\n[{i}/{len(sources_to_extract)}] ", end="")
        result = await extract_source(source_id, title, pmid, existing_entities, conn)
        results.append(result)

        # Brief pause between extractions to be nice to the API
        if i < len(sources_to_extract):
            await asyncio.sleep(1)

    # Final statistics
    print("\n\n" + "="*80)
    print("BATCH EXTRACTION COMPLETE")
    print("="*80 + "\n")

    cursor.execute('SELECT COUNT(*) FROM entities')
    entities_after = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM relations')
    relations_after = cursor.fetchone()[0]

    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful

    total_entities_created = sum(r.get('entities_created', 0) for r in results if r['success'])
    total_entities_linked = sum(r.get('entities_linked', 0) for r in results if r['success'])
    total_relations_created = sum(r.get('relations_created', 0) for r in results if r['success'])

    print(f"Sources processed: {len(sources_to_extract)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print()
    print(f"Database state AFTER extraction:")
    print(f"  Entities: {entities_before} -> {entities_after} (+{entities_after - entities_before})")
    print(f"  Relations: {relations_before} -> {relations_after} (+{relations_after - relations_before})")
    print()
    print(f"Extraction totals:")
    print(f"  Entities created: {total_entities_created}")
    print(f"  Entities linked: {total_entities_linked}")
    print(f"  Relations created: {total_relations_created}")
    print()

    # Detailed statistics
    print("="*80)
    print("DETAILED STATISTICS")
    print("="*80 + "\n")

    # Entity category breakdown
    cursor.execute('''
        SELECT er.ui_category_id, COUNT(*) as count
        FROM entity_revisions er
        WHERE er.is_current = 1
        GROUP BY er.ui_category_id
        ORDER BY count DESC
    ''')
    print("Entities by category:")
    for row in cursor.fetchall():
        category = row[0] or "uncategorized"
        count = row[1]
        print(f"  {category}: {count}")
    print()

    # Relation type breakdown
    cursor.execute('''
        SELECT rr.kind, COUNT(*) as count
        FROM relation_revisions rr
        WHERE rr.is_current = 1
        GROUP BY rr.kind
        ORDER BY count DESC
    ''')
    print("Relations by type:")
    for row in cursor.fetchall():
        kind = row[0] or "untyped"
        count = row[1]
        print(f"  {kind}: {count}")
    print()

    # Most connected entities
    cursor.execute('''
        SELECT e.id, er.slug, COUNT(DISTINCT rrr.relation_revision_id) as connection_count
        FROM entities e
        JOIN entity_revisions er ON e.id = er.entity_id
        JOIN relation_role_revisions rrr ON e.id = rrr.entity_id
        WHERE er.is_current = 1
        GROUP BY e.id, er.slug
        ORDER BY connection_count DESC
        LIMIT 10
    ''')
    print("Most connected entities (top 10):")
    for i, row in enumerate(cursor.fetchall(), 1):
        entity_id, slug, count = row
        print(f"  {i}. {slug}: {count} relations")
    print()

    conn.close()

    print("="*80)
    print("BATCH EXTRACTION COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(batch_extract())
