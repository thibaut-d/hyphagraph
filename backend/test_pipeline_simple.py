"""Test the pipeline with simple aspirin text."""
import httpx
import io

BASE_URL = "http://localhost"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "changeme123"

# Use the simpler aspirin text
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

print("=" * 60)
print("PIPELINE TEST: Upload -> Extract -> Link -> Save")
print("=" * 60)

# Authenticate
with httpx.Client() as client:
    r = client.post(f"{BASE_URL}/api/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    r.raise_for_status()
    token = r.json()["access_token"]
print("\n[1/5] OK Authenticated")

# Create source
with httpx.Client() as client:
    r = client.post(f"{BASE_URL}/api/sources/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "kind": "study",
            "title": "Aspirin Clinical Overview",
            "url": "https://example.com/aspirin",
            "trust_level": 0.9
        })
    r.raise_for_status()
    source_id = r.json()["id"]
print(f"[2/5] OK Source created: {source_id}")

# Upload document
file = ("aspirin.txt", io.BytesIO(SAMPLE_TEXT.encode('utf-8')), "text/plain")
with httpx.Client(timeout=30.0) as client:
    r = client.post(f"{BASE_URL}/api/sources/{source_id}/upload-document",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": file})
    r.raise_for_status()
print(f"[3/5] OK Document uploaded ({r.json()['character_count']} chars)")

# Extract with linking
with httpx.Client(timeout=60.0) as client:
    r = client.post(f"{BASE_URL}/api/sources/{source_id}/extract-from-document",
        headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    extraction = r.json()
print(f"[4/5] OK Extracted {extraction['entity_count']} entities, {extraction['relation_count']} relations")
print(f"      Link suggestions: {len([s for s in extraction['link_suggestions'] if s['match_type'] != 'none'])} matches")

# Save to graph
save_req = {
    "source_id": source_id,
    "entities_to_create": extraction['entities'],
    "entity_links": {},
    "relations_to_create": extraction['relations']
}
with httpx.Client(timeout=60.0) as client:
    r = client.post(f"{BASE_URL}/api/sources/{source_id}/save-extraction",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=save_req)
    r.raise_for_status()
    result = r.json()
print(f"[5/5] OK Saved: {result['entities_created']} entities, {result['relations_created']} relations")

print("\n" + "=" * 60)
print("SUCCESS! Full pipeline working end-to-end")
print("=" * 60)
