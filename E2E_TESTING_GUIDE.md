# E2E Testing Guide

This guide explains how to set up and run end-to-end (E2E) tests for HyphaGraph using Playwright.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Setup](#environment-setup)
- [Running Tests](#running-tests)
- [Debugging Tests](#debugging-tests)
- [Writing Tests](#writing-tests)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- **Docker Desktop** installed and running
- **Node.js 20+** installed
- **Git Bash** (Windows) or any Unix shell

## Quick Start

### Option 1: Run All Tests

```bash
# 1. Start the E2E environment
docker compose -f docker-compose.e2e.yml up -d

# 2. Wait for services to be ready (~30 seconds)
sleep 30

# 3. Run all tests
cd e2e
BASE_URL=http://localhost:3001 API_URL=http://localhost:8001 npm test
```

### Option 2: Use the Automated Script

**Windows:**
```cmd
rebuild-and-test.bat
```

**Linux/Mac/Git Bash:**
```bash
./rebuild-and-test.sh
```

## Environment Setup

### Docker Compose E2E Environment

The E2E tests run against isolated Docker containers defined in `docker-compose.e2e.yml`:

- **Database (PostgreSQL)** - Port 5433 (to avoid conflicts with dev DB)
- **Backend API (FastAPI)** - Port 8001
- **Frontend (React + Vite)** - Port 3001

### Starting the E2E Environment

```bash
# Start all services in background
docker compose -f docker-compose.e2e.yml up -d

# View logs
docker compose -f docker-compose.e2e.yml logs -f

# Stop all services
docker compose -f docker-compose.e2e.yml down

# Rebuild a specific service (e.g., after code changes)
docker compose -f docker-compose.e2e.yml build --no-cache web
docker compose -f docker-compose.e2e.yml up -d
```

### Verifying Services Are Running

```bash
# Check API health
curl http://localhost:8001/health
# Expected: {"status":"ok"}

# Check frontend
curl -I http://localhost:3001
# Expected: HTTP/1.1 200 OK

# Check database
docker compose -f docker-compose.e2e.yml exec db psql -U hyphagraph_test -c "SELECT version();"
```

## Running Tests

### Environment Variables

Tests require these environment variables:

- `BASE_URL` - Frontend URL (default: `http://localhost:3001`)
- `API_URL` - Backend API URL (default: `http://localhost:8001`)

### Run All Tests

```bash
cd e2e
BASE_URL=http://localhost:3001 API_URL=http://localhost:8001 npm test
```

### Run Specific Test Suite

```bash
# Entity CRUD tests
npx playwright test tests/entities/crud.spec.ts

# Authentication tests
npx playwright test tests/auth/

# Sources tests
npx playwright test tests/sources/

# Relations tests
npx playwright test tests/relations/
```

### Run Tests in UI Mode (Interactive)

```bash
npx playwright test --ui
```

### Run Tests in Headed Mode (See Browser)

```bash
npx playwright test --headed
```

### Run Specific Test by Name

```bash
npx playwright test -g "should create a new entity"
```

### Run Tests on Specific Browser

```bash
# Chromium only
npx playwright test --project=chromium

# Firefox only
npx playwright test --project=firefox

# WebKit only
npx playwright test --project=webkit
```

## Debugging Tests

### View Test Report

After running tests, view the HTML report:

```bash
npx playwright show-report
```

### View Playwright Trace

For failed tests, Playwright automatically captures traces. View them with:

```bash
npx playwright show-trace test-results/[test-name]/trace.zip
```

### Debug Mode

Run tests in debug mode with inspector:

```bash
npx playwright test --debug
```

### Console Logs

Enable verbose output:

```bash
DEBUG=pw:api npx playwright test
```

### Screenshots and Videos

Test configuration automatically captures:
- **Screenshots** on failure
- **Videos** for all tests
- **Traces** on failure

Find them in `test-results/` directory.

## Writing Tests

### Test Structure

Tests are organized by feature:

```
e2e/
├── tests/
│   ├── auth/           # Authentication tests
│   ├── entities/       # Entity CRUD tests
│   ├── sources/        # Source CRUD tests
│   ├── relations/      # Relation CRUD tests
│   ├── inferences/     # Inference tests
│   └── explanations/   # Explanation tests
├── fixtures/           # Test data and helpers
│   ├── auth-helpers.ts
│   └── test-data.ts
└── playwright.config.ts
```

### Example Test

```typescript
import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI } from '../../fixtures/auth-helpers';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsAdminViaAPI(page);
  });

  test('should do something', async ({ page }) => {
    // Navigate to page
    await page.goto('/some-page');

    // Wait for element
    await expect(page.locator('text=Expected Text')).toBeVisible();

    // Interact with page
    await page.getByLabel(/field name/i).fill('value');
    await page.getByRole('button', { name: /submit/i }).click();

    // Assert result
    await expect(page).toHaveURL(/\/success-page/);
  });
});
```

### Authentication Helpers

Use provided helpers for authentication:

```typescript
import {
  loginAsAdminViaAPI,
  loginViaUI,
  logout,
  clearAuthState
} from '../../fixtures/auth-helpers';

// Fast API login (use for most tests)
await loginAsAdminViaAPI(page);

// UI login (use for login flow tests)
await loginViaUI(page, 'user@example.com', 'password');

// Logout
await logout(page);

// Clear auth state
await clearAuthState(page);
```

### Test Data

Use test data fixtures for consistency:

```typescript
import { ADMIN_USER, TEST_USERS, generateEntityName } from '../../fixtures/test-data';

// Use admin credentials
console.log(ADMIN_USER.email);    // admin@example.com
console.log(ADMIN_USER.password); // changeme123

// Generate unique names
const entityName = generateEntityName('test-entity');
```

## Troubleshooting

### Services Not Starting

**Problem:** Docker containers fail to start

**Solutions:**
```bash
# Check Docker is running
docker ps

# Check logs for errors
docker compose -f docker-compose.e2e.yml logs

# Remove old containers and volumes
docker compose -f docker-compose.e2e.yml down -v
docker compose -f docker-compose.e2e.yml up -d
```

### Database Connection Errors

**Problem:** API can't connect to database

**Solutions:**
```bash
# Wait for database to be healthy
docker compose -f docker-compose.e2e.yml ps

# Check database logs
docker compose -f docker-compose.e2e.yml logs db

# Restart services in order
docker compose -f docker-compose.e2e.yml restart db
sleep 10
docker compose -f docker-compose.e2e.yml restart api
```

### Frontend Not Loading

**Problem:** Frontend shows blank page or errors

**Solutions:**
```bash
# Check frontend logs
docker compose -f docker-compose.e2e.yml logs web

# Rebuild frontend
docker compose -f docker-compose.e2e.yml build --no-cache web
docker compose -f docker-compose.e2e.yml up -d

# Check environment variables
docker compose -f docker-compose.e2e.yml exec web env | grep VITE
```

### Tests Timing Out

**Problem:** Tests timeout waiting for elements

**Solutions:**
- Increase timeout in test:
  ```typescript
  await expect(element).toBeVisible({ timeout: 10000 });
  ```
- Check if services are actually ready:
  ```bash
  curl http://localhost:8001/health
  curl http://localhost:3001
  ```
- Check network connectivity in Docker

### Port Already in Use

**Problem:** Ports 3001, 5433, or 8001 already in use

**Solutions:**
```bash
# Find what's using the port (Windows)
netstat -ano | findstr :3001

# Find what's using the port (Linux/Mac)
lsof -i :3001

# Change ports in docker-compose.e2e.yml if needed
# Then update BASE_URL and API_URL when running tests
```

### Authentication Failures

**Problem:** Tests fail with "Not authenticated" errors

**Solutions:**
- Ensure admin user is created:
  ```bash
  docker compose -f docker-compose.e2e.yml logs api | grep -i admin
  ```
- Check admin credentials match in:
  - `docker-compose.e2e.yml` (ADMIN_EMAIL, ADMIN_PASSWORD)
  - `e2e/fixtures/test-data.ts` (ADMIN_USER)
- Verify API URL is correct:
  ```typescript
  // Should be http://localhost:8001 not http://localhost:8000
  const API_URL = process.env.API_URL || 'http://localhost:8001';
  ```

### Playwright Browser Issues

**Problem:** Browsers fail to launch

**Solutions:**
```bash
# Install Playwright browsers
npx playwright install

# Install system dependencies
npx playwright install-deps

# Clear Playwright cache
npx playwright install --force
```

### Test Data Conflicts

**Problem:** Tests fail due to duplicate data

**Solutions:**
- Use unique names:
  ```typescript
  const timestamp = Date.now();
  const entitySlug = `test-entity-${timestamp}`;
  ```
- Clean database between test runs:
  ```bash
  docker compose -f docker-compose.e2e.yml down -v
  docker compose -f docker-compose.e2e.yml up -d
  ```

## Test Configuration

### Playwright Config

Key settings in `playwright.config.ts`:

- **Base URL:** `http://localhost:3000` (override with `BASE_URL` env var)
- **Timeout:** 30 seconds per test
- **Retries:** 2 retries on CI, 0 locally
- **Workers:** 6 parallel workers
- **Browsers:** Chromium, Firefox, WebKit

### CI/CD Integration

For CI environments:

```bash
# Set CI environment variable
export CI=true

# Run tests with retries
npx playwright test --retries=2

# Generate HTML report
npx playwright show-report
```

## Best Practices

1. **Use API login** for speed (except when testing login UI)
2. **Generate unique names** for test data (use timestamps)
3. **Wait for visibility** before interacting with elements
4. **Use semantic selectors** (getByRole, getByLabel) over CSS selectors
5. **Clean up** test data after tests (or use fresh DB)
6. **Run tests in isolation** - each test should be independent
7. **Use fixtures** for reusable test data
8. **Add meaningful assertions** - test the behavior, not the implementation

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Test Generator](https://playwright.dev/docs/codegen) - `npx playwright codegen`
- [Trace Viewer](https://playwright.dev/docs/trace-viewer)
- [VS Code Extension](https://playwright.dev/docs/getting-started-vscode)

## Common Commands Reference

```bash
# Start E2E environment
docker compose -f docker-compose.e2e.yml up -d

# Run all tests
cd e2e && BASE_URL=http://localhost:3001 API_URL=http://localhost:8001 npm test

# Run specific suite
npx playwright test tests/entities/

# Run in UI mode
npx playwright test --ui

# View report
npx playwright show-report

# View trace
npx playwright show-trace test-results/[test]/trace.zip

# Stop E2E environment
docker compose -f docker-compose.e2e.yml down

# Full rebuild
docker compose -f docker-compose.e2e.yml down && \
docker compose -f docker-compose.e2e.yml build --no-cache && \
docker compose -f docker-compose.e2e.yml up -d
```
