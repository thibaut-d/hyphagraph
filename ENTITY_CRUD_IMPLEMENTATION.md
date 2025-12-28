# Entity CRUD Implementation - Testing Guide

## Changes Made

### 1. Fixed Critical Authentication Bug
**Files Modified:**
- `frontend/src/auth/AuthContext.tsx`
- `frontend/src/components/ProtectedRoute.tsx`

**Issue:** Race condition where `ProtectedRoute` would redirect to `/account` before async `getMe()` completed, even when valid auth tokens existed in localStorage.

**Fix:** Added `loading` state to AuthContext that tracks authentication verification. ProtectedRoute now shows a loading spinner instead of redirecting while checking auth.

### 2. Updated Entity Display
**Files Modified:**
- `frontend/src/types/entity.ts` - Updated EntityRead interface
- `frontend/src/views/EntitiesView.tsx` - Display slug instead of label
- `frontend/src/views/EntityDetailView.tsx` - Display slug, add Back button

**Changes:**
- List view shows `entity.slug` with `entity.summary?.en` as secondary text
- Detail view shows `entity.slug` as title with summary
- Added "Back" button to navigate to entities list
- Updated delete confirmation to show slug

### 3. Entity CRUD Views
All required views already existed and are correctly implemented:
- ✅ `CreateEntityView.tsx` - Form with Slug and Summary fields
- ✅ `EditEntityView.tsx` - Form to edit entities
- ✅ `EntityDetailView.tsx` - View with Edit/Delete buttons
- ✅ `EntitiesView.tsx` - List with filters and pagination

## Rebuilding for Tests

Since the E2E environment runs in Docker, you need to rebuild containers to see the changes:

```bash
# Stop current containers
docker compose -f docker-compose.e2e.yml down

# Rebuild with no cache to ensure fresh build
docker compose -f docker-compose.e2e.yml build --no-cache web

# Start services
docker compose -f docker-compose.e2e.yml up -d

# Wait for services to be healthy (~30 seconds)
sleep 30

# Verify services are running
curl http://localhost:8001/health
curl -I http://localhost:3001
```

## Running Entity CRUD Tests

```bash
cd e2e
BASE_URL=http://localhost:3001 API_URL=http://localhost:8001 npx playwright test tests/entities/crud.spec.ts
```

### Expected Results

With the authentication fix, all 9 entity CRUD tests should pass:

1. ✅ should create a new entity
2. ✅ should view entity list
3. ✅ should view entity detail
4. ✅ should edit an entity
5. ✅ should delete an entity
6. ✅ should show validation error for duplicate slug
7. ✅ should show validation error for empty slug
8. ✅ should search/filter entities
9. ✅ should navigate between entities list and detail

### Test Selectors Verified

**Form Labels:**
- Slug field: "Slug" → matches `/slug/i` ✅
- Summary field: "Summary (English)" → matches `/summary.*en/i` ✅

**Buttons:**
- Create: "Create Entity" → matches `/create|submit/i` ✅
- Edit/Save: "Save Changes" → matches `/save|update/i` ✅
- Edit button: "Edit" → matches `/edit/i` ✅
- Delete: "Delete" → matches `/delete/i` ✅
- Back: "Back" → matches `/back/i` ✅

**Page Titles:**
- Create page: "Create Entity" ✅
- List page: "Entities" (as h4) ✅

## Impact on Other Tests

The authentication fix will significantly improve pass rates across ALL test suites:
- Auth tests (login, logout, register)
- Source CRUD tests
- Relation CRUD tests
- Inference tests
- Explanation tests

All tests using `loginAsAdminViaAPI()` or `loginViaAPI()` were previously failing due to the race condition causing immediate redirects to `/account`.

## Verification Checklist

After rebuilding containers:

- [ ] Services start successfully
- [ ] Can access http://localhost:3001
- [ ] Can access http://localhost:8001/health
- [ ] Login works at http://localhost:3001/account
- [ ] Can navigate to http://localhost:3001/entities/new after login
- [ ] Create Entity form is visible (not redirected to /account)
- [ ] All 9 entity CRUD tests pass

## Files Changed Summary

```
frontend/src/auth/AuthContext.tsx           - Added loading state, fixed TypeScript type
frontend/src/components/ProtectedRoute.tsx  - Wait for auth loading
frontend/src/types/entity.ts                - Updated interface to match backend
frontend/src/views/EntitiesView.tsx         - Display slug instead of label
frontend/src/views/EntityDetailView.tsx     - Display slug, add back button, remove unused imports
```

## All Changes Applied

### 1. frontend/src/auth/AuthContext.tsx
- Added `loading: boolean` to `AuthContextValue` type
- Initialize `loading` state as `true` when auth token exists
- Set `loading = true` before calling `getMe()`
- Set `loading = false` after user data loads or on error
- Added TypeScript type annotation for userData
- Export `loading` in context provider

### 2. frontend/src/components/ProtectedRoute.tsx
- Import CircularProgress and Box from MUI
- Destructure `loading` from useAuth
- Show loading spinner while `loading === true`
- Only redirect to /account after loading completes and user is null

### 3. frontend/src/types/entity.ts
- Updated EntityRead interface fields:
  - Added: `created_at`, `slug`, `summary`
  - Made optional: `kind`, `label`, `synonyms`, `ontology_ref`

### 4. frontend/src/views/EntitiesView.tsx
- Display `e.slug` instead of `e.label` in list
- Show `e.summary?.en` as secondary text (fallback to `e.kind`)

### 5. frontend/src/views/EntityDetailView.tsx
- Added ArrowBackIcon import
- Removed unused `resolveLabel` import
- Removed unused `i18n` from useTranslation
- Added Back button linking to /entities
- Display `entity.slug` as h4 title
- Display `entity.summary?.en` as secondary text
- Updated delete confirmation to show `entity.slug`

## Quick Test Command

```bash
# Full rebuild and test in one command
docker compose -f docker-compose.e2e.yml down && \
docker compose -f docker-compose.e2e.yml build --no-cache web && \
docker compose -f docker-compose.e2e.yml up -d && \
sleep 30 && \
cd e2e && \
BASE_URL=http://localhost:3001 API_URL=http://localhost:8001 npx playwright test tests/entities/crud.spec.ts
```
