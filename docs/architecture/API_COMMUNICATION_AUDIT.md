# API Communication Audit Report

**Date**: 2026-03-08
**Scope**: Backend-Frontend API Contract Validation
**Status**: Issues Identified - Action Required

---

## Executive Summary

A comprehensive inspection of backend-frontend communication has identified **9 API contract issues** ranging from Critical to Low severity. The most critical issues involve type mismatches that could cause runtime failures in extraction and entity management workflows.

**Key Findings**:
- 2 Critical type mismatches (entity_links, relation roles)
- 1 High severity route duplication (entity terms)
- 2 High severity field naming issues
- 4 Medium/Low compatibility concerns

---

## Critical Issues (Immediate Action Required)

### 1. Entity Links UUID Type Mismatch ⚠️ CRITICAL

**Impact**: Extraction save operations may fail

**Location**:
- Frontend: `frontend/src/types/extraction.ts:137`
- Backend: `backend/app/schemas/source.py:142`

**Problem**:
```typescript
// Frontend expects
entity_links: Record<string, string>;  // extracted_slug -> entity_id (string)

// Backend expects
entity_links: dict[str, UUID]  // extracted_slug -> entity_id (UUID object)
```

**Risk**: When frontend sends string IDs in extraction save, backend may fail UUID validation or require string→UUID coercion. Inconsistent behavior across edge cases.

**Solution**: Standardize on string representation in API, convert to UUID in backend service layer.

---

### 2. Extracted Relation Roles Type Mismatch ⚠️ CRITICAL

**Impact**: Relation extraction may fail validation

**Location**: `frontend/src/types/extraction.ts:62`

**Problem**:
```typescript
// Frontend allows EITHER:
roles: ExtractedRole[] | Record<string, string>;

// Backend expects only:
roles: List[RoleRevisionWrite]
```

**Risk**: If frontend sends `Record<string, string>` format, backend will reject the request.

**Solution**: Remove `Record<string, string>` from frontend type union, enforce array format only.

---

## High Severity Issues

### 3. Entity Terms Route Duplication 🔴 HIGH

**Impact**: Route ambiguity, potential routing errors

**Location**:
- `backend/app/api/entities.py:128-225`
- `backend/app/api/entity_terms.py:14-109`

**Problem**: Entity terms CRUD routes defined in TWO separate files:
1. As sub-routes under `/entities/{id}/terms` in entities.py
2. As separate router in entity_terms.py

Both files include routes like:
- `GET /{entity_id}/terms`
- `POST /{entity_id}/terms`
- `PUT /{entity_id}/terms-bulk`

**Risk**: Duplicate route registration, undefined behavior when both routers loaded.

**Solution**: Consolidate all entity terms routes into single file (entity_terms.py), remove from entities.py.

---

### 4. Source Trust Field Duplication 🔴 HIGH

**Impact**: Frontend code may access undefined field

**Location**: `frontend/src/types/source.ts:10-11`

**Problem**:
```typescript
export interface SourceRead {
  trust_level?: number | null;  // Backend returns this
  trust?: number | null;         // DUPLICATE - backend doesn't return this
}
```

**Risk**: Frontend code accessing `.trust` will get `undefined`, potential null reference errors.

**Solution**: Remove `trust` field, use only `trust_level` consistently.

---

## Medium Severity Issues

### 5. Relation Notes Type Flexibility 🟡 MEDIUM

**Impact**: Creation requests may fail validation

**Location**:
- Frontend: `frontend/src/types/relation.ts:19`
- Backend: `backend/app/schemas/relation.py:69`

**Problem**:
```typescript
// Frontend accepts
notes?: string | Record<string, string> | null;

// Backend only accepts
notes: Optional[dict[str, str]] = None  // i18n dict only
```

**Risk**: If frontend sends plain string for notes, backend validation fails.

**Solution**: Remove `string` from frontend type union, enforce i18n dict format.

---

### 6. Error Response Fallback Chain 🟡 MEDIUM

**Impact**: Inconsistent error parsing in edge cases

**Location**: `frontend/src/api/client.tsx:156,180,236,256`

**Problem**:
```typescript
// Frontend tries multiple error locations
const backendError = errorData.error || errorData.detail || errorData;
```

Backend standardizes on `{ error: ErrorDetail }` but frontend has fallback for legacy `detail` format.

**Risk**: If non-standard error is returned, parsing may fail silently.

**Solution**: Verify all backend endpoints use standardized ErrorResponse wrapper, remove fallback chain.

---

### 7. Search Result ID Type Documentation 🟡 MEDIUM

**Impact**: Potential confusion about UUID handling

**Location**:
- Frontend: `frontend/src/api/search.ts:20`
- Backend: `backend/app/schemas/search.py:96`

**Problem**: Frontend uses `id: string`, backend defines `id: UUID`. Works due to JSON serialization but types don't express this clearly.

**Solution**: Document that UUID fields are serialized as strings in TypeScript interfaces.

---

## Low Severity Issues

### 8. Extraction Preview Response Type Incompleteness 🟢 LOW

**Impact**: Frontend type doesn't reflect all backend fields

**Location**:
- Backend: `backend/app/schemas/source.py:133-136`
- Frontend: `frontend/src/types/extraction.ts:121`

**Problem**: Backend returns review metadata fields not in frontend type:
- `needs_review_count`
- `auto_verified_count`
- `avg_validation_score`

Frontend type includes `extracted_text` that backend doesn't always provide.

**Risk**: Extra properties ignored by TypeScript but increases payload size unnecessarily.

**Solution**: Align frontend type to match exact backend response schema.

---

### 9. Pagination Offset Optional vs Required 🟢 LOW

**Impact**: Minor type incompatibility

**Location**:
- Frontend: `frontend/src/api/sources.ts:34` (optional)
- Backend: `backend/app/schemas/pagination.py:38` (required)

**Problem**: Frontend marks `offset` optional but backend always returns it.

**Risk**: None currently (compatible), but could cause issues if backend changes.

**Solution**: Mark `offset` as required in frontend pagination types.

---

## Summary Statistics

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 2 | ⚠️ Requires immediate fix |
| High | 2 | 🔴 High priority |
| Medium | 3 | 🟡 Should fix soon |
| Low | 2 | 🟢 Minor improvements |
| **Total** | **9** | **Action items identified** |

---

## Recommended Action Plan

### Phase 1: Critical Fixes (This Sprint)

1. **Fix entity_links type** (Critical)
   - Update `backend/app/schemas/source.py` to accept `dict[str, str]`
   - Convert to UUID in service layer
   - Update frontend type documentation

2. **Fix extracted relation roles** (Critical)
   - Remove `Record<string, string>` from `frontend/src/types/extraction.ts`
   - Enforce array-only format

3. **Consolidate entity terms routes** (High)
   - Keep routes in `backend/app/api/entity_terms.py`
   - Remove duplicate routes from `backend/app/api/entities.py`
   - Update main.py router registration if needed

4. **Remove duplicate trust field** (High)
   - Delete `trust` field from `frontend/src/types/source.ts`
   - Grep codebase for `.trust` access and replace with `.trust_level`

### Phase 2: Medium Priority (Next Sprint)

5. **Standardize relation notes**
   - Remove `string` type from notes union in frontend
   - Update documentation

6. **Verify error response format**
   - Audit all endpoints return `{ error: ErrorDetail }`
   - Remove legacy `detail` fallback from client.tsx

7. **Document UUID serialization**
   - Add JSDoc comments explaining UUID→string serialization
   - Update API documentation

### Phase 3: Low Priority (Technical Debt)

8. **Align extraction preview types**
   - Add missing fields to frontend type
   - Remove unused fields

9. **Update pagination types**
   - Mark offset as required in frontend

---

## Testing Requirements

### Unit Tests
- [ ] Test entity_links with string IDs (post-fix)
- [ ] Test relation roles with array format only
- [ ] Test error response parsing with standardized format

### Integration Tests
- [ ] Full extraction save flow with entity linking
- [ ] Relation creation with i18n notes field
- [ ] Entity terms CRUD operations (post-consolidation)

### Contract Tests
- [ ] Pact tests for critical endpoints
- [ ] OpenAPI spec validation
- [ ] Type generation from backend schemas

---

## Prevention Strategies

### 1. Automated Type Generation
**Goal**: Generate TypeScript types from Pydantic schemas

**Tools**:
- `pydantic-to-typescript` package
- Custom script to sync types

**Benefit**: Single source of truth for API contracts

### 2. API Contract Testing
**Goal**: Validate frontend sends what backend expects

**Implementation**:
- Pact tests for consumer-driven contracts
- OpenAPI spec validation in CI/CD
- TypeScript compiler checks against generated types

### 3. Documentation
**Goal**: Keep API documentation in sync

**Strategy**:
- Auto-generate OpenAPI spec from FastAPI
- Use Swagger UI for interactive API docs
- Version API documentation

### 4. Code Review Checklist
- [ ] Frontend type matches backend schema
- [ ] Field names consistent (snake_case in API)
- [ ] Optional/required fields aligned
- [ ] Error responses standardized
- [ ] Query parameters documented

---

## Related Documentation

- `docs/architecture/ERROR_HANDLING_ARCHITECTURE.md` - Error response standards
- `docs/development/ERROR_HANDLING.md` - Error handling guide
- `docs/architecture/DATABASE_SCHEMA.md` - Data model reference
- `docs/development/API_GUIDE.md` - API conventions (TODO)

---

## Appendix A: File Checklist

### Files Requiring Updates

**Critical**:
- [ ] `frontend/src/types/extraction.ts` (lines 62, 137)
- [ ] `backend/app/schemas/source.py` (line 142)
- [ ] `backend/app/api/entities.py` (remove lines 128-225)
- [ ] `frontend/src/types/source.ts` (line 11)

**High Priority**:
- [ ] `frontend/src/types/relation.ts` (line 19)
- [ ] `backend/app/schemas/relation.py` (validate dict-only)

**Medium Priority**:
- [ ] `frontend/src/api/client.tsx` (error fallback chain)
- [ ] All backend endpoints (verify ErrorResponse wrapper)

**Low Priority**:
- [ ] `frontend/src/types/extraction.ts` (preview type)
- [ ] `frontend/src/api/sources.ts` (offset required)

---

## Appendix B: Communication Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    API REQUEST FLOW                          │
└─────────────────────────────────────────────────────────────┘

Frontend Component
       │
       │ Calls API function (e.g., saveExtraction)
       ▼
  frontend/src/api/extraction.ts
       │
       │ Calls apiFetch() with typed payload
       ▼
  frontend/src/api/client.tsx
       │
       │ HTTP POST/GET/PUT with JSON payload
       │ Headers: { Authorization, Content-Type }
       ▼
    NETWORK
       │
       ▼
  backend/app/main.py (FastAPI)
       │
       │ Route matching & CORS
       ▼
  backend/app/api/[endpoint].py
       │
       │ Pydantic validation (RequestSchema)
       ▼
  backend/app/services/[service].py
       │
       │ Business logic, DB operations
       │ Raises AppException on error
       ▼
  backend/app/middleware/error_handler.py
       │
       │ Catches exceptions → ErrorResponse
       ▼
    HTTP RESPONSE
       │
       │ Success: { ...data }
       │ Error: { error: { code, message, ... } }
       ▼
  frontend/src/api/client.tsx
       │
       │ parseError() → ParsedError
       │ console.error(formatted)
       ▼
  Frontend Component
       │
       │ catch block → showError(error)
       ▼
  NotificationContext
       │
       │ User sees toast, console has details
       ▼
    USER
```

---

**End of Report**

**Next Steps**:
1. Review findings with team
2. Prioritize fixes based on impact
3. Create GitHub issues for tracking
4. Implement Phase 1 critical fixes
5. Add contract tests to prevent regressions
