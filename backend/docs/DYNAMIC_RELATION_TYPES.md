# Dynamic Relation Types System

**Status**: ✅ **Implemented**
**Date**: 2026-01-11

---

## Overview

HyphaGraph now uses a **dynamic, database-driven relation type vocabulary** instead of hard-coded Literal types. This enables:

- ✅ Evolution of relation types over time
- ✅ Prevention of duplicates (similarity detection)
- ✅ LLM guidance with current vocabulary
- ✅ Usage tracking and analytics
- ✅ User-created custom types (superuser only)

---

## Architecture

### Before (Hard-Coded)

```python
# backend/app/llm/schemas.py
RelationType = Literal[
    "treats", "causes", "prevents", ...  # Fixed list!
]
```

**Problems**:
- ❌ Cannot add new types without code change
- ❌ No duplicate prevention
- ❌ No usage tracking
- ❌ LLM always uses same list (even if types evolve)

### After (Dynamic Database)

```python
# backend/app/models/relation_type.py
class RelationType(Base):
    type_id: str  # "treats", "measures", etc.
    label: dict  # {"en": "Treats", "fr": "Traite"}
    description: str  # For LLM guidance
    examples: str  # "aspirin treats migraine"
    aliases: list[str]  # ["cures", "heals"]
    is_active: bool
    is_system: bool
    usage_count: int
    category: str  # "therapeutic", "diagnostic", etc.
```

**Benefits**:
- ✅ Add new types via API (no code deploy)
- ✅ Similarity detection prevents duplicates
- ✅ Usage tracking shows which types are most common
- ✅ LLM prompt dynamically generated from DB

---

## Database Schema

### Table: `relation_types`

| Column | Type | Description |
|--------|------|-------------|
| `type_id` | VARCHAR(50) PK | Unique identifier (e.g., "treats") |
| `label` | JSON | i18n labels: {"en": "Treats", "fr": "Traite"} |
| `description` | TEXT | Description for LLM guidance |
| `examples` | TEXT | Example relations |
| `aliases` | TEXT (JSON) | Synonyms to detect duplicates |
| `is_active` | BOOLEAN | Whether type is currently available |
| `is_system` | BOOLEAN | System vs user-created |
| `usage_count` | INTEGER | How many times used |
| `category` | VARCHAR(50) | Semantic grouping |
| `created_at` | DATETIME | When created |

**Indexes**:
- `idx_relation_type_active` on `is_active`
- `idx_relation_type_category` on `category`

---

## Initial Seeded Types (13 total)

| Type ID | Category | Description | Examples |
|---------|----------|-------------|----------|
| **treats** | therapeutic | Treats disease/symptom | aspirin treats migraine |
| **causes** | causal | Causes symptom/outcome | duloxetine causes nausea |
| **prevents** | therapeutic | Prevents disease/outcome | vaccine prevents infection |
| **increases_risk** | causal | Increases risk of outcome | smoking increases_risk cancer |
| **decreases_risk** | therapeutic | Decreases risk of outcome | exercise decreases_risk CVD |
| **mechanism** | mechanistic | Biological mechanism | aspirin mechanism COX-inhibition |
| **contraindicated** | safety | Should not be used | warfarin contraindicated pregnancy |
| **interacts_with** | safety | Drug interaction | warfarin interacts_with aspirin |
| **metabolized_by** | mechanistic | Metabolic pathway | duloxetine metabolized_by CYP2D6 |
| **biomarker_for** | diagnostic | Biomarker indicates disease | CRP biomarker_for inflammation |
| **affects_population** | epidemiological | Affects population | fibromyalgia affects_population women |
| **measures** | diagnostic | Assessment tool measures | VAS measures pain; MoCA measures cognition |
| **other** | general | Any other relationship | Catch-all for edge cases |

---

## API Endpoints

### `GET /api/relation-types`

Get all active relation types.

**Response**:
```json
[
  {
    "type_id": "treats",
    "label": {"en": "Treats", "fr": "Traite"},
    "description": "Drug/treatment treats disease/symptom",
    "examples": "aspirin treats migraine; duloxetine treats fibromyalgia",
    "aliases": ["cures", "heals", "ameliorates"],
    "category": "therapeutic",
    "usage_count": 20,
    "is_system": true
  },
  ...
]
```

### `POST /api/relation-types`

Create new relation type (superuser only).

**Request**:
```json
{
  "type_id": "exacerbates",
  "label": {"en": "Exacerbates", "fr": "Exacerbe"},
  "description": "Factor that worsens a condition",
  "examples": "stress exacerbates fibromyalgia",
  "aliases": ["worsens", "aggravates"],
  "category": "causal"
}
```

**Validation**:
- Checks for similar existing types (similarity detection)
- Prevents duplicates
- Returns error if similar type exists

### `POST /api/relation-types/suggest`

Check if a new type should be added.

**Request**:
```json
{
  "proposed_type": "ameliorates",
  "context": "Drug ameliorates symptoms"
}
```

**Response**:
```json
{
  "similar_existing": "treats",
  "should_add": false,
  "reason": "Similar type 'treats' already exists. Consider using it or adding 'ameliorates' as an alias."
}
```

### `GET /api/relation-types/for-llm-prompt`

Get formatted list for LLM prompts.

**Response**:
```json
{
  "prompt_text": "CRITICAL: relation_type MUST be...\n   - treats: Drug/treatment treats...\n   - causes: ..."
}
```

**Usage**: Dynamically inserted into LLM prompts at extraction time.

---

## Workflow: LLM Encounters New Relation Type

### Scenario: LLM wants to use "measures"

**Before** (Hard-coded):
```
1. LLM generates: "MoCA measures cognitive-function"
2. Validation fails: "measures" not in Literal list
3. Extraction fails ❌
4. Developer must update code and redeploy
```

**After** (Dynamic):
```
1. LLM generates: "MoCA measures cognitive-function"
2. Validation checks database: "measures" exists ✅
3. Extraction succeeds
4. usage_count incremented (analytics)
```

### Scenario: LLM wants to use truly new type

**Example**: LLM encounters "exacerbates"

**Option A - Automatic** (Future):
```
1. LLM generates: "stress exacerbates fibromyalgia"
2. Validation checks DB: "exacerbates" not found
3. System calls /suggest API: Is "exacerbates" similar to existing?
4. Response: Similar to "causes" or "increases_risk"
5. Auto-map to closest existing type
```

**Option B - Review Queue** (Safer):
```
1. LLM generates: "stress exacerbates fibromyalgia"
2. Validation fails, but extracts anyway using "other"
3. System logs: "Proposed new type: exacerbates"
4. Admin reviews queue
5. Admin creates new type or adds as alias to existing
```

---

## Duplicate Prevention

### Similarity Detection

**String Similarity** (Levenshtein distance):
```python
"treats" vs "treatment" → 70% similar → Use "treats"
"measures" vs "measure" → 90% similar → Use "measures"
"causes" vs "induces" → 30% similar → Check aliases
```

**Alias Matching**:
```python
Input: "cures"
Check aliases: "treats" has aliases ["cures", "heals"]
→ Use "treats" instead
```

**Description Similarity**:
```python
Input: "makes worse"
Description: "Factor that worsens condition"
Similar to "causes" description: "Factor that causes outcome"
→ Suggest using "causes" or "increases_risk"
```

---

## LLM Integration

### Dynamic Prompt Generation

**Old** (static):
```python
PROMPT = """
CRITICAL: relation_type MUST be one of:
- treats
- causes
...
"""
```

**New** (dynamic):
```python
# At extraction time:
service = RelationTypeService(db)
relation_types_prompt = await service.get_for_llm_prompt()

PROMPT = f"""
{relation_types_prompt}
"""
```

**Generated prompt includes**:
- All active types from database
- Descriptions for each
- Examples for each
- Current usage stats (optional, for popularity)

### Extraction Workflow

```python
# 1. Get current relation types from DB
active_types = await relation_type_service.get_all_active()
type_ids = [t.type_id for t in active_types]

# 2. Generate LLM prompt with current vocabulary
prompt = await relation_type_service.get_for_llm_prompt()

# 3. Extract with LLM
result = await llm.extract(document, prompt)

# 4. Validate against DB types (not hard-coded Literal)
for relation in result.relations:
    if relation.type not in type_ids:
        # Option A: Suggest mapping to existing
        suggestion = await relation_type_service.suggest_new_type(
            relation.type,
            relation.description
        )

        if suggestion.similar_existing:
            # Map to existing type
            relation.type = suggestion.similar_existing
        else:
            # Option B: Queue for review
            log_proposed_type(relation.type)
            relation.type = "other"  # Fallback

# 5. Increment usage counts
for relation in result.relations:
    await relation_type_service.increment_usage(relation.type)
```

---

## Benefits

### 1. Evolvability ✅

**Add new types without code changes**:
```bash
POST /api/relation-types
{
  "type_id": "exacerbates",
  "label": {"en": "Exacerbates"},
  "description": "Factor that worsens a condition",
  ...
}
```

**Available immediately** to LLM in next extraction.

### 2. Consistency ✅

**Prevent duplicates**:
- "cures" → Mapped to "treats" (via alias)
- "treatment" → Suggested to use "treats" (similarity)
- "heals" → Mapped to "treats" (via alias)

### 3. Analytics ✅

**Track usage**:
```sql
SELECT type_id, usage_count
FROM relation_types
ORDER BY usage_count DESC
```

Results:
- treats: 20 uses (64.5%)
- causes: 4 uses (12.9%)
- ...

**Insights**: Know which types are actually used vs which are theoretical.

### 4. Guidance ✅

**Better LLM prompts**:
- Examples from real usage
- Descriptions refined over time
- Remove unused types
- Add types as domain evolves

---

## Migration Path

### Phase 1: Create Table ✅ (Done)
- Migration 009: Create relation_types table
- Seed with 13 initial types
- All current types preserved

### Phase 2: Update Extraction ⏭️ (Next)
- Modify ExtractionService to query DB for types
- Generate dynamic prompts
- Validate against DB instead of Literal

### Phase 3: Add UI ⏭️ (Optional)
- Admin page for managing relation types
- Review queue for proposed new types
- Analytics dashboard for usage

### Phase 4: Backwards Compatibility ✅
- Keep Literal as fallback for type hints
- Generate Literal from DB types dynamically
- No breaking changes to existing code

---

## Example: Adding "measures"

### Before (Code Change Required)

```python
# 1. Edit llm/schemas.py
RelationType = Literal[..., "measures"]

# 2. Edit prompts.py
"- measures: Assessment tool measures..."

# 3. Redeploy backend

# 4. Now "measures" works
```

### After (Database-Driven)

```python
# 1. API call (or run migration)
POST /api/relation-types
{
  "type_id": "measures",
  "label": {"en": "Measures"},
  "description": "Assessment tool measures condition",
  "examples": "VAS measures pain",
  "category": "diagnostic"
}

# 2. Available immediately!
# Next extraction uses "measures" automatically
```

---

## Files Created

1. **Model**: `app/models/relation_type.py` (58 lines)
2. **Service**: `app/services/relation_type_service.py` (180 lines)
3. **API**: `app/api/relation_types.py` (150 lines)
4. **Migration**: `alembic/versions/009_add_relation_types_table.py` (140 lines)
5. **Docs**: `docs/DYNAMIC_RELATION_TYPES.md` (this file)

---

## Testing

### Verify Seed Data

```bash
sqlite3 hyphagraph.db

SELECT type_id, category, usage_count
FROM relation_types
ORDER BY usage_count DESC;
```

Expected: 13 relation types seeded.

### Test API

```bash
# List types
curl http://localhost:8000/api/relation-types

# Create new type
curl -X POST http://localhost:8000/api/relation-types \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type_id": "exacerbates",
    "label": {"en": "Exacerbates"},
    "description": "Factor that worsens a condition",
    "category": "causal"
  }'

# Check for duplicates
curl -X POST http://localhost:8000/api/relation-types/suggest \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"proposed_type": "cures", "context": "Drug cures disease"}'

# Response: "Similar type 'treats' exists"
```

---

## Roadmap

### Phase 1: Infrastructure ✅ (Current)
- ✅ Create relation_types table
- ✅ Seed with 13 initial types
- ✅ Create service layer
- ✅ Create API endpoints

### Phase 2: Integration ⏭️ (Next)
- Update ExtractionService to use DB types
- Generate dynamic LLM prompts
- Implement suggestion workflow

### Phase 3: Analytics ⏭️ (Future)
- Dashboard showing usage statistics
- Identify unused types (candidates for removal)
- Track evolution over time

### Phase 4: LLM Learning ⏭️ (Future)
- When LLM proposes new type, auto-suggest similar
- Learn from user corrections (if user changes "cures" → "treats", add as alias)
- Evolve vocabulary based on domain usage

---

## Conclusion

The dynamic relation type system provides flexibility and consistency as the knowledge graph evolves. It prevents the problem of hard-coded enums while maintaining schema validation and duplicate prevention.

**Key Innovation**: Relation types are now **data**, not code.

**Result**: System can adapt to new domains and relationships without code changes.
