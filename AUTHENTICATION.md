# Authentication System Documentation

This document describes the HyphaGraph authentication system implementation.

---

## Overview

HyphaGraph uses a **custom JWT-based authentication system** built with FastAPI, SQLAlchemy, and standard Python libraries.

**Important**: We do NOT use FastAPI Users or any third-party authentication framework.

**Rationale**:
- FastAPI Users is in maintenance mode (no active development)
- Security-critical code must be fully transparent and auditable
- Framework abstractions introduce hidden complexity and coupling
- We prefer explicit, boring code over magical patterns

---

## Architecture

### User Model

Minimal user model with only essential fields:

```python
class User(Base, UUIDMixin):
    id: UUID               # Primary key
    email: str             # Unique, indexed
    hashed_password: str   # Bcrypt hashed
    is_active: bool        # Can user log in?
    is_superuser: bool     # Has admin privileges?
    created_at: datetime   # Registration timestamp
```

Location: `backend/app/models/user.py`

### JWT Token Flow

1. **Registration** (`POST /auth/register`):
   - User provides email + password
   - Password is hashed with bcrypt
   - User record created in database
   - Returns user info (no password)

2. **Login** (`POST /auth/login`):
   - User provides email + password via OAuth2 password flow
   - Credentials verified against database
   - JWT access token generated (30 minute expiration)
   - Token returned to client

3. **Protected Endpoints**:
   - Client includes token in `Authorization: Bearer <token>` header
   - `get_current_user` dependency validates token
   - User object injected into endpoint
   - Permission checks performed explicitly

4. **User Info** (`GET /auth/me`):
   - Requires valid JWT token
   - Returns current user information

### Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_users_email ON users(email);
```

Migration: `backend/alembic/versions/20241227_add_users_table.py`

---

## Implementation Files

### Core Authentication

| File | Purpose |
|------|---------|
| `app/models/user.py` | User ORM model |
| `app/schemas/auth.py` | Request/response schemas |
| `app/utils/auth.py` | JWT & password utilities |
| `app/dependencies/auth.py` | FastAPI dependencies |
| `app/api/auth.py` | Authentication endpoints |
| `app/utils/permissions.py` | Authorization helpers |

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SECRET_KEY` | "change-me" | JWT signing key (MUST set in production) |
| `ALGORITHM` | "HS256" | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Token expiration time |

Location: `backend/app/config.py`

**⚠️ Security Warning**: `SECRET_KEY` MUST be set via environment variable in production.

### Dependencies

```toml
# Required for authentication
"python-jose[cryptography]>=3.3"  # JWT handling
"passlib[bcrypt]>=1.7.4"          # Password hashing
"python-multipart>=0.0.6"         # OAuth2 form parsing
```

Location: `backend/pyproject.toml`

---

## API Endpoints

### POST /auth/register

Register a new user account.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-12-27T10:00:00Z"
}
```

**Errors**:
- `400 Bad Request`: Email already registered
- `422 Unprocessable Entity`: Validation error (password < 8 chars)

### POST /auth/login

Login and obtain JWT access token.

**Request** (OAuth2 form data):
```
username=user@example.com&password=securepassword123
```

Note: Despite the field name "username", we use email addresses.

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: Inactive user account

### GET /auth/me

Get current authenticated user information.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-12-27T10:00:00Z"
}
```

**Errors**:
- `401 Unauthorized`: Invalid or missing token
- `403 Forbidden`: User is inactive

### POST /auth/refresh

Refresh access token using refresh token.

**Request Body**:
```json
{
  "refresh_token": "..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "new_access_token...",
  "token_type": "bearer"
}
```

**Errors**:
- `401 Unauthorized`: Invalid or expired refresh token
- `403 Forbidden`: Revoked refresh token

### POST /auth/logout

Revoke refresh token (logout).

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "refresh_token": "..."
}
```

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

### POST /auth/change-password

Change user password (requires current password).

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "current_password": "oldpassword123",
  "new_password": "newpassword456"
}
```

**Response** (200 OK):
```json
{
  "message": "Password changed successfully"
}
```

**Errors**:
- `400 Bad Request`: Current password incorrect
- `422 Unprocessable Entity`: New password validation failed

### PUT /auth/me

Update user profile.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "email": "newemail@example.com"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "email": "newemail@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-12-27T10:00:00Z"
}
```

### POST /auth/deactivate

Deactivate user account (soft delete).

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "message": "Account deactivated successfully"
}
```

### DELETE /auth/me

Permanently delete user account.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "message": "Account deleted successfully"
}
```

### POST /auth/verify-email

Verify email address with token.

**Request Body**:
```json
{
  "token": "verification_token_from_email"
}
```

**Response** (200 OK):
```json
{
  "message": "Email verified successfully"
}
```

**Errors**:
- `400 Bad Request`: Invalid or expired token

### POST /auth/resend-verification

Resend email verification.

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response** (200 OK):
```json
{
  "message": "Verification email sent"
}
```

### POST /auth/request-password-reset

Request password reset email.

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response** (200 OK):
```json
{
  "message": "Password reset email sent if account exists"
}
```

Note: Always returns success to prevent user enumeration.

### POST /auth/reset-password

Reset password with token from email.

**Request Body**:
```json
{
  "token": "reset_token_from_email",
  "new_password": "newsecurepassword"
}
```

**Response** (200 OK):
```json
{
  "message": "Password reset successfully"
}
```

**Errors**:
- `400 Bad Request`: Invalid or expired token
- `422 Unprocessable Entity`: Password validation failed

---

## Usage Examples

### Protecting an Endpoint

```python
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_user)
):
    """This endpoint requires authentication."""
    return {"message": f"Hello, {current_user.email}!"}
```

### Adding Permission Checks

```python
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.utils.permissions import can_create_entity, require_permission
from app.schemas.entity import EntityWrite, EntityRead
from app.services.entity_service import EntityService

router = APIRouter()

@router.post("/entities", response_model=EntityRead)
async def create_entity(
    payload: EntityWrite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create entity with permission check."""
    # Explicit permission check
    require_permission(
        can_create_entity(current_user),
        "You do not have permission to create entities"
    )

    # Pass user_id for provenance tracking
    service = EntityService(db)
    return await service.create(payload, user_id=current_user.id)
```

### Requiring Superuser

```python
from app.dependencies.auth import get_current_active_superuser

@router.delete("/admin/purge")
async def admin_purge(
    current_user: User = Depends(get_current_active_superuser)
):
    """Only superusers can call this endpoint."""
    # ... dangerous operation
```

---

## Authorization System

### Permission Functions

All permission checks are implemented as explicit Python functions in `app/utils/permissions.py`.

**Entity Permissions**:
- `can_create_entity(user)` - Any active user
- `can_edit_entity(user, created_by)` - Owner or superuser

**Source Permissions**:
- `can_create_source(user)` - Any active user
- `can_edit_source(user, created_by)` - Owner or superuser

**Relation Permissions**:
- `can_create_relation(user)` - Any active user
- `can_edit_relation(user, created_by)` - Owner or superuser

**Inference Permissions**:
- `can_publish_inference(user)` - Superuser only
- `can_view_inference(user)` - Any active user

**User Management**:
- `can_manage_users(user)` - Superuser only
- `can_view_user(user, target_id)` - Self or superuser

### Permission Helper

```python
def require_permission(has_permission: bool, message: str = "Permission denied") -> None:
    """Raise HTTPException if permission check fails."""
    if not has_permission:
        raise HTTPException(status_code=403, detail=message)
```

### Permission Rules

Current authorization follows these principles:

1. **Active users** can create content (entities, sources, relations)
2. **Owners** can edit their own content
3. **Superusers** can edit any content
4. **Superusers** are required for privileged operations (publishing inferences, user management)
5. **Legacy data** (without attribution) is editable by any active user

These rules are intentionally simple and explicit. More complex authorization can be added by:
- Modifying permission functions (readable, auditable)
- NOT by adding framework magic or RBAC systems

---

## Provenance Integration

All services accept optional `user_id` parameter for audit trails:

```python
class EntityService:
    async def create(self, payload: EntityWrite, user_id: UUID | None = None):
        # ...
        if user_id:
            revision_data['created_by_user_id'] = user_id
```

This enables:
- **Audit trails**: Who created/modified what and when
- **Permission checks**: Ownership-based authorization
- **Attribution**: Credit for contributions
- **Optional auth**: System operations and migrations don't require users

---

## Security Considerations

### Password Security

- Passwords hashed with **bcrypt** (industry standard)
- Minimum password length: **8 characters**
- Passwords never stored in plaintext
- Passwords never returned in API responses

### JWT Security

- Tokens signed with **HS256** algorithm
- Token expiration: **30 minutes** (configurable)
- Secret key loaded from environment variable
- Token validation on every protected request

### HTTPS Required

In production:
- HTTPS must be enforced
- JWT tokens transmitted only over encrypted connections
- Set `SECRET_KEY` via secure environment variable

### Rate Limiting

Consider adding rate limiting to auth endpoints:
- `/auth/login` - prevent brute force attacks
- `/auth/register` - prevent spam accounts

### CORS Configuration

Configure CORS appropriately:
- Restrict allowed origins in production
- Don't use wildcard (`*`) origins
- Set credentials flag correctly

---

## Testing

### Authentication Tests

```python
def test_register_success(client):
    """Test user registration."""
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert "hashed_password" not in response.json()

def test_login_success(client, test_user):
    """Test successful login."""
    response = client.post("/auth/login", data={
        "username": test_user.email,
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_protected_endpoint_requires_auth(client):
    """Test protected endpoint rejects unauthenticated requests."""
    response = client.get("/auth/me")
    assert response.status_code == 401
```

### Permission Tests

```python
def test_can_create_entity_active_user():
    """Active user can create entities."""
    user = User(is_active=True, is_superuser=False)
    assert can_create_entity(user) == True

def test_cannot_edit_others_entity():
    """Non-owner cannot edit entity."""
    user = User(id=uuid4(), is_active=True, is_superuser=False)
    other_user_id = uuid4()
    assert can_edit_entity(user, other_user_id) == False

def test_superuser_can_edit_any_entity():
    """Superuser can edit any entity."""
    user = User(id=uuid4(), is_active=True, is_superuser=True)
    other_user_id = uuid4()
    assert can_edit_entity(user, other_user_id) == True
```

---

## Migration Guide

### Running the Migration

```bash
# From backend directory
cd backend

# Install dependencies (if using uv)
uv pip install -e .

# Run migrations
uv run alembic upgrade head
```

### Creating First Superuser

After migration, create a superuser manually:

```python
# In Python shell or migration script
from app.models.user import User
from app.utils.auth import hash_password
from app.database import SessionLocal

async with SessionLocal() as db:
    superuser = User(
        email="admin@example.com",
        hashed_password=hash_password("securepassword"),
        is_active=True,
        is_superuser=True
    )
    db.add(superuser)
    await db.commit()
```

Or via SQL:

```sql
INSERT INTO users (id, email, hashed_password, is_active, is_superuser, created_at)
VALUES (
    gen_random_uuid(),
    'admin@example.com',
    '$2b$12$...', -- Generate via: python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('yourpassword'))"
    true,
    true,
    NOW()
);
```

---

## Troubleshooting

### "Could not validate credentials" Error

**Cause**: Invalid or expired JWT token

**Solution**:
- Check token is included in `Authorization: Bearer <token>` header
- Verify token hasn't expired (30 minute default)
- Login again to get fresh token

### "Email already registered" Error

**Cause**: Attempting to register with existing email

**Solution**:
- Use different email
- Or login with existing account

### "Incorrect email or password" Error

**Cause**: Invalid login credentials

**Solution**:
- Verify email is correct
- Verify password is correct
- Check user account exists in database

### "Inactive user account" Error

**Cause**: User's `is_active` flag is false

**Solution**:
- Reactivate user account (requires superuser or database access)

```sql
UPDATE users SET is_active = true WHERE email = 'user@example.com';
```

---

## Additional Features Implemented

### Refresh Tokens ✅
- **Implemented**: Stateful refresh tokens with database storage
- 7-day expiration (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- Token revocation mechanism (logout)
- Stored as bcrypt hash in `refresh_tokens` table
- See `app/models/refresh_token.py`

### Email Verification ✅
- **Implemented**: Full email verification flow
- Verification tokens with 24-hour expiration
- Configurable via `EMAIL_ENABLED` and `EMAIL_VERIFICATION_REQUIRED`
- SMTP integration with aiosmtplib
- Endpoints: `/auth/verify-email`, `/auth/resend-verification`
- See `app/utils/email.py`

### Password Reset ✅
- **Implemented**: Secure password reset flow
- Reset tokens with expiration
- Email-based token delivery
- Prevents user enumeration (always returns success)
- Endpoints: `/auth/request-password-reset`, `/auth/reset-password`

### Account Management ✅
- **Implemented**: Complete account management
- Profile updates (`PUT /auth/me`)
- Password changes (`POST /auth/change-password`)
- Account deactivation - soft delete (`POST /auth/deactivate`)
- Account deletion - hard delete (`DELETE /auth/me`)

### Audit Logging ✅
- **Implemented**: Security event logging
- Tracks: registration, login, password changes, account deletion
- Stored in `audit_log` table
- See `app/models/audit_log.py` and `app/utils/audit.py`

### Rate Limiting ✅
- **Implemented**: SlowAPI integration
- 5 requests/minute on auth endpoints (configurable)
- 60 requests/minute on general API
- See `app/utils/rate_limit.py`

## Future Enhancements

Potential additions (NOT currently implemented):

### Multi-Factor Authentication
- TOTP support (Time-based One-Time Password)
- Backup codes
- Recovery options
- SMS verification

### OAuth Providers
- Google OAuth
- GitHub OAuth
- Microsoft OAuth
- ORCID (for researchers)

### Advanced Session Management
- Multiple device tracking
- Device fingerprinting
- Trusted device management
- Session history

**Important**: These features should only be added if clearly justified and implemented with the same explicit, auditable approach.

---

## References

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OAuth2 Password Flow](https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/)
- [python-jose Documentation](https://python-jose.readthedocs.io/)
- [passlib Documentation](https://passlib.readthedocs.io/)
- [JWT.io](https://jwt.io/) - JWT debugger

---

## Contact / Support

For questions or issues with authentication:
1. Check this documentation
2. Review CODE_GUIDE.md for coding patterns
3. Review ARCHITECTURE.md for design rationale
4. Check GitHub issues

**Remember**: Authentication is security-critical. When in doubt, prefer explicit, boring code over clever abstractions.
