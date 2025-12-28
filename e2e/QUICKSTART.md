# E2E Testing Quick Start

## Simplified Setup (Recommended for Development)

Since Docker Compose build has dependency conflicts, here's the simplest way to run E2E tests:

### Option 1: Run Against Existing Development Environment

If you already have the Hyphagraph app running locally:

```bash
# Ensure your app is running on http://localhost (via Docker Compose or manually)
# Then run E2E tests:
cd e2e
npm test
```

### Option 2: Manual Local Setup

1. **Start PostgreSQL** (locally or via Docker):
   ```bash
   docker run -d \
     -e POSTGRES_USER=hyphagraph \
     -e POSTGRES_PASSWORD=hyphagraph_password \
     -e POSTGRES_DB=hyphagraph \
     -p 5432:5432 \
     postgres:16
   ```

2. **Start Backend**:
   ```bash
   cd backend
   # Create .env with DATABASE_URL=postgresql+asyncpg://hyphagraph:hyphagraph_password@localhost:5432/hyphagraph
   uv run uvicorn app.main:app --reload --port 8000
   ```

3. **Start Frontend**:
   ```bash
   cd frontend
   npm run dev  # Runs on port 3000
   ```

4. **Run E2E Tests**:
   ```bash
   cd e2e
   # Update playwright.config.ts to use http://localhost:3000
   npm test
   ```

### Option 3: Docker Compose (Requires Fixing Dependencies)

The Docker Compose setup has npm peer dependency conflicts. To fix:

1. Update `frontend/Dockerfile`:
   ```dockerfile
   RUN npm install --legacy-peer-deps
   ```

2. Start services:
   ```bash
   docker-compose -f docker-compose.e2e.yml up -d
   ```

3. Run tests:
   ```bash
   cd e2e
   BASE_URL=http://localhost:3001 API_URL=http://localhost:8001 npm test
   ```

## Current Status

✅ E2E test suite implemented (~60-70 tests)
✅ Playwright configuration complete
⚠️  Docker Compose E2E has npm dependency conflicts
✅ Tests can run against manual/local setup

## Running Individual Tests

```bash
# Run specific test file
npm test -- tests/auth/login.spec.ts

# Run in headed mode (see browser)
npm run test:headed

# Run with UI
npm run test:ui

# Debug mode
npm run test:debug
```

## Troubleshooting

### Peer Dependency Errors in Docker

The frontend has eslint peer dependency conflicts. Solutions:
- Use `--legacy-peer-deps` flag in Dockerfile
- Or run tests against local setup instead of Docker

### Tests Fail with Connection Errors

Ensure services are running and accessible:
- Frontend: http://localhost:3000 (or configured BASE_URL)
- Backend API: http://localhost:8000/api (or configured API_URL)

### Port Conflicts

Change ports in:
- `e2e/playwright.config.ts` - Update `baseURL`
- Environment variables: `BASE_URL` and `API_URL`

## Next Steps

1. Fix Docker Compose dependency issues (update Dockerfile)
2. Run tests against local development setup
3. Review test failures and update selectors as needed
4. Add CI/CD when Docker setup is stable
