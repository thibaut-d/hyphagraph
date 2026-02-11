# AI Context — Core (Layer 1)

This file should be loaded for EVERY task. It provides the essential context for working on HyphaGraph.

---

## Project Purpose

HyphaGraph is a hypergraph-based evidence knowledge system. It transforms document-based knowledge into computable, auditable, and explainable knowledge graphs.

**Core principle**: Knowledge is derived from documented statements, never written by humans or AI.

---

## Data Philosophy

- **Documents are sources**, not knowledge
- **Claims are stored**, not conclusions
- **Contradictions are preserved**, not resolved by opinion
- **Syntheses are computed**, never authored
- **AI is constrained** — extraction and formatting only

---

## Core Invariants (must always hold)

1. No human-written synthesis is stored as fact
2. No LLM-generated output is authoritative
3. Claims are immutable in meaning (revision architecture)
4. All conclusions must be explainable
5. Hidden certainty is considered a bug
6. If a result cannot be recomputed and explained, it does not belong in the system

---

## Architecture Summary

```
Documents → Ingestion/Extraction → FastAPI Services → PostgreSQL (source of truth)
                                                          ↓
                                                   Inference & Aggregation
                                                          ↓
                                                   Explanation & LLM Formatting → Frontend (React)
```

### Components

| Component | Role | Constraint |
|-----------|------|-----------|
| PostgreSQL | Source of truth | Only system introducing semantics |
| FastAPI | Domain boundary, orchestrator | No inference in controllers, no implicit synthesis |
| Domain Services | Reasoning, aggregation | Deterministic, side-effect free, recomputable |
| LLM Integration | Stateless worker | No reasoning, no consensus, no fact storage |
| React Frontend | Presentation, editing | Cannot override backend logic or hide uncertainty |

---

## Data Model (key concepts)

- **Entity** — Stable domain object (drug, disease, symptom). Context-free, reusable.
- **Source** — Documentary provenance (study, guideline). Every relation requires one.
- **Relation** — A claim (hyper-edge) connecting N entities with roles. What a source states.
- **Role** — How an entity participates in a relation (agent, target, population, dosage...).
- **Inference** — What the system computes from multiple claims. Never authored.

### Revision Architecture

All mutable entities use dual-table pattern:
- **Base table**: immutable (`id`, `created_at`)
- **Revision table**: versioned data (`is_current` flag)

Tables: `entities/entity_revisions`, `sources/source_revisions`, `relations/relation_revisions`, `relation_role_revisions`.

User provenance: `created_by_user_id` on all revisions (SET NULL on delete).

---

## Authentication Model

- Custom JWT-based (NOT FastAPI Users — it's in maintenance mode)
- OAuth2 password flow with access + refresh tokens
- Password hashing: passlib[bcrypt] (async via thread pool)
- Token signing: python-jose
- Minimal user model: id, email, hashed_password, is_active, is_superuser

### Authorization

Explicit Python functions, no RBAC frameworks:

```python
def can_create_entity(user: User) -> bool:
    return user.is_active

def can_edit_relation(user: User, relation: Relation) -> bool:
    return user.is_active and (user.is_superuser or relation.created_by_user_id == user.id)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy (async), Pydantic |
| Database | PostgreSQL |
| Frontend | React, TypeScript, Material UI, React Router v7 |
| Auth | passlib[bcrypt], python-jose, python-multipart |
| Testing | pytest + pytest-asyncio, Vitest + Testing Library, Playwright |
| i18n | i18next (EN + FR) |
| Infrastructure | Docker Compose |

---

## Testing Philosophy

- **TDD mandatory** — write tests first, implement to pass
- **Never claim "done" if tests fail**
- **Target >= 80% coverage**
- Backend: pytest with fixtures, AAA pattern (Arrange/Act/Assert)
- Frontend: Vitest + React Testing Library, mock API calls
- E2E: Playwright for critical user flows
- If testing is blocked, implementation is blocked

---

## Coding Principles

- **Explicit over clever** — readable, verbose code preferred
- **Boring over magical** — standard patterns, no framework magic
- **Auditable over convenient** — all logic traceable
- PEP 8, type hints everywhere, 100 char max line length
- Async/await for all DB operations
- Pydantic models are single source of truth for I/O
- Business logic in services, never in API controllers
- No cross-layer shortcuts (frontend → DB, raw SQL from UI)

---

## Naming Conventions

### Backend

- Models: `Entity`, `Source`, `Relation`, `EntityRevision`
- Services: `EntityService`, `InferenceService`, `ExplanationService`
- Repositories: `entity_repo`, `source_repo`
- Schemas: `EntityRead`, `EntityWrite`, `PaginatedResponse[T]`
- API routes: `/entities`, `/sources`, `/relations`, `/inferences`, `/explain`

### Frontend

- Views: `EntitiesView`, `EntityDetailView`, `ExplanationView`
- Components: `InferenceBlock`, `EvidenceTrace`, `FilterDrawer`
- API clients: `entities.ts`, `sources.ts`, `inferences.ts`
- Hooks: `useFilterDrawer`, `usePersistedFilters`, `useDebounce`
- Types: `EntityRead`, `SourceRead`, `RelationRead`, `RoleInference`

---

## Non-Negotiables

1. **Never bypass architectural layers**
2. **Never store opinions as facts**
3. **Never hide contradictions in the UI**
4. **Never let LLM output be authoritative**
5. **All conclusions must be explainable and recomputable**
6. **Tests must pass before claiming completion**
7. **No stubs, no placeholders, no "we'll do it later"**
8. **Commit after each significant step**

---

## Documentation Map

| File | Path | Purpose |
|------|------|---------|
| Architecture | `docs/architecture/ARCHITECTURE.md` | System design, invariants |
| Database Schema | `docs/architecture/DATABASE_SCHEMA.md` | Canonical data model |
| Computed Relations | `docs/architecture/COMPUTED_RELATIONS.md` | Inference math model |
| Code Guide | `docs/development/CODE_GUIDE.md` | Coding patterns |
| Dev Workflow | `docs/development/DEV_WORKFLOW.md` | Workflow, commits |
| E2E Testing | `docs/development/E2E_TESTING_GUIDE.md` | Playwright guide |
| UX Brief | `docs/product/UX.md` | Design principles |
| AI Agent Rules | `docs/product/VIBE.md` | AI agent instructions |
| Roadmap | `docs/product/ROADMAP.md` | Status, upcoming work |
