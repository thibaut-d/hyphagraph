# Visibility Strategy for Staged Extractions

## Updated Design Decision (2026-03-07)

**Change**: Make ALL extractions visible immediately, flag uncertain ones for review.

**Rationale**:
- "Verify later" approach - don't block knowledge extraction
- More transparent - users see everything
- Review is async quality control, not a gate
- Aligns with "optional" principle - high-confidence items don't need manual review

## Implementation Approach

### Option 1: Schema Change (Complex)
Add `needs_review` and `verified` flags to entity_revisions/relation_revisions.

**Pros**: Clean, data lives with the entity
**Cons**: Schema migration, affects core tables, more complex queries

### Option 2: Use staged_extractions as Metadata Layer (Simpler) ✅

**CHOSEN APPROACH**: Use existing `staged_extractions` table as review metadata, always materialize.

#### Workflow:
```
1. Extract → Validate
2. ALWAYS materialize to Entity/Relation (immediate visibility)
3. ALWAYS create staged_extraction record with metadata
4. Set status based on validation:
   - validation_score >= 0.9, no flags → status="auto_verified"
   - validation_score < 0.9 OR flags → status="pending"
5. User sees all entities/relations in graph
6. Review queue shows items where status="pending"
7. After human review:
   - Approve → status="approved"
   - Reject → status="rejected" (but entity still exists, flagged)
```

#### Database Schema:
```python
# Existing staged_extraction statuses (extend enum):
- "auto_verified"  # NEW: High confidence, auto-approved
- "pending"        # Needs human review
- "approved"       # Human reviewed and approved
- "rejected"       # Human reviewed and rejected (but materialized)
```

#### Querying:
```sql
-- Get all entities with review status
SELECT e.*, se.status as review_status, se.validation_score
FROM entities e
JOIN entity_revisions er ON e.id = er.entity_id AND er.is_current = true
LEFT JOIN staged_extractions se ON se.materialized_entity_id = e.id

-- Filter to items needing review
WHERE se.status = 'pending'

-- Filter to verified items (either auto or human)
WHERE se.status IN ('auto_verified', 'approved')
```

#### API Response Enhancement:
```json
{
  "id": "entity-uuid",
  "slug": "duloxetine",
  "summary": "...",
  "review_metadata": {
    "status": "pending",
    "validation_score": 0.75,
    "validation_flags": ["fuzzy_match"],
    "needs_review": true
  }
}
```

### Implementation Steps

1. **Update ExtractionStatus enum** - Add "auto_verified" status
2. **Modify review service** - Always materialize, set appropriate status
3. **Update API schemas** - Include review metadata in entity/relation responses
4. **Update frontend** - Show badge/indicator for items needing review
5. **Add filter** - Allow filtering by review status

### Benefits

✅ **Simpler**: No core schema changes
✅ **Flexible**: Easy to add more statuses later
✅ **Audit-friendly**: staged_extractions keeps full history
✅ **Query-efficient**: Can join or not based on need
✅ **Backward-compatible**: Doesn't affect existing entities

### Trade-offs

⚠️ **JOIN overhead**: Need JOIN to get review status
⚠️ **Orphan risk**: If staged_extraction deleted, lose review metadata
⚠️ **Not normalized**: Review metadata separate from entity data

**Mitigation**:
- Use LEFT JOIN (optional review metadata)
- Never delete staged_extractions (audit trail)
- Add index on materialized_entity_id for fast joins

### Frontend UX

```
Entity List View:
┌─────────────────────────────────────────┐
│ Duloxetine ✅                            │
│ A medication for fibromyalgia...        │
│ Auto-verified • Score: 1.0              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Pregabalin ⚠️ Needs Review               │
│ Another medication...                    │
│ Pending review • Score: 0.75 • 1 flag   │
│ [Review Now]                             │
└─────────────────────────────────────────┘

Filter: [All] [Verified] [Needs Review]
```

### Review Queue

Shows same items as graph, but filtered to `status="pending"`:
- Quick approve/reject buttons
- Show validation flags
- Bulk operations

### Migration Path

1. **Phase 1** (Current): Keep hidden workflow, materialize on approval
2. **Phase 2** (Next): Switch to visible workflow, always materialize
3. **Phase 3** (Future): Add frontend indicators and filtering

Can switch phases without breaking changes.

## Summary

**Decision**: Use `staged_extractions` as metadata layer, always materialize entities/relations immediately.

**Key Changes**:
- Add "auto_verified" status to ExtractionStatus enum
- Modify materialization to happen before status check
- Update API to join review metadata
- Add frontend badges/filters

**No schema migration needed** - works with existing tables.
