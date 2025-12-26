# Refresh Token Migration Guide

This document explains how to apply the refresh token migration to your database.

## Migration Overview

**Migration ID:** `004_add_refresh_tokens`
**Revision:** `003_add_users` → `004_add_refresh_tokens`
**File:** `backend/alembic/versions/20241227_add_refresh_tokens.py`

This migration adds the `refresh_tokens` table required for JWT token refresh functionality.

## Running the Migration

### Option 1: Using Docker (Recommended)

If you're running HyphaGraph with Docker Compose:

```bash
# Start the containers if not already running
docker compose up -d

# Run the migration inside the backend container
docker compose exec api alembic upgrade head
```

### Option 2: Local Development

If you're running locally without Docker:

```bash
# Navigate to backend directory
cd backend

# Install dependencies with uv (if not already done)
uv pip install -e .

# Run the migration
alembic upgrade head
```

### Option 3: Manual Python Environment

If you have a Python virtual environment set up:

```bash
cd backend

# Activate your virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Run migration
alembic upgrade head
```

## Verifying the Migration

After running the migration, verify it succeeded:

```bash
# Check current migration version
alembic current

# You should see:
# 004_add_refresh_tokens (head)
```

You can also verify the table was created by connecting to your database and checking for the `refresh_tokens` table:

```sql
-- PostgreSQL
\dt refresh_tokens

-- Or check all tables
\dt
```

## What Gets Created

The migration creates:

- **Table:** `refresh_tokens`
  - `id` (UUID, primary key)
  - `user_id` (UUID, foreign key to users)
  - `token_hash` (String, unique, hashed token)
  - `expires_at` (DateTime with timezone)
  - `is_revoked` (Boolean, default false)
  - `created_at` (DateTime with timezone)
  - `revoked_at` (DateTime with timezone, nullable)

- **Indexes:**
  - `ix_refresh_tokens_user_id` on `user_id`
  - `ix_refresh_tokens_token_hash` on `token_hash` (unique)
  - `ix_refresh_tokens_expires_at` on `expires_at`

- **Foreign Key:** `user_id` references `users.id` with CASCADE delete

## Rollback (if needed)

If you need to rollback this migration:

```bash
cd backend
alembic downgrade -1
```

This will drop the `refresh_tokens` table.

## Troubleshooting

### Error: "Can't locate revision identifier"

This means Alembic can't find the migration files. Ensure you're in the `backend` directory and the `alembic/versions/` folder contains the migration file.

### Error: "Target database is not up to date"

Run all pending migrations:
```bash
alembic upgrade head
```

### Error: "relation 'users' does not exist"

The users table migration must be applied first:
```bash
alembic upgrade 003_add_users
alembic upgrade 004_add_refresh_tokens
```

Or upgrade everything:
```bash
alembic upgrade head
```

## Next Steps

After applying the migration:

1. ✅ The refresh token system is ready to use
2. ✅ Login endpoint will return both access and refresh tokens
3. ✅ Token refresh endpoint is available at `POST /api/auth/refresh`
4. ✅ Logout endpoint will revoke refresh tokens at `POST /api/auth/logout`
5. ✅ Frontend will automatically refresh expired access tokens

The authentication system is now fully functional with automatic token refresh!
