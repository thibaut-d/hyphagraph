"""
Test the complete document → extraction → linking → storage pipeline.

Full end-to-end test:
1. Create source
2. Upload document
3. Extract entities/relations with link suggestions
4. Save to graph
5. Verify data in graph
"""
import httpx
import io

# Configuration
BASE_URL = "http://localhost"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "changeme123"

# Sample medical document
SAMPLE_DOCUMENT = """
Metformin in Type 2 Diabetes: Clinical Overview

Metformin is the first-line pharmacological treatment for type 2 diabetes mellitus.
As a biguanide medication, it primarily works by reducing hepatic glucose production
and increasing insulin sensitivity in peripheral tissues.

Mechanism of Action:
Metformin activates AMP-activated protein kinase (AMPK), a key regulator of cellular
energy homeostasis. This activation inhibits gluconeogenesis in the liver and enhances
glucose uptake in skeletal muscle, leading to improved glycemic control.

Clinical Efficacy:
The UKPDS (United Kingdom Prospective Diabetes Study) demonstrated that metformin
reduces HbA1c levels by 1-2% and decreases the risk of myocardial infarction by 39%
in overweight patients with type 2 diabetes. Unlike sulfonylureas, metformin does
not cause weight gain and has a low risk of hypoglycemia.

Side Effects:
Common adverse effects include gastrointestinal disturbances (nausea, diarrhea,
abdominal discomfort) affecting 20-30% of patients. These symptoms typically
resolve with dose titration. Long-term use may lead to vitamin B12 deficiency.

The most serious but rare complication is lactic acidosis, particularly in patients
with renal impairment or conditions predisposing to tissue hypoxia.

Contraindications:
- Severe renal impairment (eGFR < 30 mL/min/1.73m²)
- Acute metabolic acidosis
- Severe hepatic impairment
- Conditions associated with tissue hypoxia

Dosing:
Initial: 500mg once or twice daily with meals
Maintenance: 1000-2000mg daily in divided doses
Maximum: 2550mg daily
"""


def main():
    print("=" * 80)
    print("FULL KNOWLEDGE EXTRACTION PIPELINE TEST")
    print("=" * 80)

    # Step 1: Authenticate
    print("\n[1/6] Authenticating...")
    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/api/auth/login",
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        token = response.json()["access_token"]
    print("      OK Authenticated")

    # Step 2: Create source
    print("\n[2/6] Creating source...")
    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/api/sources/",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "kind": "review",
                "title": "Metformin in Type 2 Diabetes: Clinical Overview",
                "authors": ["Thompson A", "Zhang L"],
                "year": 2024,
                "origin": "Clinical Diabetes Review",
                "url": "https://example.com/metformin-review",
                "trust_level": 0.85
            }
        )
        response.raise_for_status()
        source = response.json()
        source_id = source["id"]
    print(f"      OK Source created: {source_id}")

    # Step 3: Upload document
    print("\n[3/6] Uploading document...")
    file = ("metformin_review.txt", io.BytesIO(SAMPLE_DOCUMENT.encode('utf-8')), "text/plain")
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{BASE_URL}/api/sources/{source_id}/upload-document",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": file}
        )
        response.raise_for_status()
        upload_result = response.json()
    print(f"      OK Document uploaded ({upload_result['character_count']} chars)")

    # Step 4: Extract with linking suggestions
    print("\n[4/6] Extracting entities and relations with link suggestions...")
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{BASE_URL}/api/sources/{source_id}/extract-from-document",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        extraction = response.json()

    print(f"      OK Extracted {extraction['entity_count']} entities and {extraction['relation_count']} relations")
    print(f"\n      Entities:")
    for entity in extraction['entities'][:5]:  # Show first 5
        print(f"        • {entity['slug']} ({entity['category']}) - {entity['summary'][:60]}...")

    print(f"\n      Relations:")
    for relation in extraction['relations'][:5]:  # Show first 5
        print(f"        • {relation['subject_slug']} --[{relation['relation_type']}]--> {relation['object_slug']}")

    print(f"\n      Link Suggestions:")
    exact_matches = [s for s in extraction['link_suggestions'] if s['match_type'] == 'exact']
    synonym_matches = [s for s in extraction['link_suggestions'] if s['match_type'] == 'synonym']
    new_entities = [s for s in extraction['link_suggestions'] if s['match_type'] == 'none']
    print(f"        • Exact matches: {len(exact_matches)}")
    print(f"        • Synonym matches: {len(synonym_matches)}")
    print(f"        • New entities: {len(new_entities)}")

    # Step 5: Save to graph
    # For this test, we'll create all as new entities (no linking to existing)
    print("\n[5/6] Saving extraction to knowledge graph...")

    save_request = {
        "source_id": source_id,
        "entities_to_create": extraction['entities'],
        "entity_links": {},  # No links for this test (all new entities)
        "relations_to_create": extraction['relations']
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{BASE_URL}/api/sources/{source_id}/save-extraction",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=save_request
        )
        response.raise_for_status()
        save_result = response.json()

    print(f"      OK Saved to graph:")
    print(f"        • Entities created: {save_result['entities_created']}")
    print(f"        • Entities linked: {save_result['entities_linked']}")
    print(f"        • Relations created: {save_result['relations_created']}")

    # Step 6: Verify data in graph
    print("\n[6/6] Verifying data in knowledge graph...")

    # Get some created entities
    if save_result['created_entity_ids']:
        entity_id = save_result['created_entity_ids'][0]
        with httpx.Client() as client:
            response = client.get(
                f"{BASE_URL}/api/entities/{entity_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            entity = response.json()
        print(f"      OK Sample entity retrieved: {entity['slug']}")
        print(f"        Summary: {entity['summary'][:80]}...")

    # Get some created relations
    if save_result['created_relation_ids']:
        relation_id = save_result['created_relation_ids'][0]
        with httpx.Client() as client:
            response = client.get(
                f"{BASE_URL}/api/relations/{relation_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            relation = response.json()
        print(f"      OK Sample relation retrieved")
        print(f"        Type: {relation['relation_type']}")
        print(f"        Confidence: {relation['confidence_level']}")

    # Summary
    print("\n" + "=" * 80)
    print("OK FULL PIPELINE TEST PASSED!")
    print("=" * 80)
    print(f"\nResults:")
    print(f"  Source ID: {source_id}")
    print(f"  Entities created: {save_result['entities_created']}")
    print(f"  Relations created: {save_result['relations_created']}")
    print(f"\nThe knowledge from the document has been successfully extracted and")
    print(f"integrated into the graph!")


if __name__ == "__main__":
    main()
