"""
Test the combined upload-and-extract endpoint.

This endpoint combines document upload and extraction in a single request.
"""
import httpx
import io

BASE_URL = "http://localhost"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "changeme123"

# Simple medical text
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

print("=" * 70)
print("COMBINED UPLOAD + EXTRACT ENDPOINT TEST")
print("=" * 70)

# Authenticate
print("\n[1/3] Authenticating...")
with httpx.Client() as client:
    r = client.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    r.raise_for_status()
    token = r.json()["access_token"]
print("      OK Authenticated")

# Create source
print("\n[2/3] Creating source...")
with httpx.Client() as client:
    r = client.post(
        f"{BASE_URL}/api/sources/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "kind": "study",
            "title": "Combined Endpoint Test - Aspirin Study",
            "url": "https://example.com/combined-test",
            "trust_level": 0.9
        }
    )
    r.raise_for_status()
    source_id = r.json()["id"]
print(f"      OK Source created: {source_id}")

# Upload AND extract in one request!
print("\n[3/3] Uploading document and extracting knowledge (combined)...")
file = ("aspirin.txt", io.BytesIO(SAMPLE_TEXT.encode('utf-8')), "text/plain")
with httpx.Client(timeout=90.0) as client:
    r = client.post(
        f"{BASE_URL}/api/sources/{source_id}/upload-and-extract",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": file}
    )
    r.raise_for_status()
    result = r.json()

print(f"      OK Upload and extraction complete!")
print(f"\n      Results:")
print(f"        Entities extracted: {result['entity_count']}")
print(f"        Relations extracted: {result['relation_count']}")

# Show link suggestions
exact_matches = [s for s in result['link_suggestions'] if s['match_type'] == 'exact']
synonym_matches = [s for s in result['link_suggestions'] if s['match_type'] == 'synonym']
new_entities = [s for s in result['link_suggestions'] if s['match_type'] == 'none']

print(f"\n      Link Suggestions:")
print(f"        Exact matches: {len(exact_matches)}")
print(f"        Synonym matches: {len(synonym_matches)}")
print(f"        New entities: {len(new_entities)}")

# Show some extracted entities
if result['entities']:
    print(f"\n      Sample Entities:")
    for entity in result['entities'][:3]:
        match = next((s for s in result['link_suggestions'] if s['extracted_slug'] == entity['slug']), None)
        match_info = f" (matches: {match['matched_entity_slug']})" if match and match['match_type'] != 'none' else " (new)"
        print(f"        • {entity['slug']} ({entity['category']}){match_info}")
        print(f"          {entity['summary'][:70]}...")

# Show some relations
if result['relations']:
    print(f"\n      Sample Relations:")
    for relation in result['relations'][:3]:
        print(f"        • {relation['subject_slug']} --[{relation['relation_type']}]--> {relation['object_slug']}")

print("\n" + "=" * 70)
print("SUCCESS! Combined endpoint working perfectly!")
print("=" * 70)
print(f"\nThe endpoint successfully:")
print(f"  1. Uploaded the document")
print(f"  2. Extracted text from the file")
print(f"  3. Stored document in source")
print(f"  4. Extracted {result['entity_count']} entities and {result['relation_count']} relations")
print(f"  5. Found {len(exact_matches) + len(synonym_matches)} matches to existing entities")
print(f"\nYou can now use POST /sources/{source_id}/save-extraction to save to graph!")
