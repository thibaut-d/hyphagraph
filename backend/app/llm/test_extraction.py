"""
Test script for knowledge extraction with LLM.

Demonstrates entity and relation extraction from sample medical text.

Run with:
    uv run python -m app.llm.test_extraction
"""
import asyncio
import json
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.llm.client import get_llm_provider
from app.llm.prompts import (
    MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
    format_entity_extraction_prompt,
    format_relation_extraction_prompt,
    format_batch_extraction_prompt,
)
from app.llm.schemas import (
    validate_entity_extraction,
    validate_relation_extraction,
    validate_batch_extraction,
)


# Sample medical text for testing
SAMPLE_TEXT = """
Aspirin (acetylsalicylic acid) is a nonsteroidal anti-inflammatory drug (NSAID)
commonly used for pain relief, fever reduction, and as an antiplatelet agent.
In a randomized controlled trial, low-dose aspirin (75-100mg daily) was shown
to reduce the risk of myocardial infarction by 25% in adults with cardiovascular
disease (RR 0.75, 95% CI 0.68-0.82, p<0.001).

However, aspirin use is associated with an increased risk of gastrointestinal
bleeding, particularly at higher doses or with prolonged use. The absolute risk
increase is approximately 0.5-1% per year in the general population.

Aspirin is contraindicated in children with viral infections due to the risk of
Reye's syndrome. For migraine headaches, aspirin at doses of 900-1000mg has shown
efficacy comparable to NSAIDs like ibuprofen, with pain relief typically occurring
within 2 hours of administration.
"""


async def test_entity_extraction():
    """Test entity extraction from sample text."""
    print("=" * 80)
    print("Testing Entity Extraction")
    print("=" * 80)

    llm = get_llm_provider()

    prompt = format_entity_extraction_prompt(SAMPLE_TEXT)

    print(f"\nExtracting entities from sample text...")
    print(f"Text length: {len(SAMPLE_TEXT)} characters\n")

    try:
        # Get LLM response
        response_data = await llm.generate_json(
            prompt=prompt,
            system_prompt=MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=2000,
        )

        # Validate response
        validated = validate_entity_extraction(response_data)

        print(f"✓ Extracted {len(validated.entities)} entities:\n")

        for i, entity in enumerate(validated.entities, 1):
            print(f"{i}. {entity.slug}")
            print(f"   Category: {entity.category}")
            print(f"   Summary: {entity.summary}")
            print(f"   Confidence: {entity.confidence}")
            print(f"   Text span: \"{entity.text_span}\"")
            print()

        return validated.entities

    except Exception as e:
        print(f"❌ Entity extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return []


async def test_relation_extraction(entities: list):
    """Test relation extraction given extracted entities."""
    print("=" * 80)
    print("Testing Relation Extraction")
    print("=" * 80)

    if not entities:
        print("❌ No entities provided, skipping relation extraction")
        return []

    llm = get_llm_provider()

    # Convert entities to dict format for prompt
    entities_dict = [
        {
            "slug": e.slug,
            "summary": e.summary,
            "category": e.category
        }
        for e in entities
    ]

    prompt = format_relation_extraction_prompt(SAMPLE_TEXT, entities_dict)

    print(f"\nExtracting relations between {len(entities)} entities...\n")

    try:
        # Get LLM response
        response_data = await llm.generate_json(
            prompt=prompt,
            system_prompt=MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=2000,
        )

        # Validate response
        validated = validate_relation_extraction(response_data)

        print(f"✓ Extracted {len(validated.relations)} relations:\n")

        for i, rel in enumerate(validated.relations, 1):
            print(f"{i}. {rel.subject_slug} → [{rel.relation_type}] → {rel.object_slug}")
            print(f"   Confidence: {rel.confidence}")
            if rel.roles:
                print(f"   Roles: {json.dumps(rel.roles, indent=6)}")
            print(f"   Text span: \"{rel.text_span}\"")
            if rel.notes:
                print(f"   Notes: {rel.notes}")
            print()

        return validated.relations

    except Exception as e:
        print(f"❌ Relation extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return []


async def test_batch_extraction():
    """Test batch extraction (entities + relations + claims in one pass)."""
    print("=" * 80)
    print("Testing Batch Extraction (All-in-One)")
    print("=" * 80)

    llm = get_llm_provider()

    prompt = format_batch_extraction_prompt(SAMPLE_TEXT)

    print(f"\nPerforming batch extraction on sample text...\n")

    try:
        # Get LLM response
        response_data = await llm.generate_json(
            prompt=prompt,
            system_prompt=MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=3000,
        )

        # Validate response
        validated = validate_batch_extraction(response_data)

        print(f"✓ Batch extraction complete!\n")
        print(f"   Entities: {len(validated.entities)}")
        print(f"   Relations: {len(validated.relations)}")
        print(f"   Claims: {len(validated.claims)}\n")

        # Show sample outputs
        if validated.entities:
            print("Sample Entity:")
            e = validated.entities[0]
            print(f"  - {e.slug} ({e.category})")
            print(f"    {e.summary}\n")

        if validated.relations:
            print("Sample Relation:")
            r = validated.relations[0]
            print(f"  - {r.subject_slug} → {r.relation_type} → {r.object_slug}")
            print(f"    \"{r.text_span}\"\n")

        if validated.claims:
            print("Sample Claim:")
            c = validated.claims[0]
            print(f"  - {c.claim_text}")
            print(f"    Type: {c.claim_type}, Evidence: {c.evidence_strength}\n")

        return validated

    except Exception as e:
        print(f"❌ Batch extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all extraction tests."""
    print("\n" + "=" * 80)
    print("LLM Knowledge Extraction Test Suite")
    print("=" * 80)
    print(f"\nSample Text:\n{SAMPLE_TEXT}\n")

    # Test 1: Entity extraction
    entities = await test_entity_extraction()
    print()

    # Test 2: Relation extraction (using entities from test 1)
    relations = await test_relation_extraction(entities)
    print()

    # Test 3: Batch extraction (all-in-one)
    batch_result = await test_batch_extraction()
    print()

    print("=" * 80)
    if entities or relations or batch_result:
        print("✅ Knowledge extraction tests completed successfully!")
    else:
        print("❌ Some tests failed - check output above")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
