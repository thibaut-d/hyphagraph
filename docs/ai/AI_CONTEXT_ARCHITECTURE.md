# AI Context — Architecture (Layer 2)

Load this file when working on system-level design, cross-cutting concerns, or data model changes.

---

## System Overview

```
┌──────────────┐
│  Documents   │
│ (PDF, HTML)  │
└──────┬───────┘
       │
       ▼
┌────────────────────┐
│ Ingestion &        │
│ Claim Extraction   │◄── Human or LLM
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│     FastAPI        │
│  Domain Services   │◄── Frontend (React)
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   PostgreSQL       │
│ Source of Truth     │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Inference &       │
│  Aggregation       │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Explanation &      │
│ LLM Formatting     │
└────────────────────┘
```

---

## Component Responsibilities

### PostgreSQL

- Stores all authoritative data: sources, entities, relations, roles
- Strong transactional guarantees, explicit constraints
- No other system may introduce new semantics

### FastAPI

- Domain boundary and orchestrator
- Input validation (human and AI), invariant enforcement
- Does NOT perform inference implicitly or store syntheses as facts

### Domain Services

- All reasoning and aggregation logic
- Deterministic, side-effect free, recomputable, testable in isolation
- Never mutate base claims

### LLM Integration

- Stateless, non-authoritative workers
- Allowed: document parsing, claim extraction, terminology normalization, explanation formatting
- Disallowed: reasoning, consensus building, contradiction resolution, fact storage
- Never write directly to database

### React Frontend

- Presentation and editing layer
- Cannot override backend logic, hide uncertainty, or introduce implicit conclusions

---

## Data Flow Lifecycle

### Ingestion

1. Document is registered as a Source
2. Claims are extracted (human or LLM-assisted)
3. Claims validated against invariants
4. Claims stored as Relations with Roles (immutable)

### Inference

1. Query defines a scope (entity + optional filters)
2. Matching claims retrieved from Relations
3. Aggregation and inference rules applied (see COMPUTED_RELATIONS.md)
4. Results produced (optionally cached in `computed_relations` / `inference_cache`)

### Explanation

For any computed output, the system exposes:
- Contributing claims with source metadata
- Weights and rules applied
- Uncertainty, confidence breakdown, and contradictions

---

## Revision Architecture

All mutable domain objects use dual-table pattern:

| Base Table | Revision Table | Purpose |
|-----------|---------------|---------|
| `entities` | `entity_revisions` | Domain objects |
| `sources` | `source_revisions` | Documentary provenance |
| `relations` | `relation_revisions` | Claims (hyper-edges) |
| — | `relation_role_revisions` | Entity participation in relations |

Rules:
- Base table is immutable: `id`, `created_at`
- Revision table: versioned data with `is_current` flag
- Exactly one `is_current = true` per base record
- Role revisions tied to specific relation revisions (complete snapshots)
- `created_by_user_id` on all revisions (SET NULL on delete)

---

## Key Tables

### Core

- `entities`, `entity_revisions`, `entity_terms`
- `sources`, `source_revisions`
- `relations`, `relation_revisions`, `relation_role_revisions`

### Computed

- `computed_relations` — Cached inference metadata (scope_hash, model_version, uncertainty)
- `inference_cache` — Result cache

### Auth

- `users`, `refresh_tokens`, `audit_logs`

### Display

- `ui_categories` — Entity categorization for navigation
- `attributes` — Key-value metadata for entities/relations

---

## Extension Points

- **TypeDB** (planned): Secondary reasoning engine, operates on projections from PostgreSQL, disposable
- **Graph engines** (Neo4j etc.): Strictly derived views, no original semantics
- **Analytical engines** (DuckDB, Parquet): Offline analysis, do not replace PostgreSQL

---

## Critical Patterns

### Scope Filtering

Inference queries accept optional scope filters:
```json
{"population": "adults", "condition": "chronic"}
```
Scope hash (SHA256 of canonical sorted representation) used for cache keys.

### Confidence Model

- Exponential saturation model for confidence from multiple sources
- Disagreement metric (0-1) measuring conflict between supporting/contradicting evidence
- Coverage factor based on number of contributing sources

### Permission Model

Explicit functions, never decorators or RBAC frameworks:
```python
require_permission(can_create_entity(current_user), "Permission denied")
```
