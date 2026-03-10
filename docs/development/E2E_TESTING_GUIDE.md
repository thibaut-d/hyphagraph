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

### Test Data

```typescript
import { ADMIN_USER, generateEntityName } from '../../fixtures/test-data';

const entityName = generateEntityName('test-entity');
```

### Best Practices

1. **Use API login** for speed (except when testing login UI)
2. **Generate unique names** for test data (use timestamps)
3. **Wait for visibility** before interacting with elements
4. **Use semantic selectors** (`getByRole`, `getByLabel`) over CSS selectors
5. **Each test should be independent** — create its own data
6. **Use fixtures** for reusable test data

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

- **Base URL**: `http://localhost:3000` (override with `BASE_URL`)
- **Timeout**: 30 seconds per test
- **Retries**: 2 on CI, 0 locally
- **Workers**: 6 parallel
- **Browsers**: Chromium, Firefox, WebKit
