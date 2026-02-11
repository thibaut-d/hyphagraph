# Contributing to HyphaGraph

---

## Prerequisites

- Docker + Docker Compose
- Node.js >= 20
- Python >= 3.12
- uv (Python package manager, recommended)

---

## Development Setup

```bash
# Clone and configure
git clone https://github.com/your-org/hyphagraph.git
cd hyphagraph
cp .env.sample .env

# Start services
docker compose up --build -d

# Initialize database
docker compose exec api alembic upgrade head
```

### Local development (without Docker)

```bash
# Backend
cd backend
uv pip install -e ".[dev]"
alembic upgrade head

# Frontend
cd ../frontend
npm install
npm run dev
```

The `backend/.env.test` file is tracked in git with safe test defaults.

---

## Code Standards

### General Principles

- **Explicit over clever** — readable, verbose code over abstractions
- **Boring over magical** — standard patterns, avoid framework magic
- **Auditable over convenient** — all business logic must be traceable

### Backend (Python / FastAPI)

- PEP 8, type hints everywhere, 100 char max line length
- Async/await for all database operations
- Pydantic models are the single source of truth for I/O
- Business logic lives in `services/`, never in API controllers
- Use `logging`, never `print`
- ORM only for DB access (no raw SQL from API layer)

### Frontend (React / TypeScript)

- No business logic duplication from backend
- Types must reflect backend contracts
- API calls go through `src/api/` abstraction layer

Full details: [Code Guide](docs/development/CODE_GUIDE.md)

---

## Testing

**TDD is mandatory** for all new features.

1. Write tests first (define expected behavior)
2. Implement minimum code to pass
3. Verify coverage >= 80%

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test

# E2E
cd e2e && npx playwright test
```

Full details: [E2E Testing Guide](docs/development/E2E_TESTING_GUIDE.md)

---

## Workflow

### 1. Plan (required before coding)

- Provide a step-by-step plan (3-20 steps)
- Specify files impacted, rationale, test strategy
- Wait for explicit approval

### 2. Execute

- New feature -> tests first
- No stubs, no placeholders, no "we'll do it later"
- Commit after each significant step
- Push regularly

### 3. Document

- Update [Roadmap](docs/product/ROADMAP.md) if status changes
- Update architecture docs if behavior or structure changes

Full details: [Dev Workflow](docs/development/DEV_WORKFLOW.md)

---

## Pull Request Guidelines

- Keep PRs focused on a single concern
- Include test coverage for all changes
- Ensure all tests pass before requesting review
- Use descriptive commit messages

---

## Architecture Rules (Non-Negotiable)

- **Never bypass layers** (e.g., frontend -> DB, raw SQL from UI)
- **Never store human-written syntheses** as facts
- **Never let LLM output be authoritative**
- **All conclusions must be explainable and recomputable**
- **Hidden certainty is considered a bug**

See: [Architecture](docs/architecture/ARCHITECTURE.md)
