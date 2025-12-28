# Hyphagraph E2E Tests

End-to-end tests for Hyphagraph using Playwright.

## Quick Start

**Note:** Docker Compose E2E currently has npm dependency conflicts. Use local setup instead.

```bash
# 1. Install dependencies
cd e2e
npm install

# 2. Ensure Hyphagraph is running
#    - Frontend on http://localhost (or update BASE_URL in playwright.config.ts)
#    - Backend API on http://localhost/api

# 3. Run tests
npm test
```

For detailed setup options, see `QUICKSTART.md`.

## Setup

1. Install dependencies:
```bash
cd e2e
npm install
```

2. Install Playwright browsers (done automatically with npm install):
```bash
npx playwright install
```

## Running Tests

### Prerequisites

Start the E2E environment using Docker Compose:
```bash
# From the project root
docker-compose -f docker-compose.e2e.yml up -d
```

Wait for services to be ready (API on http://localhost:8001, Frontend on http://localhost:3001).

### Run all tests

```bash
npm test
```

### Run tests in headed mode (see browser)

```bash
npm run test:headed
```

### Run tests with UI (interactive mode)

```bash
npm run test:ui
```

### Run tests in debug mode

```bash
npm run test:debug
```

### Run tests for specific browser

```bash
npm run test:chromium
```

### View test report

```bash
npm run test:report
```

## Test Structure

```
e2e/
├── tests/
│   ├── auth/              # Authentication flow tests
│   ├── entities/          # Entity CRUD tests
│   ├── sources/           # Source CRUD tests
│   ├── relations/         # Relation CRUD tests
│   ├── inferences/        # Inference viewing tests
│   └── explanations/      # Explanation trace tests
├── fixtures/
│   ├── test-data.ts       # Test data fixtures
│   └── auth-helpers.ts    # Authentication helpers
├── utils/
│   ├── db-setup.ts        # Database setup/teardown
│   └── api-client.ts      # API client utilities
└── playwright.config.ts   # Playwright configuration
```

## Test Strategy

- **Database**: Fresh database per test suite for isolation
- **Data Seeding**: API-based seeding for realistic data flow
- **Execution**: On-demand (not CI/CD yet)
- **Parallelization**: Enabled for faster execution
- **Artifacts**: Screenshots and videos saved on failure
- **Language**: English only (no i18n testing)

## Writing Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI } from '../fixtures/auth-helpers';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: Login, seed data, etc.
    await loginAsAdminViaAPI(page);
  });

  test('should do something', async ({ page }) => {
    // Navigate
    await page.goto('/some-page');

    // Interact
    await page.click('button[data-testid="action-button"]');

    // Assert
    await expect(page.locator('.success-message')).toBeVisible();
  });

  test.afterEach(async ({ page }) => {
    // Cleanup if needed
  });
});
```

### Using Test Data

```typescript
import { TEST_ENTITIES, generateEntityName } from '../fixtures/test-data';
import { createEntity } from '../utils/api-client';

test('should create entity', async ({ page }) => {
  const token = 'your-auth-token';
  const entity = await createEntity(token, {
    name: generateEntityName('Test'),
    description: TEST_ENTITIES.person.description,
  });

  // Use the created entity in your test
});
```

## Debugging

### Visual Debugging

Use Playwright Inspector for step-by-step debugging:
```bash
npm run test:debug
```

### Trace Viewer

View detailed traces of failed tests:
```bash
npx playwright show-trace test-results/path-to-trace.zip
```

### Screenshots

Screenshots are automatically captured on failure and saved to `test-results/`.

### Videos

Videos are automatically recorded for failed tests and saved to `test-results/`.

## Environment Variables

- `BASE_URL`: Frontend URL (default: http://localhost:3001)
- `API_URL`: Backend API URL (default: http://localhost:8001)

## Common Issues

### Services not ready

If tests fail with connection errors, ensure Docker Compose services are running:
```bash
docker-compose -f docker-compose.e2e.yml ps
```

### Port conflicts

If ports 3001 or 8001 are already in use, stop the conflicting services or update `docker-compose.e2e.yml`.

### Browser installation

If browsers fail to launch, reinstall them:
```bash
npx playwright install --force
```

## CI/CD Integration (Future)

To run tests in CI/CD:

1. Update `docker-compose.e2e.yml` to use production-like settings
2. Add GitHub Actions workflow
3. Configure test retries and parallelization
4. Upload artifacts (screenshots, videos, traces) on failure

Example GitHub Actions workflow (to be implemented):
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - name: Start services
        run: docker-compose -f docker-compose.e2e.yml up -d
      - name: Install dependencies
        run: cd e2e && npm ci
      - name: Run tests
        run: cd e2e && npm test
      - name: Upload artifacts
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: e2e/playwright-report/
```
