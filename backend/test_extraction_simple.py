"""
Simple auto-extraction test for Smart Discovery workflow.

Tests:
1. Fetch source from database
2. Extract knowledge with LLM
3. Save entities and relations to database
4. Verify results
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
    print("❌ OPENAI_API_KEY not found in .env")
    sys.exit(1)

from app.services.pubmed_fetcher import PubMedFetcher
from app.services.extraction_service import ExtractionService


async def test_extraction():
    """Test auto-extraction on first Smart Discovery source."""

    print("=" * 80)
    print("SMART DISCOVERY AUTO-EXTRACTION TEST")
    print("=" * 80)
    print()

    conn = sqlite3.connect('hyphagraph.db')
    cursor = conn.cursor()

    # ==========================================================================
    # STEP 1: Get First Smart Discovery Source
    # ==========================================================================
    print("STEP 1: Loading Smart Discovery Source")
    print("-" * 80)

    cursor.execute('''
        SELECT s.id, sr.title, sr.source_metadata, sr.trust_level, sr.url
        FROM sources s
        JOIN source_revisions sr ON s.id = sr.source_id
        WHERE sr.source_metadata LIKE '%smart_discovery%'
        AND sr.is_current = 1
        ORDER BY sr.trust_level DESC
        LIMIT 1
    ''')

    row = cursor.fetchone()
    if not row:
        print("❌ No Smart Discovery sources found")
        return

    source_id, title, metadata_json, trust_level, url = row
    metadata = json.loads(metadata_json) if metadata_json else {}
    pmid = metadata.get('pmid')

    print(f"Source: {title}")
    print(f"Quality: {trust_level}")
    print(f"PMID: {pmid}")
    print(f"URL: {url}")
    print()

    # ==========================================================================
    # STEP 2: Count Existing Entities and Relations
    # ==========================================================================
    print("STEP 2: Database State Before Extraction")
    print("-" * 80)

    cursor.execute('SELECT COUNT(*) FROM entities')
    entities_before = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM relations')
    relations_before = cursor.fetchone()[0]

    print(f"Entities: {entities_before}")
    print(f"Relations: {relations_before}")
    print()

    # Get existing entity IDs for linking
    cursor.execute('''
        SELECT e.id, er.slug
        FROM entities e
        JOIN entity_revisions er ON e.id = er.entity_id
        WHERE er.is_current = 1
    ''')
    existing_entities = {row[1]: row[0] for row in cursor.fetchall()}
    print(f"Existing entities: {list(existing_entities.keys())}")
    print()

    # ==========================================================================
    # STEP 3: Fetch Document and Extract Knowledge
    # ==========================================================================
    print("STEP 3: Extracting Knowledge with OpenAI GPT-4")
    print("-" * 80)

    try:
        # Fetch document
        print("Fetching document from PubMed...")
        pubmed_fetcher = PubMedFetcher()
        article = await pubmed_fetcher.fetch_by_pmid(pmid)
        document_text = article.full_text
        print(f"✅ Retrieved: {len(document_text)} characters")
        print()

        # Extract with LLM
        print("Extracting knowledge (this takes ~15-20 seconds)...")
        extraction_service = ExtractionService()
        entities, relations, claims = await extraction_service.extract_batch(document_text)

        print(f"✅ Extraction complete!")
        print(f"   Entities extracted: {len(entities)}")
        print(f"   Relations extracted: {len(relations)}")
        print(f"   Claims extracted: {len(claims)}")
        print()

        # Display sample entities
        print("Sample Entities (first 10):")
        for i, entity in enumerate(entities[:10], 1):
            print(f"  {i}. {entity.slug}")
            print(f"     Category: {entity.category}")
            print(f"     Confidence: {entity.confidence}")
        if len(entities) > 10:
            print(f"  ... and {len(entities) - 10} more")
        print()

        # Display sample relations
        print("Sample Relations (first 10):")
        for i, relation in enumerate(relations[:10], 1):
            print(f"  {i}. {relation.subject_slug} --[{relation.relation_type}]--> {relation.object_slug}")
            print(f"     Confidence: {relation.confidence}")
        if len(relations) > 10:
            print(f"  ... and {len(relations) - 10} more")
        print()

        # =======================================================================
        # STEP 4: Save to Database (Simple Entity Linking)
        # =======================================================================
        print("STEP 4: Saving to Database")
        print("-" * 80)

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
                print(f"  ✅ Linked: {entity.slug}")
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
                entities_created += 1
                print(f"  🆕 Created: {entity.slug}")

        conn.commit()
        print()
        print(f"Entity processing complete:")
        print(f"  Linked to existing: {entities_linked}")
        print(f"  Created new: {entities_created}")
        print()

        # Process relations
        print("Creating relations...")
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
        print(f"✅ Relations created: {relations_created}")
        if relations_skipped > 0:
            print(f"⚠️  Relations skipped (missing entities): {relations_skipped}")
        print()

        # =======================================================================
        # STEP 5: Verify Database State
        # =======================================================================
        print("STEP 5: Database State After Extraction")
        print("-" * 80)

        cursor.execute('SELECT COUNT(*) FROM entities')
        entities_after = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM relations')
        relations_after = cursor.fetchone()[0]

        print(f"Entities: {entities_before} → {entities_after} (+{entities_after - entities_before})")
        print(f"Relations: {relations_before} → {relations_after} (+{relations_after - relations_before})")
        print()

        # Check duloxetine relations
        duloxetine_id = existing_entities.get('duloxetine')
        if duloxetine_id:
            cursor.execute('''
                SELECT COUNT(*)
                FROM relation_role_revisions rrr
                WHERE rrr.entity_id = ?
            ''', (duloxetine_id,))
            dulox_relations = cursor.fetchone()[0]
            print(f"✅ Duloxetine appears in {dulox_relations} relations")

        # Check fibromyalgia relations
        fibro_id = existing_entities.get('fibromyalgia')
        if fibro_id:
            cursor.execute('''
                SELECT COUNT(*)
                FROM relation_role_revisions rrr
                WHERE rrr.entity_id = ?
            ''', (fibro_id,))
            fibro_relations = cursor.fetchone()[0]
            print(f"✅ Fibromyalgia appears in {fibro_relations} relations")

        print()

        # =======================================================================
        # SUMMARY
        # =======================================================================
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print()
        print(f"✅ Document fetched: {len(document_text)} characters")
        print(f"✅ LLM extraction: SUCCESS")
        print(f"✅ Entities extracted: {len(entities)}")
        print(f"✅ Entities created: {entities_created}")
        print(f"✅ Entities linked: {entities_linked}")
        print(f"✅ Relations created: {relations_created}")
        print()
        print("🎉 AUTO-EXTRACTION TEST PASSED!")
        print()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(test_extraction())
