# AI Context — Backend (Layer 2)

Load this file when working on Python/FastAPI backend code.

---

## Folder Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Settings, env vars
│   ├── database.py          # Database session/engine
│   ├── startup.py           # Startup tasks (admin user, system source)
│   │
│   ├── api/                 # HTTP layer (NO domain logic)
│   │   ├── auth.py          # Auth endpoints (register, login, refresh, logout)
│   │   ├── users.py         # User management
│   │   ├── entities.py      # Entity CRUD + filter options
│   │   ├── sources.py       # Source CRUD + filter options
│   │   ├── relations.py     # Relation CRUD + roles
│   │   ├── inferences.py    # Read-only computed results
│   │   ├── explain.py       # Explainability endpoints
│   │   └── search.py        # Unified search
│   │
│   ├── schemas/             # Pydantic I/O models (single source of truth)
│   │   ├── entity.py, source.py, relation.py
│   │   ├── inference.py, explanation.py
│   │   ├── auth.py, search.py, filters.py
│   │   └── pagination.py    # PaginatedResponse[T]
│   │
│   ├── models/              # ORM models (no logic)
│   │   ├── base.py          # UUIDMixin, TimestampMixin
│   │   ├── user.py, refresh_token.py, audit_log.py
│   │   ├── entity.py, entity_revision.py, entity_term.py
│   │   ├── source.py, source_revision.py
│   │   ├── relation.py, relation_revision.py, relation_role_revision.py
│   │   ├── computed_relation.py
│   │   └── ui_category.py
│   │
│   ├── repositories/        # DB access only (queries, no business logic)
│   ├── services/            # Domain logic (deterministic, side-effect free)
│   ├── dependencies/        # FastAPI Depends (auth.py → get_current_user)
│   ├── mappers/             # ORM ↔ Pydantic conversion
│   └── utils/               # Pure helpers (auth, permissions, hashing, email)
│
├── tests/                   # pytest suite
├── alembic/                 # Database migrations
└── pyproject.toml           # Dependencies (uv)
```

---

## Layer Rules

| Layer | Can call | Cannot call |
|-------|----------|------------|
| API (controllers) | Services, Dependencies | Repositories, Models directly |
| Services | Repositories, Utils, other Services | API, Models directly for queries |
| Repositories | Models, Database session | Services, API |
| Mappers | Models, Schemas | Anything else |

---

## Critical Patterns

### Service Pattern

```python
class EntityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EntityRepo(db)

    async def create(self, payload: EntityWrite, user_id: UUID | None = None) -> EntityRead:
        # Validate → Create base → Create revision → Map to schema
```

- Services accept Pydantic schemas as input, return Pydantic schemas
- `user_id` is always optional (supports anonymous/system operations)
- Services never mutate base claims

### Repository Pattern

```python
class EntityRepo:
    async def get_by_id(self, entity_id: UUID) -> Entity | None:
        # Query with current revision join
```

- Repositories return ORM models
- All queries filter for `is_current = True` on revision tables
- Ordering by `created_at` (not name, not id)

### API Pattern

```python
@router.post("/entities", response_model=EntityRead)
async def create_entity(
    payload: EntityWrite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_permission(can_create_entity(current_user), "Permission denied")
    service = EntityService(db)
    return await service.create(payload, user_id=current_user.id)
```

- Explicit permission checks at API boundary
- No business logic in controllers
- Always pass `user_id` for provenance

### Pagination Pattern

Services return `(items, total)` tuples. API wraps in `PaginatedResponse[T]`.

---

## Auth Implementation

- `utils/auth.py` — JWT + bcrypt utilities (all async via ThreadPoolExecutor)
- `dependencies/auth.py` — `get_current_user`, `get_current_active_superuser`
- `utils/permissions.py` — Readable permission functions
- OAuth2 password flow → access token (30min) + refresh token

---

## Known Pitfalls

1. **Bcrypt is CPU-bound** — All hash operations use `loop.run_in_executor()` with thread pool
2. **Revision queries** — Always join with revision table and filter `is_current = True`
3. **Role snapshots** — When revising a relation, ALL roles must be duplicated for the new revision
4. **UUID conversion** — Role entity_ids may come as strings from frontend, convert with `UUID()`
5. **Source requirement** — Every relation MUST reference a source (NOT NULL FK)
6. **Database overrides in tests** — Use `app.dependency_overrides[get_db]` pattern

---

## Testing Patterns

```python
# Fixture
@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db

# Test
@pytest.mark.asyncio
async def test_create_entity(mock_db):
    service = EntityService(mock_db)
    result = await service.create(EntityWrite(slug="test"))
    assert result.slug == "test"
```

- Use `AsyncMock` for all DB operations
- Mark async tests with `@pytest.mark.asyncio`
- AAA pattern: Arrange / Act / Assert
- Test both success and error paths
