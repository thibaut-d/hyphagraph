"""
Auto-extraction script for Smart Discovery sources.

Extracts knowledge from all imported sources using OpenAI GPT-4.
Creates entities and relations automatically with entity linking.

Requirements:
- OPENAI_API_KEY in .env
- Database with imported sources
- Existing entities (duloxetine, fibromyalgia)
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

# Load environment (try .env first, then .env.test)
load_dotenv('.env')
if not os.getenv('OPENAI_API_KEY'):
    load_dotenv('.env.test')

# Check for OpenAI key
if not os.getenv('OPENAI_API_KEY'):
    print("❌ OPENAI_API_KEY not found in .env")
    print("Please add your OpenAI API key to .env file")
    sys.exit(1)

from app.services.pubmed_fetcher import PubMedFetcher
from app.services.extraction_service import ExtractionService
from app.services.entity_linking_service import EntityLinkingService


async def run_extraction():
    """Execute auto-extraction on all smart discovery sources."""

    print("=" * 80)
    print("AUTO-EXTRACTION: Smart Discovery Sources → Knowledge Graph")
    print("=" * 80)
    print()

    conn = sqlite3.connect('hyphagraph.db')
    cursor = conn.cursor()

    # ==========================================================================
    # STEP 1: Get Smart Discovery Sources
    # ==========================================================================
    print("STEP 1: Loading Smart Discovery Sources")
    print("-" * 80)

    cursor.execute('''
        SELECT s.id, sr.title, sr.source_metadata, sr.trust_level
        FROM sources s
        JOIN source_revisions sr ON s.id = sr.source_id
        WHERE sr.source_metadata LIKE '%smart_discovery%'
        AND sr.is_current = 1
        ORDER BY sr.trust_level DESC
    ''')

    sources = []
    for row in cursor.fetchall():
        source_id, title, metadata_json, trust_level = row
        metadata = json.loads(metadata_json) if metadata_json else {}
        pmid = metadata.get('pmid')

        if pmid:
            sources.append({
                'id': source_id,
                'title': title,
                'pmid': pmid,
                'trust_level': trust_level
            })

    print(f"✅ Found {len(sources)} sources with PMIDs")
    print()

    if not sources:
        print("⚠️  No sources found. Run test_complete_workflow.py first.")
        return

    # ==========================================================================
    # STEP 2: Initialize Services
    # ==========================================================================
    print("STEP 2: Initializing Services")
    print("-" * 80)

    pubmed_fetcher = PubMedFetcher()
    extraction_service = ExtractionService()
    linking_service = EntityLinkingService()

    print("✅ PubMedFetcher initialized")
    print("✅ ExtractionService initialized (OpenAI GPT-4)")
    print("✅ EntityLinkingService initialized")
    print()

    # ==========================================================================
    # STEP 3: Get Existing Entities for Linking
    # ==========================================================================
    print("STEP 3: Loading Existing Entities")
    print("-" * 80)

    cursor.execute('''
        SELECT e.id, er.slug
        FROM entities e
        JOIN entity_revisions er ON e.id = er.entity_id
        WHERE er.is_current = 1
    ''')

    existing_entities = {row[1]: row[0] for row in cursor.fetchall()}
    print(f"✅ Loaded {len(existing_entities)} existing entities:")
    for slug in existing_entities.keys():
        print(f"   - {slug}")
    print()

    # ==========================================================================
    # STEP 4: Extract from First Source (Test)
    # ==========================================================================
    print("STEP 4: Test Extraction on First Source")
    print("-" * 80)

    test_source = sources[0]
    print(f"Source: {test_source['title'][:70]}...")
    print(f"Quality: {test_source['trust_level']}")
    print(f"PMID: {test_source['pmid']}")
    print()

    try:
        # Fetch document
        print("Fetching document from PubMed...")
        article = await pubmed_fetcher.fetch_by_pmid(test_source['pmid'])
        document_text = article.full_text
        print(f"✅ Document retrieved: {len(document_text)} characters")
        print()

        # Extract with LLM
        print("Extracting knowledge with GPT-4 (this may take 15-20 seconds)...")
        batch_result = await extraction_service.extract_batch(document_text)

        print(f"✅ Extraction complete!")
        print(f"   Entities: {len(batch_result.entities)}")
        print(f"   Relations: {len(batch_result.relations)}")
        print()

        # Display entities
        print("Extracted Entities (first 10):")
        for i, entity in enumerate(batch_result.entities[:10], 1):
            print(f"  {i}. {entity.slug} ({entity.category})")
            print(f"     Confidence: {entity.confidence}")
        if len(batch_result.entities) > 10:
            print(f"  ... and {len(batch_result.entities) - 10} more")
        print()

        # Display relations
        print("Extracted Relations (first 10):")
        for i, relation in enumerate(batch_result.relations[:10], 1):
            print(f"  {i}. {relation.subject_slug} → {relation.relation_type} → {relation.object_slug}")
            print(f"     Evidence: {relation.evidence_strength}, Confidence: {relation.confidence}")
        if len(batch_result.relations) > 10:
            print(f"  ... and {len(batch_result.relations) - 10} more")
        print()

        # Entity linking
        print("Performing Entity Linking...")
        entities_to_create = []
        entity_links = {}
        new_entity_ids = {}

        for entity in batch_result.entities:
            # Check if entity already exists
            if entity.slug in existing_entities:
                print(f"  ✅ Linking: {entity.slug} → existing entity")
                entity_links[entity.slug] = existing_entities[entity.slug]
            else:
                # Check for similar entities
                matches = await linking_service.find_matches(
                    entity.slug,
                    entity.summary
                )

                if matches and matches[0].match_type in ["exact", "synonym"]:
                    print(f"  ✅ Linking: {entity.slug} → {matches[0].matched_slug} ({matches[0].match_type})")
                    entity_links[entity.slug] = matches[0].matched_entity_id
                else:
                    # Create new entity
                    entity_id = str(uuid.uuid4())
                    entity_rev_id = str(uuid.uuid4())
                    now = datetime.utcnow().isoformat()

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

                    entities_to_create.append(entity.slug)
                    new_entity_ids[entity.slug] = entity_id
                    entity_links[entity.slug] = entity_id

                    print(f"  🆕 Creating: {entity.slug}")

        conn.commit()

        print()
        print(f"✅ Entity linking complete:")
        print(f"   Linked to existing: {len([v for k, v in entity_links.items() if k in existing_entities])}")
        print(f"   Created new: {len(entities_to_create)}")
        print()

        # Create relations
        print("Creating Relations...")
        relations_created = 0

        for relation in batch_result.relations:
            # Get entity IDs
            subject_id = entity_links.get(relation.subject_slug)
            object_id = entity_links.get(relation.object_slug)

            if not subject_id or not object_id:
                print(f"  ⚠️  Skipping relation (missing entity): {relation.subject_slug} → {relation.object_slug}")
                continue

            # Create relation
            relation_id = str(uuid.uuid4())
            relation_rev_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            # Determine direction
            direction = "supports"  # Default
            if relation.relation_type in ["causes", "increases_risk"]:
                direction = "contradicts"

            cursor.execute('INSERT INTO relations (id, source_id, created_at) VALUES (?, ?, ?)',
                           (relation_id, test_source['id'], now))

            cursor.execute('''
                INSERT INTO relation_revisions (
                    id, relation_id, kind, direction, confidence, notes, is_current, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                relation_rev_id, relation_id, relation.relation_type,
                direction, 0.8, None, 1, now
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
        print()

        # =======================================================================
        # STEP 5: Verification
        # =======================================================================
        print("STEP 5: Verification")
        print("-" * 80)

        cursor.execute('SELECT COUNT(*) FROM entities')
        total_entities = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM relations')
        total_relations = cursor.fetchone()[0]

        print(f"Database state:")
        print(f"  Entities: {total_entities} (was 2, added {len(entities_to_create)})")
        print(f"  Relations: {total_relations} (was 0, added {relations_created})")
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
        # SUCCESS
        # =======================================================================
        print("=" * 80)
        print("EXTRACTION TEST SUMMARY")
        print("=" * 80)
        print()
        print(f"✅ Document fetched: {len(document_text)} chars")
        print(f"✅ LLM extraction: SUCCESS")
        print(f"✅ Entities extracted: {len(batch_result.entities)}")
        print(f"✅ Entities created: {len(entities_to_create)}")
        print(f"✅ Entities linked: {len([k for k in entity_links if k in existing_entities])}")
        print(f"✅ Relations created: {relations_created}")
        print()
        print("🎉 AUTO-EXTRACTION WORKING!")
        print()
        print(f"To extract remaining {len(sources) - 1} sources:")
        print(f"  - Estimated time: {(len(sources) - 1) * 20} seconds (~{(len(sources) - 1) * 20 // 60} minutes)")
        print(f"  - Would create: ~{len(entities_to_create) * len(sources)} entities")
        print(f"  - Would create: ~{relations_created * len(sources)} relations")

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(run_extraction())
