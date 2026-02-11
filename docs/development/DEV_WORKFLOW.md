# Development Workflow

Applicable to both human developers and AI agents.

---

## Development Environment

### Docker (recommended)

```bash
docker compose up --build -d
docker compose exec api alembic upgrade head
```

- Backend: http://localhost/api (auto-reload enabled)
- Frontend: http://localhost (Vite HMR)
- API docs: http://localhost/api/docs
- Default admin: `admin@example.com` / `changeme123`

### Local (without Docker)

```bash
# Backend
cd backend
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### VS Code

```bash
code .hyphagraph.code-workspace
```

---

## Workflow Phases

### 1. Planning (required)

Before writing code:

- Provide a clear step-by-step plan (3-20 steps max)
- For each step: files impacted, rationale, test strategy
- **Wait for explicit human approval**

### 2. Execution (strict)

For each approved step:

- List files modified and why
- New feature -> **tests first** (TDD)
- Implement code
- Run tests and linters
- Report results clearly
- Commit work after each significant step

Rules:
- No stubs, no "we'll do it later", no unfinished paths
- If scope is too large: **stop and propose next steps**

### 3. Documentation

- Update [Roadmap](../product/ROADMAP.md) if status changes
- Update [Architecture](../architecture/ARCHITECTURE.md) if behavior changes

### 4. Audit (milestones)

At major milestones:
- Check for regressions
- Verify architectural consistency
- Suggest concrete improvements

---

## Commit Discipline

- **Commit after each significant step** (feature complete, tests passing)
- **Never accumulate dozens of uncommitted files**
- **Use descriptive commit messages** explaining what and why
- **Push regularly** to remote for backup

When to commit:
- Feature implementation complete with passing tests
- Refactoring or cleanup complete
- Bug fix complete and verified
- Before starting a new major task

---

## Running Tests

### Backend

```bash
cd backend && pytest
pytest --cov=app --cov-report=html --cov-report=term-missing  # coverage
pytest tests/test_auth_endpoints.py                            # specific file
pytest -m unit                                                 # by marker
```

### Frontend

```bash
cd frontend && npm test
npm run test:coverage
npm run test:ui
```

### E2E

```bash
docker compose -f docker-compose.e2e.yml up -d
cd e2e && npx playwright test
npx playwright test --ui
```

See [E2E Testing Guide](E2E_TESTING_GUIDE.md) for details.

---

## Creating Migrations

```bash
docker compose exec api alembic revision --autogenerate -m "Add new field"
docker compose exec api alembic upgrade head

# Reset database
docker compose exec api alembic downgrade base
docker compose exec api alembic upgrade head
```

---

## Before Committing Checklist

```bash
# Backend
docker compose exec api pytest --cov=app
docker compose exec api ruff check .
docker compose exec api ruff format .

# Frontend
cd frontend && npm test && npm run lint
```
