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
git clone https://github.com/thibaut-d/hyphagraph.git
cd hyphagraph
cp .env.sample .env

# Start services (migrations run automatically on startup)
docker compose up --build -d
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

## Branching Strategy (GitHub Flow)

`main` is always green and releasable. All work happens on feature branches.

```
main          ─────●────────────────●──────── (protected, CI required)
                    ↑                ↑
feat/my-thing  ──●──●──●   feat/x  ──●──●
```

### Day-to-day workflow

```bash
# 1. Create a branch from main
git checkout -b feat/my-thing

# 2. Work, commit often
git add -p
git commit -m "feat: ..."

# 3. Push and open a PR
git push -u origin feat/my-thing
# → open PR on GitHub

# 4. CI must pass before merge (backend, frontend, E2E, migration-check)
# 5. Squash-merge or merge commit into main
# 6. Delete the branch
```

### Releases

Tags on `main` trigger the release workflow (Docker image build + GitHub Release):

```bash
git tag v1.2.0
git push origin v1.2.0
```

Pin to a specific version in `.env` via `HYPHAGRAPH_VERSION=1.2.0`.

### Branch protection

On GitHub: Settings → Branches → Add rule for `main`:
- Require status checks: `Backend tests`, `Frontend tests`, `Playwright E2E`
- Require branches to be up to date before merging

---

## Workflow

### 1. Plan (required before coding)

- Provide a step-by-step plan (3-20 steps)
- Specify files impacted, rationale, test strategy
- Wait for explicit approval

### 2. Execute

- New feature → tests first
- No stubs, no placeholders, no "we'll do it later"
- Commit after each significant step

### 3. Document

- Update [Roadmap](../product/ROADMAP.md) if status changes
- Update architecture docs if behavior or structure changes

Full details: [Dev Workflow](development/DEV_WORKFLOW.md)

---

## Pull Request Guidelines

- Keep PRs focused on a single concern
- Include test coverage for all changes
- All CI checks must pass before merge
- Use descriptive commit messages following the existing style

---

## Architecture Rules (Non-Negotiable)

- **Never bypass layers** (e.g., frontend -> DB, raw SQL from UI)
- **Never store human-written syntheses** as facts
- **Never let LLM output be authoritative**
- **All conclusions must be explainable and recomputable**
- **Hidden certainty is considered a bug**

See: [Architecture](docs/architecture/ARCHITECTURE.md)
