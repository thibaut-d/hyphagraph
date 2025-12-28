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
│   │   ├── database.py          # Database session and engine setup
│   │   ├── startup.py           # Startup tasks (admin user, system source)
│   │
│   │   ├── api/                 # HTTP layer (no domain logic)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # Authentication endpoints (register, login, etc.)
│   │   │   ├── users.py         # User management endpoints
│   │   │   ├── sources.py       # CRUD for Source
│   │   │   ├── entities.py      # CRUD for Entity
│   │   │   ├── relations.py     # CRUD for Relation + Roles
│   │   │   ├── inferences.py    # Read-only access to computed results
│   │   │   └── explanations.py  # Explainability endpoints
│   │
│   │   ├── schemas/             # Pydantic I/O models
│   │   │   ├── auth.py          # Login, register, token responses
│   │   │   ├── source.py        # SourceRead, SourceWrite
│   │   │   ├── entity.py        # EntityRead, EntityWrite
│   │   │   ├── relation.py      # RelationRead, RelationWrite
│   │   │   ├── inference.py     # InferenceRead
│   │   │   ├── explanation.py   # ExplanationRead
│   │   │   ├── filters.py       # SourceFilters, EntityFilters
│   │   │   └── pagination.py    # PaginatedResponse[T]
│   │   │
│   │   ├── models/              # ORM models (no logic)
│   │   │   ├── base.py          # Base class with UUIDMixin
│   │   │   ├── user.py          # User model (custom JWT, NOT FastAPI Users)
│   │   │   ├── refresh_token.py # Refresh token storage
│   │   │   ├── audit_log.py     # Security event logging
│   │   │   ├── source.py        # Source (base, immutable)
│   │   │   ├── source_revision.py  # SourceRevision (versioned data)
│   │   │   ├── entity.py        # Entity (base, immutable)
│   │   │   ├── entity_revision.py  # EntityRevision (versioned data)
│   │   │   ├── entity_term.py   # Entity terms/aliases
│   │   │   ├── relation.py      # Relation (base, immutable)
│   │   │   ├── relation_revision.py  # RelationRevision (versioned data)
│   │   │   ├── relation_role_revision.py  # Roles in relations
│   │   │   ├── computed_relation.py  # Computed inference metadata
│   │   │   └── ui_category.py   # UI categorization for entities
│   │   │
│   │   ├── repositories/        # DB access only
│   │   │   ├── user_repo.py
│   │   │   ├── source_repo.py
│   │   │   ├── entity_repo.py
│   │   │   ├── relation_repo.py
│   │   │   ├── inference_repo.py
│   │   │   └── computed_relation_repo.py
│   │   │
│   │   ├── services/            # Domain logic (pure, deterministic)
│   │   │   ├── user_service.py      # User management, auth flows
│   │   │   ├── source_service.py
│   │   │   ├── entity_service.py
│   │   │   ├── relation_service.py
│   │   │   ├── inference_service.py
│   │   │   ├── explanation_service.py
│   │   │   └── validation_service.py
│   │   │
│   │   ├── dependencies/        # FastAPI dependencies
│   │   │   └── auth.py          # get_current_user, get_current_active_superuser
│   │   │
│   │   ├── mappers/             # ORM ↔ Pydantic conversion
│   │   │   ├── source_mapper.py
│   │   │   ├── entity_mapper.py
│   │   │   ├── relation_mapper.py
│   │   │   └── inference_mapper.py
│   │   │
│   │   ├── utils/               # Shared pure helpers
│   │   │   ├── auth.py          # JWT & bcrypt utilities (custom, NOT FastAPI Users)
│   │   │   ├── permissions.py   # Explicit permission functions
│   │   │   ├── hashing.py       # scope_hash / fingerprint logic
│   │   │   ├── revision_helpers.py  # Revision pattern helpers
│   │   │   ├── audit.py         # Audit logging utilities
│   │   │   ├── email.py         # Email verification & password reset
│   │   │   └── rate_limit.py    # Rate limiting utilities
│   │   │
│   │   └── llm/                 # LLM integration (NOT YET IMPLEMENTED)
│   │       ├── base.py          # Abstract interface (planned)
│   │       ├── openai.py        # (planned)
│   │       ├── gemini.py        # (planned)
│   │       └── mistral.py       # (planned)
│   │
│   ├── tests/                   # Test suite (infrastructure ready)
│   │   ├── conftest.py          # Pytest fixtures
│   │   ├── test_auth_utils.py   # Authentication utilities tests
│   │   ├── test_user_service.py # User service tests
│   │   └── test_auth_endpoints.py  # Auth API integration tests
│   │
│   └── alembic/
│       └── versions/
│
├── frontend/
│   ├── README.md                # Frontend constraints & data rules
│   ├── package.json
│   ├── vitest.config.ts         # Vitest test configuration
│   ├── src/
│   │   ├── app/                 # App shell, routing
│   │   │   ├── App.tsx          # App root with AuthProvider and Router
│   │   │   └── routes.tsx       # Route definitions (React Router v7)
│   │   │
│   │   ├── api/                 # Typed API clients
│   │   │   ├── client.tsx       # Base HTTP client with token refresh
│   │   │   ├── auth.ts          # Authentication API (login, register, etc.)
│   │   │   ├── entities.ts      # Entity CRUD with pagination
│   │   │   ├── sources.ts       # Source CRUD with filtering
│   │   │   ├── relations.ts     # Relation and Role management
│   │   │   ├── inferences.ts    # Inference endpoints
│   │   │   └── explanations.ts  # Explainability endpoints
│   │   │
│   │   ├── auth/                # Authentication context (NOT state/)
│   │   │   ├── AuthContext.tsx  # React Context for auth state
│   │   │   └── useAuth.ts       # Custom hook for auth
│   │   │
│   │   ├── components/          # Pure UI components
│   │   │   ├── Layout.tsx       # App shell with navigation
│   │   │   ├── ProtectedRoute.tsx  # Auth-protected route wrapper
│   │   │   ├── UserAvatar.tsx
│   │   │   ├── ProfileMenu.tsx
│   │   │   ├── EvidenceTrace.tsx   # Inference visualization
│   │   │   ├── InferenceBlock.tsx
│   │   │   ├── ScrollToTop.tsx
│   │   │   └── filters/         # Filter components
│   │   │       ├── FilterDrawer.tsx
│   │   │       ├── FilterDrawerHeader.tsx
│   │   │       ├── FilterDrawerContent.tsx
│   │   │       ├── CheckboxFilter.tsx
│   │   │       ├── RangeFilter.tsx
│   │   │       ├── YearRangeFilter.tsx
│   │   │       └── SearchFilter.tsx
│   │   │
│   │   ├── views/               # Pages (20+ views)
│   │   │   ├── HomeView.tsx
│   │   │   ├── EntitiesView.tsx, EntityDetailView.tsx
│   │   │   ├── CreateEntityView.tsx, EditEntityView.tsx
│   │   │   ├── SourcesView.tsx, SourceDetailView.tsx
│   │   │   ├── CreateSourceView.tsx, EditSourceView.tsx
│   │   │   ├── RelationsView.tsx
│   │   │   ├── CreateRelationView.tsx, EditRelationView.tsx
│   │   │   ├── InferencesView.tsx
│   │   │   ├── ExplanationView.tsx
│   │   │   ├── SearchView.tsx
│   │   │   ├── AccountView.tsx  # Login/Register
│   │   │   ├── ProfileView.tsx
│   │   │   ├── ChangePasswordView.tsx
│   │   │   ├── SettingsView.tsx
│   │   │   ├── RequestPasswordResetView.tsx
│   │   │   ├── ResetPasswordView.tsx
│   │   │   ├── VerifyEmailView.tsx
│   │   │   └── ResendVerificationView.tsx
│   │   │
│   │   ├── hooks/               # Data fetching hooks
│   │   │   ├── useFilterDrawer.ts      # Filter drawer UI state
│   │   │   ├── usePersistedFilters.ts  # Filter state with localStorage
│   │   │   ├── useDebounce.ts          # Debounce hook
│   │   │   └── useInfiniteScroll.ts    # Pagination helper
│   │   │
│   │   ├── types/               # Shared TypeScript types
│   │   │   ├── entity.ts        # EntityRead, EntityWrite
│   │   │   ├── relation.ts      # RelationRead, RoleRead
│   │   │   ├── source.ts        # SourceRead, SourceWrite
│   │   │   ├── inference.ts     # InferenceRead, RoleInference
│   │   │   └── filters.ts       # FilterConfig, FilterState
│   │   │
│   │   ├── i18n/                # Internationalization (i18next)
│   │   │   ├── config.ts        # i18next configuration
│   │   │   ├── en.json          # English translations
│   │   │   └── fr.json          # French translations
│   │   │
│   │   ├── utils/               # Utility functions
│   │   │   └── ...
│   │   │
│   │   └── test/                # Test setup
│   │       └── setup.ts         # Vitest setup with jest-dom
│   │
│   └── tests/                   # Test files (23+ test files)
│       └── __tests__/           # Organized by feature
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

---

## Architecture Notes

### Backend

**Authentication:** Custom JWT implementation (NOT FastAPI Users)
- `app/utils/auth.py` - JWT & bcrypt utilities
- `app/dependencies/auth.py` - FastAPI dependencies
- `app/utils/permissions.py` - Explicit permission functions
- See `AUTHENTICATION.md` for complete details

**Dual-Table Revision Pattern:**
- Base tables (Source, Entity, Relation) are immutable
- Revision tables hold all versioned data with `is_current` flag
- Full audit trail of all changes

**LLM Integration:** Architecture designed but not yet implemented

**Tests:** Infrastructure ready (pytest, fixtures), test files need to be written

### Frontend

**State Management:** Distributed approach (NOT centralized store)
- Authentication state → `src/auth/AuthContext.tsx` (React Context)
- Filter state → `src/hooks/usePersistedFilters.ts` (localStorage + hooks)
- UI state → Component-level hooks

**Why no `src/state/` directory?**
The application uses React Context API and custom hooks for state management instead of Redux/Zustand. This lightweight approach is appropriate for the current scope.

**Internationalization:** Full i18next support with English and French translations

**Testing:** Vitest + Testing Library configured with 23+ test files

