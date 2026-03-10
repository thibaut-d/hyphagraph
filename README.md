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

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Node.js >= 20
- Python >= 3.12

### Setup

```bash
git clone https://github.com/your-org/hyphagraph.git
cd hyphagraph
cp .env.sample .env

# Start services
docker compose up --build -d

# Initialize database (first run)
docker compose exec api alembic upgrade head
```

### Access

- **Frontend**: http://localhost
- **API docs**: http://localhost/api/docs
- **Default admin**: `admin@example.com` / `changeme123`

---

## Screenshots

<!-- TODO: Add screenshots of key views -->
<!-- Entity detail, inference display, explanation trace, disagreements view -->

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLAlchemy (async) |
| Database | PostgreSQL |
| Frontend | React, TypeScript, Material UI |
| Auth | Custom JWT (OAuth2 password flow) |
| Testing | pytest, Vitest, Playwright |
| Infrastructure | Docker Compose |

---

## Project Status

This repository is a **proof of concept** demonstrating conceptual soundness and architectural viability of hypergraph-based evidence reasoning.

See [Roadmap](docs/product/ROADMAP.md) for current status and planned work.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Project Overview](PROJECT_OVERVIEW.md) | Vision, philosophy, and scientific motivation |
| [Contributing](CONTRIBUTING.md) | Development setup, standards, and workflow |
| [Architecture](docs/architecture/ARCHITECTURE.md) | System architecture and invariants |
| [Database Schema](docs/architecture/DATABASE_SCHEMA.md) | Canonical data model |
| [Computed Relations](docs/architecture/COMPUTED_RELATIONS.md) | Inference mathematical model |
| [Code Guide](docs/development/CODE_GUIDE.md) | Coding conventions and patterns |
| [Dev Workflow](docs/development/DEV_WORKFLOW.md) | Development workflow and commit discipline |
| [E2E Testing](docs/development/E2E_TESTING_GUIDE.md) | Playwright E2E testing guide |
| [UX Design Brief](docs/product/UX.md) | UX principles and design constraints |
| [AI Agent Rules](docs/product/VIBE.md) | AI agent instructions and coding standards |
| [Roadmap](docs/product/ROADMAP.md) | Project status and upcoming work |

---

## License

See [LICENSE](LICENSE).
