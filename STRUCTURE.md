# Project's structure

```
hyphagraph/
│
├── README.md                    # Vision, motivation, overview
├── CODE_CONVENTIONS.md          # Contributor rules (short, strict)
├── ARCHITECTURE.md              # System architecture & invariants
├── DATABASE_SCHEMA.md           # Logical data model (human-readable)
│
├── backend/
│   ├── README.md                # Backend setup & local dev
│   ├── pyproject.toml           # uv / deps
│   │
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── config.py            # Settings, env vars, feature flags
│   │
│   │   ├── api/                 # HTTP layer (no domain logic)
│   │   │   ├── __init__.py
│   │   │   ├── sources.py       # CRUD for Source
│   │   │   ├── entities.py      # CRUD for Entity
│   │   │   ├── relations.py     # CRUD for Relation + Roles
│   │   │   ├── inferences.py    # Read-only access to computed results
│   │   │   └── explain.py       # Explainability endpoints
│   │   │
│   │   ├── schemas/             # Pydantic I/O models
│   │   │   ├── source.py
│   │   │   ├── entity.py
│   │   │   ├── relation.py
│   │   │   ├── role.py
│   │   │   ├── inference.py
│   │   │   └── explanation.py
│   │   │
│   │   ├── models/              # ORM models (no logic)
│   │   │   ├── source.py
│   │   │   ├── entity.py
│   │   │   ├── relation.py
│   │   │   ├── role.py
│   │   │   └── inference_cache.py
│   │   │
│   │   ├── repositories/        # DB access only
│   │   │   ├── source_repo.py
│   │   │   ├── entity_repo.py
│   │   │   ├── relation_repo.py
│   │   │   └── inference_repo.py
│   │   │
│   │   ├── services/            # Domain logic (pure, deterministic)
│   │   │   ├── relation_service.py
│   │   │   ├── inference_service.py
│   │   │   ├── scoring_service.py
│   │   │   ├── explain_service.py
│   │   │   └── validation_service.py
│   │   │
│   │   ├── llm/                 # LLM integration (stateless)
│   │   │   ├── base.py           # Abstract interface
│   │   │   ├── openai.py
│   │   │   ├── gemini.py
│   │   │   ├── mistral.py
│   │   │   └── prompts/
│   │   │       ├── extract_relations.md
│   │   │       └── explain_inference.md
│   │   │
│   │   ├── utils/               # Shared pure helpers
│   │   │   ├── hashing.py        # scope_hash / fingerprint logic
│   │   │   ├── enums.py
│   │   │   └── logging.py
│   │   │
│   │   └── tests/
│   │       ├── test_invariants.py
│   │       ├── test_relations.py
│   │       ├── test_inference.py
│   │       └── test_explainability.py
│   │
│   └── alembic/
│       └── versions/
│
├── frontend/
│   ├── README.md                # Frontend constraints & data rules
│   ├── package.json
│   ├── src/
│   │   ├── app/                 # App shell, routing
│   │   ├── api/                 # Typed API clients
│   │   ├── components/          # Pure UI components
│   │   ├── views/               # Pages (Source, Relation, Inference)
│   │   ├── state/               # State management
│   │   ├── hooks/               # Data fetching hooks
│   │   └── types/               # Shared TS types (Entity, Relation…)
│
├── docs/
│   ├── SCORING.md                # Evidence weighting & aggregation
│   ├── DATA_QUALITY.md           # Validation & review rules
│   ├── API_CONTRACT.md           # Public API specification
│   └── GLOSSARY.md               # Canonical terminology
│
├── scripts/
│   ├── ingest_sources.py         # Batch document ingestion
│   ├── extract_relations.py      # LLM-assisted extraction
│   └── recompute_inferences.py  # Deterministic recomputation
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── LICENSE
```

