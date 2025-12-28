# Authentication Setup Guide

Quick reference for setting up and testing the HyphaGraph authentication system.

---

## Prerequisites

1. Python 3.12+
2. PostgreSQL database running
3. Backend dependencies installed

---

## Installation

### 1. Install Dependencies

```bash
cd backend

# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

This installs:
- `python-jose[cryptography]` - JWT handling
- `passlib[bcrypt]` - Password hashing
- `python-multipart` - OAuth2 form parsing

### 2. Configure Environment

The `backend/.env.test` file is already included in the repository with test defaults:

```bash
# Database - using SQLite for testing
DATABASE_URL=sqlite+aiosqlite:///./test.db

# Security (test values only!)
SECRET_KEY=test-secret-key-for-testing-only
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

You can customize this file if needed for your local setup.

**Note**: In production, use environment variables directly instead of `.env.test` files.

**⚠️ Security Warning**: Generate a secure SECRET_KEY for production:

```bash
# Generate random secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Run Database Migrations

```bash
cd backend

# Check current migration status
uv run alembic current

# Run all migrations (including auth)
uv run alembic upgrade head

# Verify users table was created
psql -d hyphagraph -c "\d users"
```

Expected output:
```
                          Table "public.users"
     Column      |           Type           | Collation | Nullable | Default
-----------------+--------------------------+-----------+----------+---------
 id              | uuid                     |           | not null |
 email           | character varying        |           | not null |
 hashed_password | character varying        |           | not null |
 is_active       | boolean                  |           | not null | true
 is_superuser    | boolean                  |           | not null | false
 created_at      | timestamp with time zone |           | not null | now()
```

---

## Testing the Authentication System

### 1. Start the Backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

The API should be available at: `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### 2. Register a User

Using curl:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

Expected response:
```json
{
  "id": "uuid-here",
  "email": "test@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-12-27T10:00:00Z"
}
```

Using Python:
```python
import requests

response = requests.post(
    "http://localhost:8000/auth/register",
    json={
        "email": "test@example.com",
        "password": "testpassword123"
    }
)
print(response.json())
```

Using FastAPI docs (`/docs`):
1. Go to http://localhost:8000/docs
2. Find `POST /auth/register`
3. Click "Try it out"
4. Fill in email and password
5. Click "Execute"

### 3. Login and Get Token

Using curl:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpassword123"
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Note**: The OAuth2 form uses "username" but we treat it as email.

Using Python:
```python
response = requests.post(
    "http://localhost:8000/auth/login",
    data={
        "username": "test@example.com",  # Note: username field
        "password": "testpassword123"
    }
)
token = response.json()["access_token"]
print(f"Access token: {token}")
```

### 4. Access Protected Endpoint

Using curl:
```bash
# Replace <token> with actual token from step 3
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

Expected response:
```json
{
  "id": "uuid-here",
  "email": "test@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-12-27T10:00:00Z"
}
```

Using Python:
```python
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8000/auth/me",
    headers=headers
)
print(response.json())
```

Using FastAPI docs:
1. Go to http://localhost:8000/docs
2. Click the "Authorize" button (top right)
3. Enter token in the value field
4. Click "Authorize"
5. Now all protected endpoints will include the token automatically

---

## Creating a Superuser

### Method 1: Via Database

```sql
-- Connect to database
psql -d hyphagraph

-- Create superuser
INSERT INTO users (id, email, hashed_password, is_active, is_superuser, created_at)
VALUES (
    gen_random_uuid(),
    'admin@example.com',
    -- Hash generated with: python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('adminpass123'))"
    '$2b$12$abcdefghijklmnopqrstuvwxyz1234567890abcdefghij',
    true,
    true,
    NOW()
);
```

### Method 2: Via Python Script

Create `backend/create_superuser.py`:

```python
import asyncio
from app.database import SessionLocal
from app.models.user import User
from app.utils.auth import hash_password

async def create_superuser():
    async with SessionLocal() as db:
        superuser = User(
            email="admin@example.com",
            hashed_password=hash_password("adminpass123"),
            is_active=True,
            is_superuser=True
        )
        db.add(superuser)
        await db.commit()
        print(f"Superuser created: {superuser.email}")

if __name__ == "__main__":
    asyncio.run(create_superuser())
```

Run it:
```bash
cd backend
uv run python create_superuser.py
```

### Method 3: Via API + Manual Update

1. Register normally via API
2. Update in database:

```sql
UPDATE users
SET is_superuser = true
WHERE email = 'admin@example.com';
```

---

## Verification Checklist

After setup, verify:

- [ ] Users table exists in database
- [ ] Can register new user via `/auth/register`
- [ ] Can login and receive JWT token via `/auth/login`
- [ ] Can access `/auth/me` with valid token
- [ ] Cannot access `/auth/me` without token (401 error)
- [ ] Cannot access `/auth/me` with invalid token (401 error)
- [ ] Token expires after configured time (default 30 min)
- [ ] Superuser exists in database
- [ ] `SECRET_KEY` is set via environment variable (production)

---

## Common Issues

### Issue: "alembic: command not found"

**Solution**: Use `uv run alembic` instead of `alembic`

```bash
uv run alembic upgrade head
```

### Issue: "Could not validate credentials"

**Causes**:
- Token expired (30 minute default)
- Token malformed
- SECRET_KEY changed since token was issued

**Solution**: Login again to get fresh token

### Issue: "Email already registered"

**Cause**: User with that email already exists

**Solutions**:
- Use different email
- Delete existing user from database
- Login with existing account

### Issue: "Incorrect email or password"

**Cause**: Invalid credentials

**Solution**: Verify email and password are correct

### Issue: Import errors

**Cause**: Missing dependencies

**Solution**:
```bash
cd backend
uv pip install -e .
```

### Issue: "relation 'users' does not exist"

**Cause**: Migration not run

**Solution**:
```bash
cd backend
uv run alembic upgrade head
```

---

## Next Steps

After authentication is working:

1. **Update existing endpoints** to require authentication
2. **Add permission checks** using `app.utils.permissions`
3. **Pass user_id** to services for provenance tracking
4. **Set SECRET_KEY** in production environment
5. **Enable HTTPS** in production
6. **Add rate limiting** to auth endpoints
7. **Configure CORS** appropriately

See `AUTHENTICATION.md` for detailed documentation.

---

## Quick Reference

### Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Key Endpoints

- `POST /auth/register` - Create account
- `POST /auth/login` - Get JWT token
- `GET /auth/me` - Get user info (requires auth)

### Dependencies

```python
from app.dependencies.auth import get_current_user
from app.utils.permissions import can_create_entity, require_permission
```

### Example Protected Endpoint

```python
@router.post("/entities")
async def create_entity(
    payload: EntityWrite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_permission(can_create_entity(current_user))
    service = EntityService(db)
    return await service.create(payload, user_id=current_user.id)
```

---

## Documentation

- `AUTHENTICATION.md` - Complete auth documentation
- `CODE_GUIDE.md` - Coding guidelines and patterns
- `ARCHITECTURE.md` - System architecture and design rationale
- FastAPI docs - http://localhost:8000/docs
