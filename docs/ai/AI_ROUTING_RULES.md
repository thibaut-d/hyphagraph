# AI Routing Rules (Layer 3)

This file defines which context files an AI agent should load for specific tasks. The goal is to stay under 200k tokens by loading only what is needed.

---

## Always Load (Layer 1)

For **every task**, load:
- `docs/ai/AI_CONTEXT_CORE.md`

This provides project purpose, invariants, tech stack, naming conventions, and non-negotiables.

---

## Task-Specific Loading

### Database Schema Changes

```
Load:
- docs/architecture/DATABASE_SCHEMA.md
- docs/ai/AI_CONTEXT_BACKEND.md
- backend/app/models/*
- backend/alembic/versions/ (latest migration)
```

Constraints:
- Revision architecture must be preserved (dual-table pattern)
- Add `created_by_user_id` to new revision tables
- Foreign keys: SET NULL on user delete
- Create Alembic migration for all schema changes

---

### Computed Relations / Inference

```
Load:
- docs/architecture/COMPUTED_RELATIONS.md
- docs/ai/AI_CONTEXT_ARCHITECTURE.md
- backend/app/services/inference_service.py
- backend/app/services/explanation_service.py
- backend/app/schemas/inference.py
- backend/app/schemas/explanation.py
```

Constraints:
- Mathematical model must match COMPUTED_RELATIONS.md exactly
- All inference must be deterministic and recomputable
- Scope filtering uses SHA256 hash for cache keys

---

### Backend API Endpoints

```
Load:
- docs/ai/AI_CONTEXT_BACKEND.md
- backend/app/api/ (relevant router file)
- backend/app/schemas/ (relevant schema)
- backend/app/services/ (relevant service)
- backend/app/dependencies/auth.py
```

Constraints:
- No business logic in API controllers
- Explicit permission checks at boundary
- Always pass user_id for provenance
- Return Pydantic schemas, not ORM models

---

### Backend Services

```
Load:
- docs/ai/AI_CONTEXT_BACKEND.md
- backend/app/services/ (relevant service)
- backend/app/repositories/ (relevant repo)
- backend/app/schemas/ (relevant schemas)
- backend/tests/ (existing tests for the service)
```

Constraints:
- Services must be deterministic and side-effect free
- Write tests FIRST (TDD)
- Services accept/return Pydantic schemas
- User_id is always optional parameter

---

### Frontend Views

```
Load:
- docs/ai/AI_CONTEXT_FRONTEND.md
- docs/product/UX.md (relevant section)
- frontend/src/views/ (relevant view)
- frontend/src/api/ (relevant API client)
- frontend/src/types/ (relevant types)
- frontend/src/i18n/en.json (for translation keys)
```

Constraints:
- No business logic duplication from backend
- Types must match backend schemas
- Never hide uncertainty or contradictions
- Responsive design (MUI breakpoints)
- Add i18n keys for all user-visible text

---

### Frontend Components

```
Load:
- docs/ai/AI_CONTEXT_FRONTEND.md
- frontend/src/components/ (relevant component)
- frontend/src/components/__tests__/ (existing tests)
- frontend/src/hooks/ (if component uses custom hooks)
```

Constraints:
- Components should be reusable and pure
- Test with Vitest + Testing Library
- Mock API calls, don't make real requests

---

### Authentication Changes

```
Load:
- docs/ai/AI_CONTEXT_BACKEND.md
- docs/architecture/ARCHITECTURE.md (Section 6)
- backend/app/utils/auth.py
- backend/app/dependencies/auth.py
- backend/app/utils/permissions.py
- backend/app/services/user_service.py
- backend/app/models/user.py
- backend/tests/test_auth_*.py
```

Constraints:
- Custom JWT only — NO FastAPI Users, NO auth frameworks
- All bcrypt operations must be async (ThreadPoolExecutor)
- Permission functions must be explicit, readable, testable
- No decorator-based permissions, no RBAC frameworks

---

### Filter / Search Features

```
Load:
- docs/ai/AI_CONTEXT_FRONTEND.md
- docs/product/UX.md (Sections 5.2-5.4)
- frontend/src/components/filters/
- frontend/src/hooks/useFilterDrawer.ts
- frontend/src/hooks/usePersistedFilters.ts
- backend/app/api/ (filter-options endpoints)
```

Constraints:
- Drawer is STRICTLY for filters, never navigation
- Filters affect display, NOT underlying calculations
- Clear indication when evidence is hidden
- Use domain language, not technical jargon
- Persist filter state in localStorage

---

### UX / Design Changes

```
Load:
- docs/product/UX.md
- docs/ai/AI_CONTEXT_FRONTEND.md
- frontend/src/components/Layout.tsx
- frontend/src/views/ (affected views)
```

Constraints:
- Contradictions never hidden
- Syntheses never appear as absolute truth
- Every conclusion traceable to sources (2 clicks)
- Responsive: mobile/tablet/desktop

---

### E2E Tests

```
Load:
- docs/development/E2E_TESTING_GUIDE.md
- e2e/fixtures/ (helpers and test data)
- e2e/tests/ (relevant test files)
- e2e/playwright.config.ts
```

Constraints:
- Role-based selectors preferred over text locators
- Sequential execution (workers: 1) for test isolation
- Each test must clean up after itself
- Use auth helpers for login flows

---

### Documentation Changes

```
Load:
- docs/ai/AI_CONTEXT_CORE.md
- The specific document being modified
- Related documents that may need cross-reference updates
```

Constraints:
- Keep files focused and non-redundant
- Update cross-references when moving content
- AI context files must stay synchronized with actual codebase

---

## Token Budget Guidelines

| Task Complexity | Estimated Context | Strategy |
|----------------|-------------------|----------|
| Simple bug fix | ~20k tokens | Core + relevant file |
| Feature addition | ~50k tokens | Core + domain context + relevant files |
| Architecture change | ~80k tokens | Core + Architecture + multiple domain files |
| Cross-cutting refactor | ~120k tokens | Core + all domain contexts + affected files |

Goal: Stay under 200k tokens total (context + conversation) for efficient operation.
