# Human-in-the-Loop Review System Implementation

**Status**: Core infrastructure complete, integration pending
**Date**: 2026-03-07 (Session 4)

## Overview

This system provides **optional** human review of LLM extractions before committing them to the knowledge graph. The key design principle is that high-confidence, well-validated extractions can auto-commit, while uncertain extractions are staged for review.

## Architecture

### Database Layer

**New Table**: `staged_extractions`
- Stores pending LLM extractions with validation metadata
- Tracks review status (pending → approved/rejected → materialized)
- Links to source documents and materialized entities/relations
- Migration: `002_add_staged_extractions.py`

**Model**: `app.models.staged_extraction.StagedExtraction`
- Fields: extraction_type, status, extraction_data (JSON), validation_score, confidence_adjustment, validation_flags
- Relationships: source, reviewer, materialized_entity, materialized_relation
- Auto-commit metadata: auto_commit_eligible, auto_commit_threshold

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

**Auto-Commit Logic**:
```python
def _is_auto_commit_eligible(validation_result):
    if not auto_commit_enabled:
        return False
    if validation_score < threshold (default 0.9):
        return False
    if require_no_flags and len(flags) > 0:
        return False
    return True
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

## Integration Points

### 1. Extraction Service (PENDING)

**File**: `app.services.extraction_service.py`

**Required Changes**:
1. Add `ExtractionReviewService` initialization
2. After validation, check `auto_commit_eligible`
3. If eligible: materialize immediately
4. If not eligible: stage for review
5. Add configuration for auto-commit behavior

### 2. Document Extraction API (PENDING)

**File**: `app.api.document_extraction.py`

**Required Changes**:
1. Return staged extraction IDs in response
2. Add flag to indicate if extractions were auto-committed or staged
3. Provide review URL for staged extractions

### 3. Frontend (FUTURE)

**Components Needed**:
- ReviewQueue view - List pending extractions
- ExtractionReviewCard - Display extraction with approve/reject buttons
- ReviewStats dashboard - Overview of pending reviews
- BatchReview interface - Select multiple extractions

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

### High-Confidence Extraction (Auto-Commit)

1. LLM extracts entity: `duloxetine` with text_span: "Duloxetine is an FDA-approved medication"
2. Validation: exact match found, validation_score=1.0, no flags
3. Auto-commit check: score >= 0.9, no flags → **ELIGIBLE**
4. System auto-approves and materializes entity
5. Entity appears in knowledge graph immediately

### Low-Confidence Extraction (Staged for Review)

1. LLM extracts relation with text_span not found in source
2. Validation: validation_score=0.5, flags=["text_span_not_found"]
3. Auto-commit check: score < 0.9 → **NOT ELIGIBLE**
4. System stages extraction for human review
5. Human reviews, sees validation flags, can approve/reject
6. If approved: materialized to knowledge graph
7. If rejected: stays in rejected state

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

✅ **Scientific honesty** - Humans can review uncertain extractions
✅ **Traceability** - Staged extractions link to source documents
✅ **Explainability** - Validation scores and flags explain why staged
✅ **Progressive disclosure** - Auto-commit hides complexity for high-quality extractions
✅ **AI constraint** - LLMs are workers, humans make final decisions on uncertain cases

## Notes

- The system is **optional by design** - high-confidence extractions bypass review
- Review is **async** - extractions can be verified after initial auto-commit if needed
- The system is **transparent** - validation scores/flags help humans make decisions
- The system is **efficient** - batch operations prevent review bottlenecks
