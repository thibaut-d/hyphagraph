# Contributing to E2E Tests

## Writing New Tests

### Test Organization

Tests are organized by feature area:
- `tests/auth/` - Authentication and authorization
- `tests/entities/` - Entity CRUD operations
- `tests/sources/` - Source CRUD operations
- `tests/relations/` - Relation CRUD operations
- `tests/inferences/` - Inference viewing and filtering
- `tests/explanations/` - Explanation trace and visualization

### Test Naming Conventions

- Test files: `[feature].spec.ts`
- Test suites: `describe('[Feature Name]')`
- Test cases: `test('should [expected behavior]')`

### Example Test Structure

```typescript
import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI } from '../../fixtures/auth-helpers';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: Login, navigate, seed data
    await loginAsAdminViaAPI(page);
    await page.goto('/feature');
  });

  test('should perform basic action', async ({ page }) => {
    // Arrange
    const testData = 'test value';

    // Act
    await page.getByLabel('Input').fill(testData);
    await page.getByRole('button', { name: 'Submit' }).click();

    // Assert
    await expect(page.locator('text=Success')).toBeVisible();
  });

  test.afterEach(async ({ page }) => {
    // Cleanup if needed
  });
});
```

## Best Practices

### 1. Use Semantic Locators

Prefer role-based and accessible selectors:

```typescript
// Good
await page.getByRole('button', { name: 'Login' });
await page.getByLabel('Email');
await page.getByPlaceholder('Search...');

// Avoid
await page.click('button.login-btn');
await page.fill('#email-input');
```

### 2. Handle Async Operations

Always await async operations and use appropriate timeouts:

```typescript
// Wait for navigation
await page.waitForURL('/dashboard');

// Wait for element to appear
await expect(page.locator('text=Welcome')).toBeVisible({ timeout: 5000 });

// Wait for network to be idle
await page.waitForLoadState('networkidle');
```

### 3. Clean Test Data

Each test should be independent and create its own data:

```typescript
test('should create entity', async ({ page }) => {
  // Generate unique test data
  const entitySlug = generateEntityName('test').toLowerCase().replace(/\s+/g, '-');

  // Create and test
  // ...
});
```

### 4. Use Helper Functions

Reuse common actions through helpers:

```typescript
// Use existing helpers
await loginAsAdminViaAPI(page);

// Create new helpers for repeated actions
async function createTestEntity(page: Page, slug: string) {
  await page.goto('/entities/new');
  await page.getByLabel(/slug/i).fill(slug);
  await page.getByRole('button', { name: /create/i }).click();
}
```

### 5. Handle Optional UI Elements

Some UI elements might not always be present:

```typescript
// Check if element exists before interacting
const filterButton = page.getByRole('button', { name: /filter/i });
if (await filterButton.isVisible({ timeout: 2000 })) {
  await filterButton.click();
}
```

### 6. Use Descriptive Assertions

Make assertions clear and specific:

```typescript
// Good
await expect(page.locator('text=Registration Successful')).toBeVisible();
await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+/);

// Less clear
await expect(page.locator('.message')).toBeVisible();
```

### 7. Group Related Tests

Use describe blocks to organize related tests:

```typescript
test.describe('Entity CRUD', () => {
  test.describe('Create', () => {
    test('should create with valid data', async ({ page }) => {});
    test('should validate required fields', async ({ page }) => {});
  });

  test.describe('Update', () => {
    test('should update existing entity', async ({ page }) => {});
  });
});
```

## Debugging Tests

### Run Single Test

```bash
npm test -- tests/auth/login.spec.ts
```

### Run with Browser Visible

```bash
npm run test:headed
```

### Use Debug Mode

```bash
npm run test:debug
```

### Add Debug Breakpoints

```typescript
test('should debug', async ({ page }) => {
  await page.pause(); // Opens Playwright Inspector
  // ... rest of test
});
```

### View Trace

After a test failure:

```bash
npx playwright show-trace test-results/[path-to-trace].zip
```

## Common Issues

### Services Not Ready

Wait longer for Docker Compose services:

```bash
# Check service status
docker-compose -f docker-compose.e2e.yml ps

# View logs
docker-compose -f docker-compose.e2e.yml logs -f api
```

### Timeout Errors

Increase timeouts for slow operations:

```typescript
await expect(page.locator('text=Loaded')).toBeVisible({ timeout: 10000 });
```

### Flaky Tests

Make tests more resilient:

```typescript
// Wait for stable state
await page.waitForLoadState('networkidle');

// Use retry logic for assertions
await expect(async () => {
  const text = await page.textContent('.status');
  expect(text).toBe('Ready');
}).toPass({ timeout: 5000 });
```

## Continuous Improvement

- Review failed test screenshots and videos
- Update selectors when UI changes
- Add new test coverage for new features
- Refactor duplicate test code into helpers
- Keep tests fast (avoid unnecessary waits)
- Document complex test scenarios

## Questions?

- Check existing tests for examples
- Review Playwright documentation: https://playwright.dev
- Ask in the team chat or create an issue
