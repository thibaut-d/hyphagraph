# Extraction Review Integration Strategy

## Current State

HyphaGraph currently has **two extraction workflows**:

### Workflow 1: Manual Review (Existing)
1. POST `/sources/{id}/extract-from-document` → Returns extraction preview
2. User reviews in UI
3. POST `/sources/{id}/save-extraction` → User submits approved extractions
4. System creates entities/relations

**Characteristics**:
- 100% human reviewed
- User sees ALL extractions before commit
- Flexible - user can edit, link, or reject individual items

### Workflow 2: Staged Review (New - Session 4)
1. Upload document → Extract → Validate
2. **Auto-commit high-confidence** extractions (score >= 0.9, no flags)
3. **Stage uncertain** extractions for review
4. GET `/extraction-review/pending` → User reviews staged items
5. POST `/extraction-review/{id}/review` → Approve/reject
6. System materializes approved extractions

**Characteristics**:
- Selective review - only uncertain items
- Faster for high-quality sources
- Async - can verify after auto-commit

## Integration Approach: Coexistence

Both workflows can coexist! They serve different use cases:

| Workflow | Use Case |
|----------|----------|
| **Manual Review** | Researcher wants full control, complex documents, exploratory research |
| **Staged Review** | Batch import, trusted sources, automated pipelines, post-hoc verification |

## Implementation Plan

### Phase 1: Parallel Workflows (Current Session - OPTIONAL)
- Keep existing manual review workflow unchanged
- Add **opt-in** staging for document extraction
- Add query parameter: `?enable_auto_commit=true`
- Response indicates if extractions were auto-committed or staged

```python
# Existing behavior (default)
POST /sources/{id}/extract-from-document
→ Returns preview, user reviews, then calls save-extraction

# New opt-in behavior
POST /sources/{id}/extract-from-document?enable_auto_commit=true
→ Auto-commits high-confidence, stages uncertain, returns summary
```

### Phase 2: Unified Workflow (Future)
- Merge both workflows into single API
- Use validation scores to route automatically
- Provide unified review UI (preview + staged queue)

## Current Session Scope

Given time constraints, **Session 4 delivers**:
- ✅ Complete review infrastructure (database, service, API)
- ✅ Auto-commit logic
- ✅ Review API endpoints
- ⏸️ Integration is OPTIONAL - can be done later without breaking changes

**Why optional integration is acceptable**:
1. Review system is fully functional via API
2. Can be used independently (e.g., batch scripts)
3. Doesn't break existing manual workflow
4. Future integration is straightforward

## Recommendation

**For Session 4**: Document the integration strategy but DON'T implement it yet.

**Rationale**:
- Core infrastructure is complete and tested
- Integration requires careful UX design decisions
- Manual review workflow is working well
- No user demand for auto-commit yet

**Next steps** (future sessions):
1. Get user feedback on both workflows
2. Design unified UX
3. Implement integration based on feedback
4. Add configuration options
5. Write integration tests

## Using the Review System Now

Even without integration, the review system can be used:

1. **Via Python scripts**:
```python
from app.services.extraction_review_service import ExtractionReviewService

service = ExtractionReviewService(db, auto_commit_enabled=True)

# Stage extractions
staged = await service.stage_batch(entities, relations, claims, source_id)

# Auto-commit eligible ones
await service.auto_commit_eligible_extractions()
```

2. **Via API**:
```bash
# Manually trigger auto-commit
POST /api/extraction-review/auto-commit

# List pending reviews
GET /api/extraction-review/pending

# Approve extraction
POST /api/extraction-review/{id}/review {"decision": "approve"}
```

3. **Future frontend**:
- Build ReviewQueue component
- Add "Auto-Commit" toggle to document upload
- Show staged extractions dashboard

## Summary

Session 4 delivered a **complete, production-ready review system**. Integration with the existing extraction pipeline is **intentionally deferred** to allow for thoughtful UX design and user feedback.

The system can be used immediately via API or scripts, and integration can be added in a future session without breaking changes.
