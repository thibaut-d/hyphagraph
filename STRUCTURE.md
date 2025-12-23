hypergraph/
│
├── README.md                    # Vision, scientific rationale, overview
├── CODE_GUIDE.md                # How to write code (developer rules)
├── ARCHITECTURE.md              # System architecture & invariants
├── DATABASE_SCHEMA.md           # Logical data model (human-readable)
│
├── backend/
│   ├── README.md                # Backend-specific setup & conventions
│   ├── pyproject.toml           # uv config
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── config.py            # Settings, env vars, feature flags
│   │   │
│   │   ├── api/                 # HTTP layer (no domain logic)
│   │   │   ├── __init__.py
│   │   │   ├── documents.py     # CRUD for Document
│   │   │   ├── concepts.py      # CRUD for Concept
│   │   │   ├── assertions.py    # CRUD for Assertion & AssertionConcept
│   │   │   ├── derived_claims.py# Read-only access to computed claims
│   │   │   └── explain.py       # Explainability endpoints
│   │   │
│   │   ├── schemas/             # Pydantic models (I/O validation)
│   │   │   ├── document.py
│   │   │   ├── concept.py
│   │   │   ├── assertion.py
│   │   │   ├── derived_claim.py
│   │   │   └── explanation.py
│   │   │
│   │   ├── models/              # ORM models (no logic)
│   │   │   ├── document.py
│   │   │   ├── concept.py
│   │   │   ├── assertion.py
│   │   │   ├── assertion_concept.py
│   │   │   └── derived_claim.py
│   │   │
│   │   ├── repositories/        # DB access only
│   │   │   ├── document_repo.py
│   │   │   ├── concept_repo.py
│   │   │   ├── assertion_repo.py
│   │   │   └── derived_claim_repo.py
│   │   │
│   │   ├── services/            # Domain logic (pure, deterministic)
│   │   │   ├── assertion_service.py
│   │   │   ├── aggregation_service.py
│   │   │   ├── scoring_service.py
│   │   │   ├── explain_service.py
│   │   │   └── validation_service.py
│   │   │
│   │   ├── llm/                 # LLM integration (stateless workers)
│   │   │   ├── base.py           # Abstract interface
│   │   │   ├── openai.py         # ChatGPT adapter
│   │   │   ├── gemini.py         # Gemini adapter
│   │   │   ├── mistral.py        # Mistral adapter
│   │   │   └── prompts/          # Prompt templates (versioned)
│   │   │       ├── extract_assertions.md
│   │   │       └── explain_claim.md
│   │   │
│   │   ├── utils/               # Shared helpers (pure)
│   │   │   ├── hashing.py        # scope_hash logic
│   │   │   ├── enums.py
│   │   │   └── logging.py
│   │   │
│   │   └── tests/
│   │       ├── test_invariants.py
│   │       ├── test_assertions.py
│   │       ├── test_aggregation.py
│   │       └── test_explainability.py
│   │
│   └── alembic/                 # DB migrations
│       └── versions/
│
├── frontend/
│   ├── README.md                # Frontend architecture & constraints
│   ├── package.json
│   ├── src/
│   │   ├── app/                 # App shell, routing
│   │   ├── api/                 # Typed API clients
│   │   ├── components/          # UI components (pure)
│   │   ├── views/               # Pages (Document, Assertion, Claim)
│   │   ├── state/               # State management
│   │   ├── hooks/               # Data fetching hooks
│   │   └── types/               # Shared TypeScript types
│
├── docs/
│   ├── SCORING.md                # Evidence weighting & aggregation rules
│   ├── DATA_QUALITY.md           # Validation & review rules
│   ├── API_CONTRACT.md           # Public API specification
│   └── GLOSSARY.md               # Domain-agnostic terminology
│
├── scripts/
│   ├── ingest_documents.py       # Batch document ingestion
│   ├── run_extraction.py         # LLM-assisted assertion extraction
│   └── recompute_claims.py       # Deterministic recomputation
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── LICENSE
