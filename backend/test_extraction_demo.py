"""
Simple demonstration of the entity extraction API endpoint.

This script shows the LLM-based knowledge extraction working end-to-end.
"""
import httpx
import json

# Configuration
BASE_URL = "http://localhost"  # Through Caddy on port 80
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "changeme123"

# Sample medical text
SAMPLE_TEXT = """
Aspirin (acetylsalicylic acid) is a nonsteroidal anti-inflammatory drug (NSAID)
commonly used to treat pain, fever, and inflammation. It is also used in low doses
to prevent heart attacks and strokes in patients with cardiovascular disease.

Common side effects include stomach irritation and increased bleeding risk.
Aspirin works by irreversibly inhibiting cyclooxygenase (COX) enzymes, which
are involved in prostaglandin synthesis.
"""

def main():
    print("=" * 80)
    print("HYPHAGRAPH ENTITY EXTRACTION DEMONSTRATION")
    print("=" * 80)

    # Step 1: Authenticate
    print("\n1. Authenticating...")
    with httpx.Client() as client:
        login_response = client.post(
            f"{BASE_URL}/api/auth/login",
            data={
                "username": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        login_response.raise_for_status()
        token = login_response.json()["access_token"]
    print("   [OK] Authentication successful")

    # Step 2: Check extraction service status
    print("\n2. Checking extraction service status...")
    with httpx.Client() as client:
        status_response = client.get(
            f"{BASE_URL}/api/extract/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        status_response.raise_for_status()
        status = status_response.json()
    print(f"   Status: {status['status']}")
    print(f"   Provider: {status['provider']}")
    print(f"   Model: {status['model']}")
    print(f"   Available: {status['available']}")

    # Step 3: Extract entities from sample text
    print("\n3. Extracting entities from sample medical text...")
    print(f"\n   Text to analyze:\n   {SAMPLE_TEXT.strip()}\n")

    with httpx.Client(timeout=30.0) as client:
        extraction_response = client.post(
            f"{BASE_URL}/api/extract/entities",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "text": SAMPLE_TEXT,
                "min_confidence": "medium"
            }
        )
        extraction_response.raise_for_status()
        result = extraction_response.json()

    print(f"   [OK] Extracted {result['count']} entities:\n")

    for entity in result["entities"]:
        print(f"   • {entity['slug']}")
        print(f"     Category: {entity['category']}")
        print(f"     Confidence: {entity['confidence']}")
        print(f"     Summary: {entity['summary'][:80]}...")
        print(f"     Text span: \"{entity['text_span']}\"")
        print()

    print("=" * 80)
    print("[OK] ENTITY EXTRACTION WORKING SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
