# Code Maintainability Review & Action Plan

**Date**: 2026-03-08
**Scope**: Single Responsibility Principle (SRP) Violations
**Status**: Issues Identified - Refactoring Plan Defined

---

## Executive Summary

A comprehensive review identified **24 SRP violations** and maintainability issues across the codebase. The most critical issues include a 594-line god-component in the frontend, a 216-line god-method in backend services, and duplicated confidence filtering logic across 4+ locations.

**Key Metrics**:
- **God Components**: 2 (>500 lines)
- **God Methods**: 1 (>200 lines)
- **Code Duplication**: 4+ instances of same filtering logic
- **Mixed Concerns**: 15 services/components doing too much

---

## Priority Matrix

| Priority | Count | Impact |
|----------|-------|--------|
| **HIGH** | 5 | Architectural/performance issues |
| **MEDIUM** | 4 | Code organization issues |
| **LOW** | 3 | Quality improvements |

---

## HIGH PRIORITY ISSUES

### 1. EntityDetailView God-Component ⚠️ CRITICAL

**File**: `frontend/src/views/EntityDetailView.tsx`
**Size**: 594 lines
**Severity**: HIGH

**Issues**:
- Multiple data fetching responsibilities (entity, inference, sources)
- Complex state management (10+ useState hooks)
- Mixed presentation and business logic
- Nested conditional rendering
- Hard to test and maintain

**Current Structure**:
```typescript
// Lines 55-68: Too many state variables
const [entity, setEntity] = useState<EntityRead | null>(null);
const [inference, setInference] = useState<...>(null);
const [sources, setSources] = useState<SourceRead[]>([]);
const [isLoading, setIsLoading] = useState(true);
const [scopeFilter, setScopeFilter] = useState<ScopeFilter>({});
// ... 6 more state variables
```

**Recommendation**:
```typescript
// Extract custom hooks
const { entity, isLoading } = useEntityData(entityId);
const { inference } = useEntityInference(entityId, scopeFilter);
const { sources } = useEntitySources(inference);

// Extract sub-components
<EntityDetailHeader entity={entity} />
<EntityInferencePanel inference={inference} onFilterChange={...} />
<EntitySourceList sources={sources} />
```

**Benefits**:
- Reduce component from 594 → ~150 lines
- Improve testability (test hooks independently)
- Better code reusability
- Clearer separation of concerns

**Effort**: 4-6 hours
**Files to Create**:
- `hooks/useEntityData.ts`
- `hooks/useEntityInference.ts`
- `hooks/useEntitySources.ts`
- `components/EntityDetailHeader.tsx`
- `components/EntityInferencePanel.tsx`

---

### 2. EntityService.list_all() God-Method ⚠️ CRITICAL

**File**: `backend/app/services/entity_service.py`
**Lines**: 102-318 (216 lines!)
**Severity**: HIGH

**Issues**:
- Builds 6+ subqueries in one method
- Computes consensus, evidence quality, and recency
- Applies multiple filter types
- Handles pagination and result mapping
- Performance impact (complex query construction)

**Current Structure**:
```python
async def list_all(self, filters: EntityFilters) -> PaginatedEntityList:
    # Lines 119-137: Basic filter application
    # Lines 142-154: Clinical effects subquery
    # Lines 156-186: Evidence quality computation
    # Lines 188-241: Recency computation (54 lines!)
    # Lines 243-297: Consensus level computation (55 lines!)
    # Lines 299-318: Pagination + result conversion
```

**Recommendation**:
```python
# Extract query builder pattern
class EntityQueryBuilder:
    def apply_basic_filters(self, filters) -> Select: ...
    def add_clinical_effects_filter(self, filters) -> Select: ...
    def add_evidence_quality_filter(self, filters) -> Select: ...
    def add_recency_filter(self, filters) -> Select: ...
    def add_consensus_filter(self, filters) -> Select: ...

# Simplified service method
async def list_all(self, filters: EntityFilters):
    query = self.query_builder.build_query(filters)
    results = await self.db.execute(query)
    return self.paginate(results, filters.limit, filters.offset)
```

**Benefits**:
- Each filter type independently testable
- Better query performance (can optimize individual filters)
- Easier to add new filter types
- Reduce method from 216 → ~30 lines

**Effort**: 6-8 hours
**Files to Create**:
- `backend/app/services/entity_query_builder.py`
- Unit tests for each filter method

---

### 3. Duplicate Confidence Filtering Logic ⚠️ HIGH

**Locations** (ExtractionService):
- Lines 160-168 (extract_entities)
- Lines 225-234 (extract_relations)
- Lines 369-376, 379-385 (extract_batch - twice!)

**Issue**: Same filtering code copied 4+ times:
```python
# Repeated in 4 places!
confidence_order = {"high": 3, "medium": 2, "low": 1}
min_level = confidence_order.get(min_confidence, 1)
entities = [e for e in entities
            if confidence_order.get(e.confidence, 0) >= min_level]
```

**Recommendation**:
```python
# backend/app/utils/confidence_filter.py
from typing import TypeVar, Protocol

class HasConfidence(Protocol):
    confidence: Literal["high", "medium", "low"]

T = TypeVar("T", bound=HasConfidence)

def filter_by_confidence(
    items: list[T],
    min_confidence: Literal["high", "medium", "low"] | None
) -> list[T]:
    """Filter items by minimum confidence level."""
    if not min_confidence:
        return items

    confidence_order = {"high": 3, "medium": 2, "low": 1}
    min_level = confidence_order[min_confidence]

    return [
        item for item in items
        if confidence_order.get(item.confidence, 0) >= min_level
    ]

# Usage
entities = filter_by_confidence(entities, min_confidence)
relations = filter_by_confidence(relations, min_confidence)
```

**Benefits**:
- DRY principle enforced
- Single source of truth for filtering logic
- Type-safe with Protocol
- Easy to modify filtering logic in future

**Effort**: 1-2 hours

---

### 4. Auth Utilities Mixed Concerns ⚠️ HIGH

**File**: `backend/app/utils/auth.py`
**Lines**: 26-222 (8 different concerns!)
**Severity**: HIGH

**Issues**:
- Password hashing functions (lines 26-83)
- Access token functions (lines 86-136)
- Refresh token functions (lines 139-222)
- Hard to test individual concerns
- No clear separation

**Current Structure**: Flat module with 8 functions

**Recommendation**:
```python
# backend/app/utils/password_hasher.py
class PasswordHasher:
    async def hash_password(self, password: str) -> str: ...
    async def verify_password(self, password: str, hash: str) -> bool: ...

# backend/app/utils/access_token_manager.py
class AccessTokenManager:
    def create_access_token(self, user_id: UUID) -> str: ...
    def decode_access_token(self, token: str) -> dict: ...

# backend/app/utils/refresh_token_manager.py
class RefreshTokenManager:
    def generate_refresh_token(self) -> str: ...
    async def hash_refresh_token(self, token: str) -> str: ...
    async def verify_refresh_token(self, token: str, hash: str) -> bool: ...

# backend/app/utils/auth.py (factory/facade)
def get_password_hasher() -> PasswordHasher: ...
def get_access_token_manager() -> AccessTokenManager: ...
def get_refresh_token_manager() -> RefreshTokenManager: ...
```

**Benefits**:
- Clear separation of password vs token concerns
- Easier to mock in tests
- Can swap implementations (e.g., use Argon2 instead of bcrypt)
- Better encapsulation

**Effort**: 3-4 hours

---

### 5. ExtractionService Batch Methods ⚠️ HIGH

**File**: `backend/app/services/extraction_service.py`
**Methods**:
- `extract_batch` (lines 295-405, 110 lines)
- `extract_batch_with_validation_results` (lines 407-571, 165 lines)

**Issues**:
- Both methods mix extraction + validation + filtering + logging
- Very similar logic duplicated
- Hard to test individual steps
- Complex control flow

**Recommendation**:
```python
# Extract orchestration pattern
class BatchExtractionOrchestrator:
    def __init__(
        self,
        extraction_service: ExtractionService,
        validation_service: ValidationService,
        filter_service: ConfidenceFilterService
    ):
        self.extraction = extraction_service
        self.validation = validation_service
        self.filter = filter_service

    async def extract_batch(self, text: str, options: dict):
        # 1. Extract raw data
        raw_data = await self.extraction.extract_all(text)

        # 2. Filter by confidence
        filtered_data = self.filter.apply(raw_data, options.min_confidence)

        # 3. Validate if needed
        if options.validate:
            validated = await self.validation.validate(filtered_data)
            return validated

        return filtered_data
```

**Benefits**:
- Each step testable independently
- Clear pipeline: extract → filter → validate
- Easier to add new steps (e.g., deduplication)

**Effort**: 5-6 hours

---

## MEDIUM PRIORITY ISSUES

### 6. ReviewQueueView State Management 🟡 MEDIUM

**File**: `frontend/src/views/ReviewQueueView.tsx`
**Lines**: 52-64 (11 state variables)
**Severity**: MEDIUM

**Issue**:
```typescript
// Too many related state variables
const [extractions, setExtractions] = useState([]);
const [stats, setStats] = useState(null);
const [isLoading, setIsLoading] = useState(false);
const [page, setPage] = useState(1);
const [hasMore, setHasMore] = useState(true);
const [selectedIds, setSelectedIds] = useState<Set<string>>();
const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
const [reviewNotes, setReviewNotes] = useState("");
const [reviewDecision, setReviewDecision] = useState<...>();
const [minScore, setMinScore] = useState<number | undefined>();
const [onlyFlagged, setOnlyFlagged] = useState(false);
```

**Recommendation**:
```typescript
// Extract hooks
const { extractions, stats, isLoading, loadMore, hasMore } = useReviewQueue({
    page, minScore, onlyFlagged
});

const { selectedIds, toggleSelection, clearSelection } = useSelection();

const {
    isOpen,
    notes,
    decision,
    openDialog,
    closeDialog,
    submitReview
} = useReviewDialog();
```

**Benefits**:
- Reduce component from ~400 → ~150 lines
- Hooks reusable in other review views
- Easier to test

**Effort**: 2-3 hours

---

### 7. Layout Component Multiple Concerns 🟡 MEDIUM

**File**: `frontend/src/components/Layout.tsx`
**Severity**: MEDIUM

**Responsibilities**:
1. Navigation menu management
2. Authentication state checks
3. Mobile vs desktop responsive logic
4. Language switching
5. Entity category dropdown
6. Global search dialog
7. Profile menu

**Recommendation**:
```typescript
// Extract components
<AppBar>
    <MobileNavigation categories={categories} onCategorySelect={...} />
    <DesktopNavigation categories={categories} />
    <LanguageSwitcher currentLanguage={i18n.language} />
    <GlobalSearchButton onClick={openSearch} />
    <ProfileMenu user={user} onLogout={logout} />
</AppBar>

<GlobalSearchDialog open={searchOpen} onClose={closeSearch} />
```

**Effort**: 2-3 hours

---

### 8. Sources API Metadata Extraction 🟡 MEDIUM

**File**: `backend/app/api/sources.py`
**Lines**: 38-138 (extract_metadata_from_url)
**Severity**: MEDIUM

**Issue**: Mixes URL type detection + provider-specific logic

**Recommendation**:
```python
# backend/app/services/metadata_extractors/base.py
class MetadataExtractor(ABC):
    @abstractmethod
    async def can_handle(self, url: str) -> bool: ...

    @abstractmethod
    async def extract_metadata(self, url: str) -> SourceMetadata: ...

# backend/app/services/metadata_extractors/pubmed.py
class PubMedMetadataExtractor(MetadataExtractor):
    async def can_handle(self, url: str) -> bool:
        return "pubmed.ncbi.nlm.nih.gov" in url

    async def extract_metadata(self, url: str) -> SourceMetadata:
        pmid = self._extract_pmid(url)
        return await self.pubmed_fetcher.fetch_metadata(pmid)

# backend/app/services/metadata_extractors/generic.py
class GenericUrlMetadataExtractor(MetadataExtractor):
    async def can_handle(self, url: str) -> bool:
        return True  # Fallback

    async def extract_metadata(self, url: str) -> SourceMetadata:
        return await self.url_fetcher.fetch_url_metadata(url)

# API endpoint becomes:
@router.post("/metadata-from-url")
async def extract_metadata_from_url(request: MetadataRequest):
    extractor = metadata_extractor_factory.get_extractor(request.url)
    return await extractor.extract_metadata(request.url)
```

**Benefits**:
- Strategy pattern - easy to add new providers
- Each extractor testable independently
- Clear separation of URL type detection logic

**Effort**: 3-4 hours

---

### 9. API Endpoint Error Handling Duplication 🟡 MEDIUM

**Files**: `backend/app/api/extraction.py`
**Lines**: 169-200, 233-265, 299-330, 355-391

**Issue**: Same try-catch pattern repeated 4 times

**Recommendation**:
```python
# backend/app/api/error_handlers.py
def handle_extraction_errors(func):
    """Decorator to handle extraction errors consistently."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except AppException:
            raise  # Re-raise AppExceptions
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            raise AppException(
                status_code=500,
                error_code=ErrorCode.EXTRACTION_FAILED,
                message=f"{func.__name__} failed",
                details=str(e)
            )
    return wrapper

# Usage
@handle_extraction_errors
async def extract_entities(...):
    return await extraction_service.extract_entities(...)
```

**Effort**: 1-2 hours

---

## LOW PRIORITY ISSUES

### 10. SearchView Multiple State Updates 🟢 LOW

**File**: `frontend/src/views/SearchView.tsx`
**Lines**: 66-70

**Issue**:
```typescript
// Updating 5 state variables manually
setResults(searchResults.results);
setTotal(searchResults.total);
setStats(searchResults.stats);
setTotalResults(searchResults.total);
setLoading(false);
```

**Recommendation**:
```typescript
// Use single state object or custom hook
const { results, total, stats, isLoading, search } = useSearch();

// Or useReducer
const [state, dispatch] = useReducer(searchReducer, initialState);
dispatch({ type: 'SEARCH_SUCCESS', payload: searchResults });
```

**Effort**: 1 hour

---

### 11. ValidationService Separation 🟢 LOW

**File**: `backend/app/services/validation_service.py`

**Recommendation**: Separate relation schema validation from role schema validation

**Effort**: 1-2 hours

---

### 12. EntityMergeService Duplicate Detection 🟢 LOW

**File**: `backend/app/services/entity_merge_service.py`
**Lines**: 30-86

**Recommendation**: Extract similarity checking and term matching into separate utilities

**Effort**: 2 hours

---

## Implementation Roadmap

### Phase 1: Quick Wins (1-2 days)
1. ✅ Extract confidence filtering utility (HIGH - #3)
2. ✅ Add API error handling decorator (MEDIUM - #9)
3. ✅ Consolidate search state management (LOW - #10)

### Phase 2: Core Refactoring (1 week)
4. ⏳ Refactor EntityService.list_all() with query builder (HIGH - #2)
5. ⏳ Split auth utilities into focused classes (HIGH - #4)
6. ⏳ Extract EntityDetailView hooks and components (HIGH - #1)

### Phase 3: Architectural Improvements (1-2 weeks)
7. ⏳ Implement BatchExtractionOrchestrator (HIGH - #5)
8. ⏳ Extract metadata extractors with strategy pattern (MEDIUM - #8)
9. ⏳ Refactor ReviewQueueView hooks (MEDIUM - #6)
10. ⏳ Split Layout into sub-components (MEDIUM - #7)

### Phase 4: Quality Improvements (ongoing)
11. ⏳ Remaining LOW priority items

---

## Metrics & Goals

### Current State
- **Longest component**: 594 lines
- **Longest method**: 216 lines
- **Code duplication**: 4+ instances
- **Average component size**: ~250 lines
- **Average method size**: ~35 lines

### Target State (Post-Refactoring)
- **Longest component**: <300 lines
- **Longest method**: <100 lines
- **Code duplication**: 0 critical duplications
- **Average component size**: ~150 lines
- **Average method size**: ~25 lines

---

## Testing Strategy

### Unit Tests Required
- [ ] ConfidenceFilterService tests
- [ ] EntityQueryBuilder tests (each filter method)
- [ ] PasswordHasher tests
- [ ] AccessTokenManager tests
- [ ] RefreshTokenManager tests
- [ ] MetadataExtractor tests (each provider)

### Integration Tests Required
- [ ] EntityService.list_all() with various filters
- [ ] Batch extraction orchestration flow
- [ ] Review queue with pagination

---

## Prevention Strategies

### Code Review Checklist
- [ ] Component <300 lines?
- [ ] Method <50 lines?
- [ ] Single responsibility clear?
- [ ] No duplicated logic?
- [ ] Proper abstraction level?

### Automated Checks
- **ESLint**: max-lines rule (300 for components)
- **Pylint**: max-lines-per-method (50)
- **SonarQube**: Cognitive complexity threshold
- **CodeClimate**: Duplication detection

---

## Appendix: File-by-File Action Items

### Backend
- [ ] `entity_service.py` - Extract EntityQueryBuilder
- [ ] `extraction_service.py` - Extract ConfidenceFilter + orchestrator
- [ ] `auth.py` - Split into 3 classes
- [ ] `sources.py` - Extract MetadataExtractor pattern
- [ ] `extraction.py` - Add error handling decorator

### Frontend
- [ ] `EntityDetailView.tsx` - Extract 3 hooks + 2 components
- [ ] `ReviewQueueView.tsx` - Extract 2 hooks
- [ ] `Layout.tsx` - Extract 4 sub-components
- [ ] `SearchView.tsx` - Use useSearch hook

---

**End of Report**
