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

See `docs/ai/AI_CONTEXT_BACKEND.md` for code patterns.

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
