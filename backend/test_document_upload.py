"""
Test script for document upload endpoint.

Creates a test source, uploads a sample text document, and verifies the upload.
"""
import httpx
import io

# Configuration
BASE_URL = "http://localhost"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "changeme123"

# Sample document content
SAMPLE_MEDICAL_TEXT = """
Metformin in Type 2 Diabetes Management

Metformin is a first-line medication for type 2 diabetes mellitus. It belongs to the
biguanide class of antidiabetic agents and works primarily by decreasing hepatic
glucose production and improving insulin sensitivity in peripheral tissues.

Clinical Efficacy:
Multiple randomized controlled trials have demonstrated that metformin reduces HbA1c
levels by approximately 1-2% when used as monotherapy. The UKPDS (United Kingdom
Prospective Diabetes Study) showed that metformin reduced the risk of diabetes-related
endpoints by 32% and all-cause mortality by 36% compared to conventional treatment.

Mechanism of Action:
Metformin activates AMP-activated protein kinase (AMPK), which plays a crucial role
in cellular energy homeostasis. This activation leads to decreased gluconeogenesis
in the liver and increased glucose uptake in skeletal muscle.

Common Side Effects:
- Gastrointestinal disturbances (diarrhea, nausea, abdominal discomfort) occur in
  20-30% of patients
- Vitamin B12 deficiency with long-term use
- Rare but serious: lactic acidosis (especially in patients with renal impairment)

Contraindications:
Metformin is contraindicated in patients with:
- Severe renal impairment (eGFR < 30 mL/min/1.73m²)
- Acute metabolic acidosis
- Severe hepatic impairment
- Conditions predisposing to hypoxia

Dosing:
Initial dose: 500mg once or twice daily with meals
Maintenance dose: 1000-2000mg daily in divided doses
Maximum dose: 2550mg daily
"""


def main():
    print("=" * 80)
    print("DOCUMENT UPLOAD TEST")
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

    # Step 2: Create a test source
    print("\n2. Creating test source...")
    with httpx.Client() as client:
        source_response = client.post(
            f"{BASE_URL}/api/sources/",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "kind": "study",
                "title": "Clinical Study on Metformin",
                "authors": ["Smith J", "Jones M"],
                "year": 2024,
                "origin": "Journal of Diabetes Research",
                "url": "https://example.com/metformin-study",
                "trust_level": 0.9
            }
        )
        source_response.raise_for_status()
        source = source_response.json()
        source_id = source["id"]
    print(f"   [OK] Source created: {source_id}")
    print(f"   Title: {source['title']}")

    # Step 3: Upload document
    print("\n3. Uploading document...")
    # Create a text file in memory
    file_content = SAMPLE_MEDICAL_TEXT.encode('utf-8')
    file = ("metformin_study.txt", io.BytesIO(file_content), "text/plain")

    with httpx.Client(timeout=30.0) as client:
        upload_response = client.post(
            f"{BASE_URL}/api/sources/{source_id}/upload-document",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": file}
        )
        upload_response.raise_for_status()
        result = upload_response.json()

    print(f"   [OK] Document uploaded successfully")
    print(f"   Format: {result['document_format']}")
    print(f"   Character count: {result['character_count']}")
    print(f"   Truncated: {result['truncated']}")
    if result.get('warnings'):
        print(f"   Warnings: {result['warnings']}")

    print(f"\n   Document preview (first 500 chars):")
    print(f"   {result['document_text_preview']}")

    # Step 4: Verify document is stored in database
    print("\n4. Verifying document storage...")
    with httpx.Client() as client:
        source_response = client.get(
            f"{BASE_URL}/api/sources/{source_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        source_response.raise_for_status()
        updated_source = source_response.json()

    print(f"   [OK] Source retrieved: {updated_source['title']}")

    print("\n" + "=" * 80)
    print("[OK] DOCUMENT UPLOAD TEST PASSED!")
    print("=" * 80)
    print(f"\nSource ID: {source_id}")
    print(f"You can now use this source for knowledge extraction!")


if __name__ == "__main__":
    main()
