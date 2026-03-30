# Code Guide

Coding guidelines and conventions for HyphaGraph development.

---

## 1. General Principles

### Explicit over clever
- Prefer readable, verbose code over clever abstractions
- Avoid magic methods and hidden behavior

### Boring over magical
- Use standard patterns and libraries
- Avoid framework-specific magic when plain Python will do
- Dependency injection should be explicit (FastAPI `Depends` is acceptable)

### Auditable over convenient
- All business logic must be traceable
- Side effects must be explicit
- Security-critical code must be fully transparent

### Long-term maintainability
- Write code understandable in 5 years
- Document "why" not "what"
- Avoid dependencies on frameworks in maintenance mode

---

## 2. Authentication & Authorization

### No "magic" authentication frameworks

We do NOT use FastAPI Users, Auth0, Clerk, or complex RBAC frameworks.

**Why**: Authentication is security-critical and must be fully auditable. Framework abstractions hide important security logic. Maintenance mode libraries create long-term risk.

### Implementation summary

- **User model**: Minimal — id, email, hashed_password, is_active, is_superuser, created_at
- **JWT**: passlib[bcrypt] for hashing, python-jose for tokens
- **Endpoints**: POST `/auth/register`, POST `/auth/login`, GET `/auth/me`
- **Dependency**: `get_current_user` extracts and validates JWT
- **Permissions**: Explicit Python functions in `utils/permissions.py`

Use `docs/architecture/ARCHITECTURE.md` and the owning backend modules for concrete patterns.

### What NOT to do

- No decorator-based permission systems
- No complex role hierarchies
- No permissions stored in database
- No OAuth providers without clear justification

---

## 3. Service Layer Patterns

Services implement domain logic and must be:
- **Deterministic** (same input = same output)
- **Side-effect free** (no hidden mutations)
- **Recomputable** (can be re-run safely)
- **Testable in isolation**

### User provenance tracking

All create/update operations accept optional `user_id`:

```python
async def create(self, payload: EntityWrite, user_id: UUID | None = None) -> EntityRead:
```

Why optional: supports anonymous/system operations, migration data, test fixtures, LLM-generated data.

---

## 4. Database Patterns

### Revision architecture

All mutable entities use dual-table pattern:
- **Base table**: immutable (`id`, `created_at`)
- **Revision table**: versioned data (`is_current` flag)

### User foreign keys

All revision tables reference users for provenance:

```python
created_by_user_id: Mapped[UUID | None] = mapped_column(
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
)
```

SET NULL on delete preserves historical data even if user is deleted.

---

## 5. Dependency Management

Required auth packages:
```
python-jose[cryptography]  # JWT handling
passlib[bcrypt]            # Password hashing
python-multipart           # OAuth2 form parsing
```

Before adding any dependency:
1. Check if actively maintained
2. Check GitHub stars and recent commits
3. Prefer libraries with explicit long-term support

---

## 6. Security Checklist

- [ ] Passwords hashed with bcrypt (never plaintext)
- [ ] JWT secret from environment variable
- [ ] JWT tokens have reasonable expiration (30 min)
- [ ] HTTPS enforced in production
- [ ] CORS properly configured
- [ ] SQL injection prevented (use SQLAlchemy ORM)
- [ ] No secrets in version control
- [ ] Rate limiting on auth endpoints
- [ ] Failed login attempts logged

---

## 7. Code Style

- Follow PEP 8
- Use type hints everywhere
- Maximum line length: 100 characters
- Use async/await for all database operations
- Import order: stdlib, third-party, local
- Use f-strings for formatting

---

## 8. Naming Rules

Use names that are easy to search and review.

Prefer descriptive verb-noun names:
- `build_explanation_summary`
- `attach_document_revision`
- `load_relation_filters`

Avoid vague public names:
- `process`, `handle`, `run`, `data`, `tmp`, `res`

---

## 9. Quick Rules by Layer

### Backend
- Keep business logic in services; keep API routers thin (validate → authorize → call service → shape response).
- Use Pydantic schemas as the I/O contract.
- Pass `user_id` where provenance matters.
- Preserve revision history; never mutate history in place.
- Use `logging`, not `print()`.
- Keep auth and permission logic explicit and readable.

### Frontend
- Keep all network behavior inside `frontend/src/api/`.
- Keep React views thin; move reusable logic into hooks/components.
- Match frontend types to backend contracts.
- Route user-visible strings through i18n on primary UI flows.
- Do not present computed output as unquestionable truth.
- Keep contradiction, evidence, and traceability states visible.

---

## 10. Structured Data Preference

Prefer, in order:

1. Pydantic `BaseModel`
2. `TypedDict`
3. `dataclass`
4. raw `dict` only when unavoidable

Raw dictionaries are acceptable for very local transformations, direct library interop, or transient glue code that does not cross a public boundary.

---

## 11. Function Design

Functions should be focused, typed, and understandable in isolation.

Avoid:
- Long multi-purpose functions
- Behavior driven by many flags
- Orchestration mixed with low-level implementation details

---

## 12. Side Effects and State

- Prefer explicit state transitions.
- Avoid hidden mutation.
- Avoid global mutable state.
- Do not silently swallow errors in domain flows.
- If degraded behavior is intentional, make it visible in code and in UI.

---

## 13. Testing Expectations

- Add or update focused tests for behavior changes.
- Backend changes need pytest coverage for success and failure paths.
- Frontend changes need loading, error, empty, and contradiction-visible states covered when relevant.
- If you cannot run a needed test, say so clearly.

---

## 14. Temporary and Support Artifacts

- Put temporary reports and experiments in `.temp/`.
- Keep agent workflow files in `docs/` and `AGENTS.md`.
- Do not scatter scratch files into backend, frontend, or docs directories.

---

## 15. Frontend Error Handling

### Error display rule

| Situation | Pattern |
|-----------|---------|
| Async API call triggered by a user action (submit, delete, save) | `useAsyncAction` **without** `setError` → toast via `NotificationContext` |
| Same, but error must appear next to a form field | `useAsyncAction(setError)` → inline display; **no toast** |
| Data-fetch lifecycle (loading + data + error state in a view) | `useAsyncResource` |
| One-off error outside of the above (e.g. manual `useEffect`) | `usePageErrorHandler` → toast |

**Never** mix both patterns for the same error: `useAsyncAction(setError)` suppresses the toast automatically. If you also call `showError` manually, you will show two notifications for the same failure.

### Error response contract

All API errors return `{ "error": { "code", "message", "details", "field", "context" } }`.

The frontend parses this into `ParsedAppError` with:
- `userMessage` — shown in the Snackbar or inline alert
- `developerMessage` — logged to `console.error` via `formatErrorForLogging()`; shown in the expandable "Dev details" section in the Snackbar (development builds only)
- `code` — `ErrorCode` enum value (keep frontend and backend enums in sync; see `test_error_handlers.py::test_error_code_enum_matches_known_set`)
- `field` — optional field name for form validation errors
- `context` — optional structured context for debugging

### What NOT to do

- Do not use `useState<string>` for API error state. Use `useAsyncAction(setError)` where `setError` receives the parsed `userMessage` string.
- Do not call both `showError(e)` and `setError(...)` for the same error.
- Do not add a new `ErrorCode` value in backend without also adding it to the frontend enum and the `EXPECTED_BACKEND_ERROR_CODES` snapshot in `test_error_handlers.py`.
