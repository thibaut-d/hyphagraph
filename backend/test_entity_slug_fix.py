"""
Test script to verify entity_slug is populated in inference API responses
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost"
FIBROMYALGIA_ENTITY_ID = "de334806-3edc-40c3-8b82-8e4c05f29481"

# Test credentials
TEST_USER = "admin@example.com"
TEST_PASSWORD = "changeme123"

def test_inference_api():
    """Test that inference API returns entity_slug in roles"""

    print("=" * 60)
    print("Testing Inference API - Entity Slug Fix")
    print("=" * 60)

    # Step 1: Login
    print("\n1. Logging in...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data={"username": TEST_USER, "password": TEST_PASSWORD}
        )

        if response.status_code != 200:
            print(f"✗ Login failed: {response.status_code}")
            return False

        token = response.json().get("access_token")
        print(f"✓ Login successful")

    except Exception as e:
        print(f"✗ Login error: {str(e)}")
        return False

    # Step 2: Get inference for fibromyalgia entity
    print(f"\n2. Getting inference for entity {FIBROMYALGIA_ENTITY_ID}...")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            f"{BASE_URL}/api/inferences/entity/{FIBROMYALGIA_ENTITY_ID}",
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print(f"✗ Inference API failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

        data = response.json()
        print(f"✓ Inference API successful")

    except Exception as e:
        print(f"✗ Inference API error: {str(e)}")
        return False

    # Step 3: Check if entity_slug is present in roles
    print("\n3. Checking if entity_slug is populated in roles...")

    relations_by_kind = data.get("relations_by_kind", {})

    if not relations_by_kind:
        print("⚠ No relations found")
        return True

    total_roles = 0
    roles_with_slug = 0
    sample_relations = []

    for kind, relations in relations_by_kind.items():
        for relation in relations:
            roles = relation.get("roles", [])

            for role in roles:
                total_roles += 1
                if role.get("entity_slug"):
                    roles_with_slug += 1

                # Collect sample for display
                if len(sample_relations) < 3:
                    sample_relations.append({
                        "kind": kind,
                        "role_type": role.get("role_type"),
                        "entity_id": role.get("entity_id"),
                        "entity_slug": role.get("entity_slug"),
                    })

    print(f"\nResults:")
    print(f"  Total roles: {total_roles}")
    print(f"  Roles with entity_slug: {roles_with_slug}")
    print(f"  Percentage: {(roles_with_slug/total_roles*100):.1f}%")

    print(f"\nSample relations:")
    for i, sample in enumerate(sample_relations, 1):
        print(f"\n  {i}. {sample['kind']}")
        print(f"     Role Type: {sample['role_type']}")
        print(f"     Entity ID: {sample['entity_id']}")
        print(f"     Entity Slug: {sample['entity_slug'] or 'MISSING'}")

    # Step 4: Verify success
    print("\n" + "=" * 60)
    if roles_with_slug == total_roles:
        print("✓ SUCCESS: All roles have entity_slug populated!")
        print("=" * 60)
        return True
    elif roles_with_slug > 0:
        print(f"⚠ PARTIAL: {roles_with_slug}/{total_roles} roles have entity_slug")
        print("=" * 60)
        return False
    else:
        print("✗ FAILED: No roles have entity_slug populated")
        print("=" * 60)
        return False

if __name__ == "__main__":
    test_inference_api()
