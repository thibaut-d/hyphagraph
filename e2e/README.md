# HyphaGraph E2E Tests

End-to-end tests using Playwright.

## Quick Start

```bash
# 1. Start E2E environment
docker compose -f docker-compose.e2e.yml up -d

# 2. Wait for services (~30 seconds)

# 3. Install and run
cd e2e
npm install
BASE_URL=http://localhost:3001 API_URL=http://localhost:8001 npm test
```

## Running Tests

```bash
# All tests
npm test

# Specific suite
npx playwright test tests/auth/
npx playwright test tests/entities/crud.spec.ts

# Interactive modes
npx playwright test --ui       # UI mode
npx playwright test --headed   # See browser
npx playwright test --debug    # Debug mode

# View report
npx playwright show-report
```

## Test Structure

```
e2e/
├── tests/
│   ├── auth/              # Authentication flows
│   ├── entities/          # Entity CRUD
│   ├── sources/           # Source CRUD
│   ├── relations/         # Relation CRUD
│   ├── inferences/        # Inference viewing
│   └── explanations/      # Explanation traces
├── fixtures/
│   ├── test-data.ts       # Test data generators
│   └── auth-helpers.ts    # Authentication helpers
├── utils/
│   ├── db-setup.ts        # Database setup/teardown
│   └── api-client.ts      # API client utilities
└── playwright.config.ts
```

## Environment Variables

- `BASE_URL` — Frontend URL (default: `http://localhost:3001`)
- `API_URL` — Backend API URL (default: `http://localhost:8001`)

For setup details, debugging, writing tests, and troubleshooting, see [E2E Testing Guide](../docs/development/E2E_TESTING_GUIDE.md).
