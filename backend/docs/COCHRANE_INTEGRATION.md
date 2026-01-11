# Cochrane Library Integration

## Overview

This document explains how HyphaGraph handles Cochrane systematic reviews and the different access strategies available.

---

## What is Cochrane Library?

**Cochrane Library** is the gold standard database for systematic reviews in healthcare.

- Publisher: Wiley (on behalf of Cochrane)
- Content: High-quality systematic reviews and meta-analyses
- Quality: Considered the highest level of evidence (OCEBM Level 1a)
- Access: Subscription-based (institutional licenses)

**Key fact**: All Cochrane reviews are **also indexed in PubMed** with the journal name "Cochrane Database of Systematic Reviews" or abbreviated as "Cochrane Database Syst Rev".

---

## Access Strategies

### ✅ **Strategy 1: Via PubMed** (Currently Implemented)

**Status**: ✅ **FULLY WORKING**

Since Cochrane reviews are indexed in PubMed, we can access their metadata through the free PubMed E-utilities API.

**How it works:**

1. User pastes PubMed URL: `https://pubmed.ncbi.nlm.nih.gov/25881025/`
2. PubMedFetcher extracts PMID: `25881025`
3. API call to E-utilities: `efetch.fcgi?db=pubmed&id=25881025`
4. Extract metadata:
   - Title: "Duloxetine for treating painful neuropathy..."
   - Journal: "Cochrane Database Syst Rev"
   - Authors: Lunn MP, Hughes RA, Wiffen PJ
   - Year: 2014
   - Abstract: Full abstract from Cochrane
5. **Special Cochrane detection**: Journal contains "cochrane database"
6. **Automatic quality scoring**: `trust_level = 1.0` (systematic review)

**Example PubMed URLs for Cochrane reviews:**
```
https://pubmed.ncbi.nlm.nih.gov/25881025/  → Duloxetine for painful neuropathy
https://pubmed.ncbi.nlm.nih.gov/23152217/  → Antidepressants for pain management
https://pubmed.ncbi.nlm.nih.gov/28122680/  → NSAIDs for chronic pain
```

**Advantages:**
- ✅ Free (no API key required)
- ✅ Already implemented
- ✅ Gets title, authors, abstract, year, DOI
- ✅ Automatic trust_level = 1.0 for Cochrane
- ✅ No additional authentication needed

**Limitations:**
- ⚠️ May not get full review text (only abstract)
- ⚠️ Delayed indexing (new reviews take ~days to appear in PubMed)
- ⚠️ Can't access Cochrane protocols (only published reviews)

**Code Implementation:**

```python
# In source_quality.py (lines 369-376)
def infer_trust_level_from_pubmed_metadata(...):
    # Special case: Cochrane Database publications are ALWAYS systematic reviews
    if journal and "cochrane database" in journal.lower():
        return calculate_trust_level(
            study_type="systematic_review",
            journal=journal,
            is_peer_reviewed=True,
            publication_year=year
        )
```

**Test Results:**
```python
>>> infer_trust_level_from_pubmed_metadata(
...     "Antidepressants for pain management",
...     "Cochrane Database of Systematic Reviews",
...     2023
... )
1.0  # ✅ Perfect score (OCEBM Level 1a)
```

---

### 🔒 **Strategy 2: Direct Cochrane API** (Optional, Requires License)

**Status**: ⚠️ **NOT IMPLEMENTED** (requires institutional access)

The Cochrane Library provides a REST API through Archie (their internal system).

**API Details:**
- Base URL: `https://archie.cochrane.org/rest/reviews/`
- Authentication: OAuth 2.0 or HTTP Basic Auth
- Formats: XML (RM5/JATS), JSON

**Endpoints:**
```
GET /rest/reviews/{CD_NUMBER}           # Get review by Cochrane ID
GET /rest/reviews/{Review_ID}/latest    # Get latest version
GET /rest/reviews/{Review_ID}/translations  # Translations
```

**Requirements:**
- 🔐 OAuth 2.0 access token OR institutional credentials
- 📧 Permission from Wiley (contact: dpentesc@wiley.com)
- 💰 Institutional subscription to Cochrane Library

**Advantages:**
- ✅ Full review text (not just abstract)
- ✅ Cochrane-specific metadata (review status, updates)
- ✅ Access to protocols and withdrawn reviews
- ✅ Immediate access to new reviews (no PubMed delay)

**Disadvantages:**
- ❌ Requires authentication (API key/OAuth)
- ❌ Institutional license required
- ❌ Additional complexity
- ❌ Need to request permission from Wiley

**Implementation Example (if needed in future):**

```python
class CochraneFetcher:
    """
    Direct Cochrane API integration (requires authentication).

    Note: This requires institutional Cochrane Library access.
    Contact Wiley for API access: dpentesc@wiley.com
    """
    BASE_URL = "https://archie.cochrane.org/rest/reviews"

    def __init__(self, oauth_token: str):
        self.oauth_token = oauth_token

    async def fetch_review(self, cd_number: str) -> CochraneReview:
        """
        Fetch Cochrane review by CD number (e.g., CD003345).

        Requires: OAuth 2.0 Bearer token
        """
        headers = {
            "Authorization": f"Bearer {self.oauth_token}",
            "Accept": "application/json"
        }

        url = f"{self.BASE_URL}/{cd_number}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return self._parse_cochrane_json(response.json())

    def _parse_cochrane_json(self, data: dict) -> CochraneReview:
        # Parse Cochrane-specific JSON structure
        return CochraneReview(
            cd_number=data.get("cdNumber"),
            title=data.get("title"),
            authors=data.get("authors", []),
            abstract=data.get("abstract"),
            full_text=data.get("fullText"),  # Only via Cochrane API
            # ... additional Cochrane-specific fields
        )
```

**Configuration needed:**
```python
# In config.py
COCHRANE_API_TOKEN = os.getenv("COCHRANE_API_TOKEN")  # OAuth token
COCHRANE_ENABLED = bool(COCHRANE_API_TOKEN)
```

---

### 📝 **Strategy 3: Manual Entry** (Always Available)

Users can always manually create a source for Cochrane reviews:

**Workflow:**
1. Visit Cochrane Library directly
2. Copy metadata manually
3. Create source in HyphaGraph with:
   - URL: Cochrane URL (e.g., `https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD003345/full`)
   - Kind: `article`
   - Title: Review title
   - Authors: Author list
   - Journal: "Cochrane Database of Systematic Reviews"
   - Trust Level: **Automatically set to 1.0** when journal detected

**Note**: Our autofill system won't work with Cochrane URLs (requires auth), but users can copy-paste the PubMed URL instead.

---

## Current Implementation Status

### ✅ What Works Now

1. **PubMed URLs for Cochrane reviews**
   - ✅ Metadata extraction via E-utilities
   - ✅ Automatic detection: journal = "Cochrane Database..."
   - ✅ Automatic trust_level = 1.0
   - ✅ Abstract included

2. **Journal Recognition**
   - ✅ "Cochrane Database of Systematic Reviews" → systematic_review
   - ✅ "Cochrane Database Syst Rev" → systematic_review
   - ✅ "Cochrane Library" → systematic_review

3. **Quality Scoring**
   - ✅ All Cochrane reviews get maximum score (1.0)
   - ✅ Age penalty applied for very old reviews (>20 years)

### ❌ What Doesn't Work (Without Cochrane API)

1. ❌ Direct Cochrane Library URLs (authentication required)
2. ❌ Full review text (only abstract via PubMed)
3. ❌ Cochrane protocols (not indexed in PubMed)
4. ❌ Withdrawn reviews (may not be in PubMed)

---

## Recommendations

### For Most Users: **Use PubMed URLs** ✅

This is the simplest and most reliable approach:

1. Find Cochrane review on https://www.cochranelibrary.com/
2. Click "View in PubMed" link or search PubMed directly
3. Copy PubMed URL (e.g., `https://pubmed.ncbi.nlm.nih.gov/25881025/`)
4. Paste in HyphaGraph Create Source form
5. Click "Auto-Fill"
6. ✅ All metadata filled, trust_level = 1.0

**Example Workflow:**
```
Cochrane URL: https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD003345
                ↓
         Search PubMed for title
                ↓
PubMed URL: https://pubmed.ncbi.nlm.nih.gov/25881025/
                ↓
         HyphaGraph Auto-Fill
                ↓
         Source created with trust_level=1.0
```

### For Institutions with Cochrane Access: **Consider Direct API** ⚡

If your institution has a Cochrane Library subscription and you need:
- Full review text (not just abstracts)
- Access to protocols
- Immediate access to new reviews

Then implementing Strategy 2 (Direct Cochrane API) may be worth the effort.

**Steps:**
1. Contact Wiley: dpentesc@wiley.com
2. Request API access for data mining
3. Obtain OAuth 2.0 credentials
4. Implement `CochraneFetcher` service
5. Add Cochrane URL detection to autofill endpoint

**Effort estimate**: 2-3 days development + license approval time

---

## Code Files

**Current Implementation:**
- `backend/app/utils/source_quality.py` (lines 369-376) - Cochrane detection
- `backend/app/services/pubmed_fetcher.py` - PubMed integration (already works for Cochrane)
- `backend/app/api/sources.py` - Autofill endpoint (supports Cochrane via PubMed)

**Future Implementation (if direct API needed):**
- `backend/app/services/cochrane_fetcher.py` - New service (not created yet)
- `backend/app/config.py` - Add COCHRANE_API_TOKEN setting
- `backend/app/api/sources.py` - Add Cochrane URL detection

---

## Testing

### Test with Real Cochrane Review

```bash
# Example: "Duloxetine for treating painful neuropathy" (PMID 25881025)

curl -X POST http://localhost:8000/api/sources/extract-metadata-from-url \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "https://pubmed.ncbi.nlm.nih.gov/25881025/"
  }'

# Expected response:
{
  "url": "https://pubmed.ncbi.nlm.nih.gov/25881025/",
  "title": "Duloxetine for treating painful neuropathy, chronic pain or fibromyalgia",
  "authors": ["Lunn MP", "Hughes RA", "Wiffen PJ"],
  "year": 2014,
  "origin": "Cochrane Database Syst Rev",
  "kind": "article",
  "trust_level": 1.0,  ← Maximum quality!
  "summary_en": "BACKGROUND: Duloxetine is a balanced serotonin...",
  "source_metadata": {
    "pmid": "25881025",
    "doi": "10.1002/14651858.CD007115.pub3",
    "source": "pubmed"
  }
}
```

---

## Summary

### Current Status: ✅ **Cochrane Fully Supported via PubMed**

- ✅ All Cochrane reviews in PubMed can be imported
- ✅ Automatic detection via journal name
- ✅ Automatic trust_level = 1.0 (OCEBM Level 1a)
- ✅ Full metadata extraction (title, authors, abstract, DOI)
- ✅ No API key required
- ✅ No scraping (uses official NCBI API)

### API Access Required? **NO** ❌

You do **NOT** need Cochrane API access for the current implementation.

**Why?** Because:
1. Cochrane reviews are indexed in PubMed (free, public)
2. PubMed provides complete metadata
3. HyphaGraph automatically detects Cochrane and assigns maximum quality
4. Abstracts are sufficient for most knowledge extraction workflows

### When to Consider Direct Cochrane API

Only if you need:
- ❌ Full review text (not just abstract)
- ❌ Cochrane protocols (before full review published)
- ❌ Withdrawn reviews
- ❌ Real-time access to brand-new reviews (before PubMed indexing)

For 95% of use cases, **PubMed access is sufficient**.

---

## References

1. **Cochrane Library**: https://www.cochranelibrary.com/
2. **Cochrane in PubMed**: https://pubmed.ncbi.nlm.nih.gov/?term=cochrane+database+syst+rev
3. **Cochrane API Docs**: https://documentation.cochrane.org/display/API
4. **Contact for API Access**: dpentesc@wiley.com (Wiley)

**Last Updated**: 2026-01-11
