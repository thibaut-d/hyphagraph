"""
Test script for extraction API endpoints.

Tests the entity extraction service through the API.
"""
import asyncio
import httpx
import json


BASE_URL = "http://localhost"  # Use port 80 (Caddy), not 8000 (internal API port)
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "changeme123"

# Sample medical text for testing
SAMPLE_TEXT = """
Aspirin (acetylsalicylic acid) is a nonsteroidal anti-inflammatory drug (NSAID)
commonly used to treat pain, fever, and inflammation. It is also used in low doses
to prevent heart attacks and strokes in patients with cardiovascular disease.

Common side effects include stomach irritation and increased bleeding risk.
Aspirin works by irreversibly inhibiting cyclooxygenase (COX) enzymes, which
are involved in prostaglandin synthesis.

Clinical studies have shown that daily aspirin therapy reduces the risk of
myocardial infarction by approximately 25% in adults with coronary artery disease.
"""


async def get_auth_token() -> str:
    """Authenticate and get access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            data={
                "username": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["access_token"]


async def test_extraction_status(token: str):
    """Test the extraction service status endpoint."""
    print("\n=== Testing Extraction Service Status ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/extract/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()

        print(f"Status: {data['status']}")
        print(f"Provider: {data['provider']}")
        print(f"Model: {data['model']}")
        print(f"Available: {data['available']}")

        assert data["available"], "Extraction service should be available"
        print("[OK] Status endpoint working")


async def test_entity_extraction(token: str):
    """Test entity extraction endpoint."""
    print("\n=== Testing Entity Extraction ===")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/extract/entities",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "text": SAMPLE_TEXT,
                "min_confidence": "medium",
            },
        )
        response.raise_for_status()
        data = response.json()

        print(f"\nExtracted {data['count']} entities from {data['text_length']} characters")
        print(f"\nEntities:")
        for entity in data["entities"]:
            print(f"  - {entity['slug']} ({entity['category']})")
            print(f"    Summary: {entity['summary'][:80]}...")
            print(f"    Confidence: {entity['confidence']}")
            print(f"    Text span: \"{entity['text_span']}\"")
            print()

        # Validate response structure
        assert "entities" in data
        assert "count" in data
        assert data["count"] == len(data["entities"])
        assert data["count"] > 0, "Should extract at least one entity"

        # Validate entity structure
        for entity in data["entities"]:
            assert "slug" in entity
            assert "summary" in entity
            assert "category" in entity
            assert "confidence" in entity
            assert "text_span" in entity
            assert entity["confidence"] in ["high", "medium", "low"]
            assert entity["category"] in [
                "drug", "disease", "symptom", "biological_mechanism",
                "treatment", "biomarker", "population", "outcome", "other"
            ]

        print("[OK] Entity extraction working")
        return data["entities"]


async def test_relation_extraction(token: str, entities: list):
    """Test relation extraction endpoint."""
    print("\n=== Testing Relation Extraction ===")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/extract/relations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "text": SAMPLE_TEXT,
                "entities": entities,
                "min_confidence": "medium",
            },
        )
        response.raise_for_status()
        data = response.json()

        print(f"\nExtracted {data['count']} relations")
        print(f"\nRelations:")
        for relation in data["relations"]:
            print(f"  - {relation['subject_slug']} --[{relation['relation_type']}]--> {relation['object_slug']}")
            print(f"    Confidence: {relation['confidence']}")
            print(f"    Text span: \"{relation['text_span'][:80]}...\"")
            if relation.get('notes'):
                print(f"    Notes: {relation['notes']}")
            print()

        # Validate response structure
        assert "relations" in data
        assert "count" in data
        assert data["count"] == len(data["relations"])

        # Validate relation structure
        for relation in data["relations"]:
            assert "subject_slug" in relation
            assert "relation_type" in relation
            assert "object_slug" in relation
            assert "confidence" in relation
            assert "text_span" in relation
            assert relation["confidence"] in ["high", "medium", "low"]

        print("[OK] Relation extraction working")


async def test_batch_extraction(token: str):
    """Test batch extraction endpoint."""
    print("\n=== Testing Batch Extraction ===")

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/extract/batch",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "text": SAMPLE_TEXT,
                "min_confidence": "medium",
                "min_evidence_strength": "moderate",
            },
        )
        response.raise_for_status()
        data = response.json()

        print(f"\nBatch extraction results:")
        print(f"  Entities: {data['entity_count']}")
        print(f"  Relations: {data['relation_count']}")
        print(f"  Claims: {data['claim_count']}")
        print(f"  Text length: {data['text_length']}")

        # Validate response structure
        assert "entities" in data
        assert "relations" in data
        assert "claims" in data
        assert "entity_count" in data
        assert "relation_count" in data
        assert "claim_count" in data

        print("[OK] Batch extraction working")


async def main():
    """Run all extraction API tests."""
    try:
        print("Authenticating...")
        token = await get_auth_token()
        print("[OK] Authentication successful")

        # Test status endpoint
        await test_extraction_status(token)

        # Test entity extraction
        entities = await test_entity_extraction(token)

        # Test relation extraction (using entities from previous step)
        await test_relation_extraction(token, entities)

        # Test batch extraction
        await test_batch_extraction(token)

        print("\n" + "="*60)
        print("[OK] All extraction API tests passed!")
        print("="*60)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
