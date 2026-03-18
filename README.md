# HyphaGraph

**Hypergraph-based Evidence Knowledge System**

HyphaGraph transforms document-based knowledge into a computable, auditable, and explainable knowledge graph. It is designed for domains where information is heterogeneous, sometimes contradictory, and supported by sources of unequal quality.

> Knowledge should not be written. It should be derived from documented statements.

---

## Who is it for?

- **Researchers** working with large bodies of scientific literature
- **Physicians** navigating contradictory clinical evidence
- **Analysts** in any field requiring auditable, evidence-based reasoning

No prior knowledge of graphs, databases, or formal logic is required.

---

## Key Features

- **Document-grounded claims** — Knowledge is extracted from sources, never invented
- **Hypergraph structure** — Relations connect multiple entities with explicit roles
- **Contradiction handling** — Disagreements are preserved and surfaced, not hidden
- **Computed syntheses** — All conclusions are derived algorithmically, never authored
- **Full traceability** — Any conclusion reachable to its source in 2 clicks
- **Explainability** — Confidence breakdowns, contributing factors, and uncertainty always visible
- **Constrained AI** — LLMs assist with extraction and formatting only, never as authority

---

## Local Development

### Prerequisites

- Docker + Docker Compose
- Node.js >= 20 (for frontend dev outside Docker)
- Python >= 3.12 + [uv](https://docs.astral.sh/uv/) (for backend dev outside Docker)

### Start

```bash
git clone https://github.com/thibaut-d/hyphagraph.git
cd hyphagraph
cp .env.sample .env

# Start the full stack (API, DB, frontend, Caddy)
docker compose up -d
# or: make up
```

The API container applies migrations automatically on startup — no manual `alembic upgrade head` needed.

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| API docs | http://localhost/api/docs |
| Default admin | `admin@example.com` / `changeme123` |

### Common commands

```bash
make logs          # tail all service logs
make logs-api      # tail API logs only
make api-shell     # shell inside the API container
make db-shell      # psql inside the database container
make db-dump       # dump database to ./backups/
make down          # stop the stack
make clean         # stop + remove volumes (data loss)
```

Run `make help` for the full list.

---

## Running Tests

### Backend (pytest)

```bash
# Inside the running container
make api-tests

# Or directly with uv (outside Docker, from backend/)
cd backend
uv run pytest
uv run pytest -q --tb=short          # quiet output
uv run pytest tests/test_foo.py -x   # stop on first failure
```

### Frontend (Vitest)

```bash
cd frontend
npm test             # interactive watch mode
npm test -- --run    # single run (CI mode)
```

### End-to-end (Playwright)

See [E2E Testing Guide](docs/development/E2E_TESTING_GUIDE.md).

---

## Production Self-Hosting

HyphaGraph is distributed as versioned Docker images via GitHub Container Registry. Each instance you operate (one per site) pulls those images and manages its own database.

### Step 1 — Create your environment file

```bash
cp .env.prod.template .env
```

Edit `.env` and replace every `change-me-*` placeholder:

| Variable | What to set |
|----------|-------------|
| `POSTGRES_PASSWORD` | Strong random password |
| `SECRET_KEY` | Long random string |
| `JWT_SECRET_KEY` | Long random string (different from above) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Initial admin credentials |
| `FRONTEND_URL` | Your public URL, e.g. `https://yoursite.com` |
| `HYPHAGRAPH_VERSION` | Pin to a release tag, e.g. `1.2.0` |

### Step 2 — Configure your domain

Edit `deploy/caddy/Caddyfile.self-host` — replace `your-domain.com` with your actual domain:

```
yoursite.com {
    handle /api/* {
        reverse_proxy api:8000
    }
    handle {
        reverse_proxy web:80
    }
}
```

Caddy obtains and renews TLS certificates from Let's Encrypt automatically. Ports 80 and 443 must be reachable from the internet.

### Step 3 — Start

```bash
docker compose -f docker-compose.self-host.yml up -d
```

The API container runs `alembic upgrade head` before starting — migrations are applied automatically on every start (idempotent).

### Updating

```bash
# Pull new images and restart
docker compose -f docker-compose.self-host.yml pull
docker compose -f docker-compose.self-host.yml up -d
```

To pin a specific version, set `HYPHAGRAPH_VERSION=1.2.0` in `.env`.

### Logs

```bash
docker compose -f docker-compose.self-host.yml logs -f
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLAlchemy (async) |
| Database | PostgreSQL |
| Frontend | React, TypeScript, Material UI |
| Auth | Custom JWT (OAuth2 password flow) |
| Testing | pytest, Vitest, Playwright |
| Infrastructure | Docker Compose, Caddy |

---

## Documentation

| Document | Description |
|----------|-------------|
| [Project Overview](docs/PROJECT_OVERVIEW.md) | Vision, philosophy, and scientific motivation |
| [Contributing](docs/CONTRIBUTING.md) | Development setup, standards, and workflow |
| [Architecture](docs/architecture/ARCHITECTURE.md) | System architecture and invariants |
| [Database Schema](docs/architecture/DATABASE_SCHEMA.md) | Canonical data model |
| [Computed Relations](docs/architecture/COMPUTED_RELATIONS.md) | Inference mathematical model |
| [Code Guide](docs/development/CODE_GUIDE.md) | Coding conventions and patterns |
| [Dev Workflow](docs/development/DEV_WORKFLOW.md) | Development workflow and commit discipline |
| [E2E Testing](docs/development/E2E_TESTING_GUIDE.md) | Playwright E2E testing guide |
| [UX Design Brief](docs/product/UX.md) | UX principles and design constraints |
| [AI Agent Guide](AGENTS.md) | Canonical AI-agent entrypoint and workflow |
| [Roadmap](docs/product/ROADMAP.md) | Project status and upcoming work |

---

## License

See [LICENSE](LICENSE).
