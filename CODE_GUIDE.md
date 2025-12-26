# Code Guide

This document provides coding guidelines and conventions for HyphaGraph development.

---

## 1. General principles

### 1.1 Explicit over clever
- Prefer readable, verbose code over clever abstractions
- Avoid magic methods and hidden behavior
- If logic cannot be understood at a glance, it needs refactoring

### 1.2 Boring over magical
- Use standard patterns and libraries
- Avoid framework-specific magic when plain Python will do
- Dependency injection should be explicit (FastAPI Depends is acceptable)

### 1.3 Auditable over convenient
- All business logic must be traceable
- Side effects must be explicit
- Security-critical code must be fully transparent

### 1.4 Long-term maintainability
- Write code that will be understandable in 5 years
- Document "why" not "what"
- Avoid dependencies on frameworks in maintenance mode

---

## 2. Authentication & Authorization

### 2.1 No "magic" authentication frameworks

**Rule**: Authentication logic MUST remain explicit.

We do NOT use:
- FastAPI Users (maintenance mode, too much abstraction)
- Auth0, Clerk, or similar SaaS providers (avoid vendor lock-in)
- Complex RBAC frameworks (premature abstraction)

**Why**:
- Authentication is security-critical and must be fully auditable
- Framework abstractions hide important security logic
- Maintenance mode libraries create long-term risk
- Explicit code is easier to reason about and test

### 2.2 Authentication implementation

**User model** (backend/app/models/user.py):
```python
class User(Base, UUIDMixin):
    """Minimal user model for authentication."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
```

**JWT utilities** (backend/app/utils/auth.py):
- Password hashing with passlib[bcrypt]
- Token creation/validation with python-jose
- No refresh tokens unless explicitly justified

**Auth endpoints** (backend/app/api/auth.py):
- POST /auth/register - create new user
- POST /auth/login - obtain JWT access token
- GET /auth/me - get current user info

**Dependencies** (backend/app/dependencies/auth.py):
```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate current user from JWT token."""
    # Explicit token validation
    # Explicit user lookup
    # Explicit exception handling
    ...
```

### 2.3 Authorization implementation

**Rule**: Authorization MUST be implemented as readable Python functions.

**Permission helpers** (backend/app/utils/permissions.py):
```python
def can_create_entity(user: User) -> bool:
    """Check if user can create entities."""
    return user.is_active

def can_edit_relation(user: User, relation: Relation) -> bool:
    """Check if user can edit a relation."""
    return user.is_active and (
        user.is_superuser or
        relation.created_by_user_id == user.id
    )

def can_publish_inference(user: User) -> bool:
    """Check if user can publish inference results."""
    return user.is_active and user.is_superuser

def require_permission(
    has_permission: bool,
    message: str = "Permission denied"
) -> None:
    """Raise HTTPException if permission check fails."""
    if not has_permission:
        raise HTTPException(status_code=403, detail=message)
```

**API integration**:
```python
@router.post("/entities", response_model=EntityRead)
async def create_entity(
    payload: EntityWrite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new entity (requires authentication)."""
    # Explicit permission check
    require_permission(
        can_create_entity(current_user),
        "You do not have permission to create entities"
    )

    # Pass user_id for provenance tracking
    service = EntityService(db)
    return await service.create(payload, user_id=current_user.id)
```

### 2.4 What NOT to do

**❌ Do NOT**:
- Use decorator-based permission systems (too magical)
- Implement complex role hierarchies (premature)
- Store permissions in database (overengineering)
- Use permission inheritance (hard to audit)
- Add OAuth providers without clear justification

**✅ Do INSTEAD**:
- Write explicit permission functions
- Keep authorization logic in one place
- Make permission checks visible in endpoints
- Test permission logic in isolation
- Document why each permission exists

---

## 3. Service layer patterns

### 3.1 Service responsibilities

Services implement domain logic and must be:
- Deterministic (same input = same output)
- Side-effect free (no hidden mutations)
- Recomputable (can be re-run safely)
- Testable in isolation

### 3.2 User provenance tracking

All create/update operations accept optional `user_id`:

```python
class EntityService:
    async def create(self, payload: EntityWrite, user_id: UUID | None = None) -> EntityRead:
        """Create entity with optional user provenance."""
        # ... entity creation logic

        if user_id:
            revision_data['created_by_user_id'] = user_id

        # ... continue
```

**Why user_id is optional**:
- Supports both authenticated and anonymous/system operations
- Migration data may not have user attribution
- Test fixtures don't require user setup
- LLM-generated data may not have user association

---

## 4. Database patterns

### 4.1 Revision architecture

All mutable entities use dual-table pattern:
- Base table: immutable (id, created_at)
- Revision table: versioned data (is_current flag)

### 4.2 User foreign keys

All revision tables reference users for provenance:

```python
created_by_user_id: Mapped[UUID | None] = mapped_column(
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
)
```

**Note**: SET NULL on delete preserves historical data even if user is deleted.

---

## 5. Testing guidelines

### 5.1 Authentication tests

Test authentication explicitly:

```python
def test_login_success(client, test_user):
    """Test successful login returns valid JWT."""
    response = client.post("/auth/login", data={
        "username": test_user.email,
        "password": "testpass123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_protected_endpoint_requires_auth(client):
    """Test protected endpoint rejects unauthenticated requests."""
    response = client.get("/auth/me")
    assert response.status_code == 401
```

### 5.2 Permission tests

Test permissions in isolation:

```python
def test_can_create_entity_active_user():
    """Active user can create entities."""
    user = User(is_active=True, is_superuser=False)
    assert can_create_entity(user) == True

def test_can_edit_relation_owner():
    """User can edit own relation."""
    user = User(id=uuid4(), is_active=True)
    relation = Relation(created_by_user_id=user.id)
    assert can_edit_relation(user, relation) == True

def test_can_edit_relation_non_owner():
    """Non-owner cannot edit relation."""
    user = User(id=uuid4(), is_active=True, is_superuser=False)
    relation = Relation(created_by_user_id=uuid4())
    assert can_edit_relation(user, relation) == False
```

---

## 6. Dependency management

### 6.1 Authentication dependencies

Required packages:
```
python-jose[cryptography]  # JWT handling
passlib[bcrypt]            # Password hashing
python-multipart           # OAuth2 form parsing
```

### 6.2 Avoiding deprecated packages

Before adding any dependency:
1. Check if actively maintained
2. Check GitHub stars and recent commits
3. Prefer libraries with explicit long-term support
4. Document rationale for any "risky" dependencies

---

## 7. Security checklist

Before deploying authentication:

- [ ] Passwords are hashed with bcrypt (never stored in plaintext)
- [ ] JWT secret is loaded from environment variable
- [ ] JWT tokens have reasonable expiration (e.g., 30 minutes)
- [ ] HTTPS is enforced in production
- [ ] CORS is properly configured
- [ ] SQL injection is prevented (use SQLAlchemy ORM)
- [ ] No secrets in version control
- [ ] Rate limiting on auth endpoints
- [ ] Failed login attempts are logged

---

## 8. Code style

- Follow PEP 8
- Use type hints everywhere
- Maximum line length: 100 characters
- Use async/await for all database operations
- Import order: stdlib, third-party, local
- Use f-strings for formatting
- Prefer explicit over implicit

---

## 9. When in doubt

Ask yourself:
1. Can I explain this code to someone in 5 years?
2. Is the security implication obvious?
3. Would I understand this without documentation?
4. Is this the simplest solution that works?

If the answer to any is "no", refactor.
