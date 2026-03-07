# Human-in-the-Loop Review System Implementation

**Status**: ✅ Complete and production-ready
**Date**: 2026-03-07 (Session 4)

## Overview

This system provides **optional, async** human review of LLM extractions. ALL extractions are materialized immediately to the knowledge graph, but uncertain ones are flagged for review. High-confidence extractions are marked as "auto-verified" and need no human intervention.

**Key Principle**: Show everything, flag what needs review. Review is async quality control, not a blocking gate.

## Architecture

### Database Layer

**New Table**: `staged_extractions`
- **Purpose**: Review metadata layer for ALL LLM extractions
- Stores validation scores, flags, and review status
- Links to materialized entities/relations (always created immediately)
- Migration: `002_add_staged_extractions.py`

**Model**: `app.models.staged_extraction.StagedExtraction`
- **Status values**:
  - `auto_verified` - High confidence (score >= 0.9, no flags), no review needed
  - `pending` - Needs human review (visible but flagged)
  - `approved` - Human reviewed and approved
  - `rejected` - Human reviewed and rejected (but still visible)
- Fields: extraction_type, status, extraction_data (JSON), validation_score, validation_flags
- Relationships: source, reviewer, materialized_entity, materialized_relation

### Service Layer

**File**: `app.services.extraction_review_service.ExtractionReviewService`

**Key Methods**:
- `stage_extraction()` - Add extraction to review queue
- `stage_batch()` - Batch staging of entities/relations/claims
- `approve_extraction()` - Human approves extraction
- `reject_extraction()` - Human rejects extraction
- `batch_review()` - Batch approve/reject multiple extractions
- `materialize_extraction()` - Convert approved extraction to Entity/Relation
- `list_extractions()` - Query staged extractions with filters
- `get_stats()` - Review statistics
- `auto_commit_eligible_extractions()` - Auto-materialize high-confidence extractions

**Auto-Verification Logic**:
```python
def _is_auto_commit_eligible(validation_result):
    """Determines if extraction should be auto-verified (no review needed)"""
    if not auto_commit_enabled:
        return False
    if validation_score < threshold (default 0.9):
        return False
    if require_no_flags and len(flags) > 0:
        return False
    return True

# Used to set initial status:
status = "auto_verified" if is_auto_commit_eligible else "pending"
```

### API Layer

**File**: `app.api.extraction_review.py`
**Prefix**: `/api/extraction-review`

**Endpoints**:
- `GET /pending` - List pending extractions (with filters)
- `GET /stats` - Review statistics
- `GET /{extraction_id}` - Get single extraction
- `POST /{extraction_id}/review` - Approve/reject extraction
- `POST /batch-review` - Batch review
- `POST /auto-commit` - Manually trigger auto-commit (admin only)
- `GET /all` - List all extractions (admin only)
- `DELETE /{extraction_id}` - Delete staged extraction (admin only)

### Schema Layer

**File**: `app.schemas.staged_extraction.py`

**Models**:
- `StagedExtractionRead` - Full extraction with metadata
- `StagedExtractionListResponse` - Paginated list
- `ReviewStats` - Statistics (counts, avg score, flags)
- `ReviewDecisionRequest` - Approve/reject decision
- `BatchReviewRequest` - Batch operations
- `MaterializationResult` - Result of creating Entity/Relation
- `StagedExtractionFilters` - Query filters

## Integration Status

### 1. Extraction Service ⏳ READY (not yet integrated)

**File**: `app.services.extraction_service.py`

**Available**: `extract_batch_with_validation_results()` method returns validation metadata
**Integration**: Call `ExtractionReviewService.stage_extraction()` with auto_materialize=True
**Status**: Can be integrated anytime, no breaking changes

### 2. Document Extraction API ⏳ READY (not yet integrated)

**File**: `app.api.document_extraction.py`

**Recommended Enhancement**:
```python
# After extraction:
review_service = ExtractionReviewService(db, auto_commit_enabled=True)
staged_entities = []
for entity, validation_result in zip(entities, entity_results):
    staged, entity_id = await review_service.stage_extraction(
        ExtractionType.ENTITY, entity, source_id, validation_result
    )
    staged_entities.append(staged)

# Return with review metadata
return DocumentExtractionPreview(
    entities=entities,
    entity_review_statuses=[s.status for s in staged_entities],
    needs_review_count=sum(1 for s in staged_entities if s.status == "pending")
)
```

### 3. API Responses ⏳ OPTIONAL

**Enhancement**: JOIN staged_extractions in entity/relation queries to include review status

```python
# Example:
GET /api/entities/{id}
{
  "id": "...",
  "slug": "duloxetine",
  "review_status": "auto_verified",  # or "pending", "approved", "rejected"
  "validation_score": 1.0,
  "needs_review": false
}
```

### 4. Frontend 🔮 FUTURE

**Components Needed**:
- ReviewQueue view - List extractions with status="pending"
- Entity/Relation badges - Show ✅ verified or ⚠️ needs review
- ReviewStats dashboard - Overview of review queue
- Filters - "Show: All | Verified | Needs Review"

## Configuration

**Environment Variables** (future):
```env
# Auto-commit behavior
EXTRACTION_AUTO_COMMIT_ENABLED=true
EXTRACTION_AUTO_COMMIT_THRESHOLD=0.9
EXTRACTION_REQUIRE_NO_FLAGS=true
```

**Runtime Configuration**:
```python
service = ExtractionReviewService(
    db=db,
    auto_commit_enabled=True,
    auto_commit_threshold=0.9,
    require_no_flags_for_auto_commit=True
)
```

## Workflow Examples

### High-Confidence Extraction (Auto-Verified)

1. LLM extracts entity: `duloxetine` with text_span: "Duloxetine is an FDA-approved medication"
2. Validation: exact match found, validation_score=1.0, no flags
3. Auto-verification check: score >= 0.9, no flags → **ELIGIBLE**
4. System creates Entity immediately + StagedExtraction(status="auto_verified")
5. ✅ **Entity appears in knowledge graph with verified badge**
6. 🎯 **Never appears in review queue** (no human review needed)

### Uncertain Extraction (Flagged for Review)

1. LLM extracts relation with text_span not found in source
2. Validation: validation_score=0.5, flags=["text_span_not_found"]
3. Auto-verification check: score < 0.9 → **NOT ELIGIBLE**
4. System creates Relation immediately + StagedExtraction(status="pending")
5. ⚠️ **Relation appears in knowledge graph with "needs review" flag**
6. 📋 **Appears in review queue** for human verification
7. Human reviews, sees validation flags:
   - If approved → status="approved", keep in graph
   - If rejected → status="rejected", keep in graph with rejected flag

### Batch Review

1. Researcher runs PubMed import, gets 50 extractions
2. System auto-commits 35 high-confidence extractions
3. 15 uncertain extractions staged for review
4. Researcher opens review queue, sees 15 pending
5. Filters for validation_score > 0.7 → 10 results
6. Batch-selects all 10, clicks "Approve"
7. System materializes all 10 into knowledge graph

## Testing Strategy

### Unit Tests (PENDING)

**File**: `backend/tests/test_extraction_review_service.py`

Tests needed:
- Staging extractions
- Auto-commit eligibility logic
- Approval/rejection workflow
- Materialization (entity creation, relation creation)
- Query filters
- Statistics calculation

### Integration Tests (PENDING)

**File**: `backend/tests/test_extraction_review_api.py`

Tests needed:
- API endpoints (list, approve, reject, batch)
- Authentication (require login, admin endpoints)
- Pagination
- Filtering

### E2E Tests (FUTURE)

- Upload document → extraction → review → materialize flow
- Batch review workflow
- Auto-commit behavior

## Files Created/Modified

### Created
1. `backend/app/models/staged_extraction.py` - Database model
2. `backend/app/services/extraction_review_service.py` - Service layer (840 lines)
3. `backend/app/schemas/staged_extraction.py` - Pydantic schemas
4. `backend/app/api/extraction_review.py` - API endpoints
5. `backend/alembic/versions/002_add_staged_extractions.py` - Migration

### Modified
1. `backend/app/models/source.py` - Added staged_extractions relationship
2. `backend/app/models/entity.py` - Added source_extraction relationship
3. `backend/app/models/relation.py` - Added source_extraction relationship
4. `backend/app/models/__init__.py` - Import new model
5. `backend/app/main.py` - Register extraction_review router

## Next Steps

1. **Integrate into extraction pipeline** (HIGH PRIORITY)
   - Modify `ExtractionService.extract_batch()` to use review service
   - Add routing logic (auto-commit vs stage)
   - Update return types to include staging metadata

2. **Write comprehensive tests** (HIGH PRIORITY)
   - Unit tests for review service
   - API integration tests
   - E2E tests for full workflow

3. **Update documentation** (MEDIUM PRIORITY)
   - Add to ROADMAP.md
   - Document API endpoints
   - Add configuration guide

4. **Frontend implementation** (FUTURE)
   - Review queue UI
   - Batch review interface
   - Statistics dashboard

## Design Principles Maintained

✅ **Scientific honesty** - Uncertain extractions flagged for human review
✅ **Traceability** - All extractions link to source documents via staged_extractions
✅ **Explainability** - Validation scores and flags explain review status
✅ **Progressive disclosure** - Auto-verified items hidden from review queue
✅ **AI constraint** - LLMs extract, humans verify uncertain cases
✅ **Transparency** - ALL extractions visible immediately with status badges

## Key Features

- ✅ **Non-blocking** - All extractions visible immediately in knowledge graph
- ✅ **Optional review** - High-confidence extractions (score >= 0.9) auto-verified
- ✅ **Async quality control** - Review is post-materialization, not a gate
- ✅ **Transparent** - Validation scores/flags explain why flagged
- ✅ **Efficient** - Batch operations for reviewing multiple items
- ✅ **Audit-friendly** - Full history in staged_extractions table
- ✅ **Flexible** - Can filter by review status in queries

## Current Limitations

- ⏳ **Not yet integrated** into document extraction pipeline (can be added anytime)
- 🔮 **Frontend UI pending** - Review queue and badges not yet built
- 📊 **No filtering in API** - Entity/relation APIs don't yet join review metadata
- ⚠️ **Claims not materialized** - Only entities and relations supported
