"""Test with completely new entities."""
import httpx
import io
import time

BASE_URL = "http://localhost"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "changeme123"

# Use unique entities that won't exist yet
SAMPLE_TEXT = f"""
Ibuprofen-{int(time.time())} is a new experimental nonsteroidal anti-inflammatory medication
being tested for treatment of chronic headaches and muscle pain. The medication works by
inhibiting prostaglandin synthesis through COX-enzyme modulation.

Early clinical trials show promising results in reducing chronic-pain-{int(time.time())}
severity by approximately 40% in study participants.
"""

print("=" * 60)
print("PIPELINE TEST: With New Entities")
print("=" * 60)

# Authenticate
with httpx.Client() as client:
    r = client.post(f"{BASE_URL}/api/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    r.raise_for_status()
    token = r.json()["access_token"]
print("[1/5] OK Authenticated")

# Create source
with httpx.Client() as client:
    r = client.post(f"{BASE_URL}/api/sources/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "kind": "study",
            "title": f"Novel Drug Study {int(time.time())}",
            "url": f"https://example.com/study-{int(time.time())}",
            "trust_level": 0.9
        })
    r.raise_for_status()
    source_id = r.json()["id"]
print(f"[2/5] OK Source created")

# Upload
file = ("test.txt", io.BytesIO(SAMPLE_TEXT.encode('utf-8')), "text/plain")
with httpx.Client(timeout=30.0) as client:
    r = client.post(f"{BASE_URL}/api/sources/{source_id}/upload-document",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": file})
    r.raise_for_status()
print(f"[3/5] OK Document uploaded")

# Extract
with httpx.Client(timeout=60.0) as client:
    r = client.post(f"{BASE_URL}/api/sources/{source_id}/extract-from-document",
        headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    extraction = r.json()
print(f"[4/5] OK Extracted {extraction['entity_count']} entities, {extraction['relation_count']} relations")

# Save
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
print("SUCCESS!")
print("=" * 60)
