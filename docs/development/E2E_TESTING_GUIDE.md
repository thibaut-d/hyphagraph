# E2E Testing Guide

How to set up, run, write, and debug E2E tests for HyphaGraph using Playwright.

---

## Prerequisites

- Docker Desktop installed and running
- Node.js 20+

## Environment Setup

The E2E tests run against isolated Docker containers defined in `docker-compose.e2e.yml`:

- **Database (PostgreSQL)** — Port 5433
- **Backend API (FastAPI)** — Port 8001
- **Frontend (React + Vite)** — Port 3001

### Starting the Environment

```bash
docker compose -f docker-compose.e2e.yml up -d

# View logs
docker compose -f docker-compose.e2e.yml logs -f

# Stop
docker compose -f docker-compose.e2e.yml down

# Rebuild after code changes
docker compose -f docker-compose.e2e.yml build --no-cache web
docker compose -f docker-compose.e2e.yml up -d
```

### Verifying Services

```bash
curl http://localhost:8001/health          # API health
curl -I http://localhost:3001              # Frontend
```

---

## Running Tests

Environment variables:
- `BASE_URL` — Frontend URL (default: `http://localhost:3001`)
- `API_URL` — Backend API URL (default: `http://localhost:8001`)

```bash
cd e2e

# All tests
BASE_URL=http://localhost:3001 API_URL=http://localhost:8001 npm test

# Specific suite
npx playwright test tests/entities/crud.spec.ts
npx playwright test tests/auth/

# Interactive modes
npx playwright test --ui         # UI mode
npx playwright test --headed     # See browser
npx playwright test --debug      # Debug mode

# Specific test by name
npx playwright test -g "should create a new entity"

# Specific browser
npx playwright test --project=chromium
```

---

## Debugging

### View Report

```bash
npx playwright show-report
```

### View Trace (failed tests)

```bash
npx playwright show-trace test-results/[test-name]/trace.zip
```

### Verbose Output

```bash
DEBUG=pw:api npx playwright test
```

Test configuration automatically captures screenshots on failure, videos for all tests, and traces on failure. Find them in `test-results/`.

---

## Writing Tests

### Test Structure

```
e2e/tests/
├── auth/           # Authentication tests
├── entities/       # Entity CRUD
├── sources/        # Source CRUD
├── relations/      # Relation CRUD
├── inferences/     # Inference tests
└── explanations/   # Explanation tests
```

### Example Test

```typescript
import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI } from '../../fixtures/auth-helpers';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test('should do something', async ({ page }) => {
    await page.goto('/some-page');
    await expect(page.locator('text=Expected Text')).toBeVisible();
    await page.getByLabel(/field name/i).fill('value');
    await page.getByRole('button', { name: /submit/i }).click();
    await expect(page).toHaveURL(/\/success-page/);
  });
});
```

### Authentication Helpers

```typescript
import { loginAsAdminViaAPI, loginViaUI, logout, clearAuthState } from '../../fixtures/auth-helpers';

await loginAsAdminViaAPI(page);                          // Fast API login (most tests)
await loginViaUI(page, 'user@example.com', 'password');  // UI login (login flow tests)
await logout(page);
await clearAuthState(page);
```

### Test Data & Cleanup

Import from `test-fixtures` instead of `@playwright/test` to get automatic cleanup:

```typescript
import { test, expect } from '../../fixtures/test-fixtures';
```

Three fixtures are provided per test:

| Fixture | Returns | Use for |
|---------|---------|---------|
| `testSlug(label)` | `e2e-{test-title}-{label}-{ts}` | Entity slugs, URL slugs |
| `testLabel(label)` | `[e2e] Suite > Test: label` | Source titles, display names |
| `cleanup.track(type, id)` | `void` | Register any created DB item |

**Full example:**

```typescript
import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState, getAccessToken } from '../../fixtures/auth-helpers';

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // UI-created item: extract ID from URL, track it
  test('should create an entity', async ({ page, cleanup, testSlug }) => {
    const slug = testSlug('my-entity');
    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(slug);
    await page.getByRole('button', { name: /create/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);  // auto-deleted after test
  });

  // API-created item: get ID from response
  test('should use a seeded source', async ({ page, cleanup, testLabel, testSlug }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const token = await getAccessToken(page);
    const resp = await page.request.post(`${API_URL}/api/sources/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: { title: testLabel('source'), url: `https://example.com/${testSlug('url')}`, kind: 'study' },
    });
    const { id } = await resp.json();
    cleanup.track('source', id);  // auto-deleted after test
  });
});
```

**Naming rules:**
- Entity slugs must be URL-safe → use `testSlug(label)`
- Source titles and other display fields → use `testLabel(label)`
- The `[e2e]` prefix makes test data identifiable in the DB at a glance
- If an item survives a run, its name tells you exactly which test created it

**Cleanup:** runs automatically after each test (relations → sources → entities). Items the test itself deletes are silently skipped (404 is ignored).

### Best Practices

1. **Use API login** for speed (except when testing login UI)
2. **Always track created items** with `cleanup.track(type, id)` — never leave orphan records
3. **Use `testSlug` / `testLabel`** instead of raw timestamps — embeds the test name for traceability
4. **Wait for visibility** before interacting with elements
5. **Use semantic selectors** (`getByRole`, `getByLabel`) over CSS selectors
6. **Each test should be independent** — create its own data, clean it up via `cleanup`

---

## Troubleshooting

### Services Not Starting

```bash
docker compose -f docker-compose.e2e.yml logs              # Check logs
docker compose -f docker-compose.e2e.yml down -v            # Remove volumes
docker compose -f docker-compose.e2e.yml up -d              # Restart fresh
```

### Tests Timing Out

- Check services are ready: `curl http://localhost:8001/health`
- Increase timeout: `await expect(element).toBeVisible({ timeout: 10000 });`

### Authentication Failures

- Verify admin credentials match between `docker-compose.e2e.yml` and `e2e/fixtures/test-data.ts`
- Check API URL is `http://localhost:8001` (not 8000)

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :3001

# Linux/Mac
lsof -i :3001
```

### Browser Issues

```bash
npx playwright install          # Install browsers
npx playwright install --force  # Force reinstall
```

---

## Configuration

Key settings in `playwright.config.ts`:

- **Base URL**: `http://localhost` (override with `BASE_URL`; e2e Docker compose exposes frontend on port 3001 — set `BASE_URL=http://localhost:3001`)
- **Timeout**: 30 seconds per test
- **Retries**: 2 on CI, 1 locally
- **Workers**: 1 (sequential to avoid database conflicts)
- **Browsers**: Chromium only (Firefox/WebKit commented out; uncomment in `playwright.config.ts` for cross-browser runs)
