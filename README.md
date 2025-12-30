# HyphaGraph

HyphaGraph is an experimental knowledge system based on hypergraphs, designed to transform documents into auditable, traceable, and computable knowledge instead of opaque summaries.

This repository is a proof of concept.


---

## What problem does it solve?

Most knowledge systems store information as documents or free-form summaries.
This makes knowledge:

- hard to audit,

- hard to update,

- hard to reason over,

- and prone to subjective interpretation.


HyphaGraph takes a different approach:
it extracts explicit factual statements (“claims”) from documents and represents them as a structured hypergraph, preserving sources, context, and contradictions.

### Typical use cases include:

- scientific literature analysis

- medical or technical knowledge curation

- comparison of contradictory sources

- explainable AI-assisted synthesis



---

## Project status

- ⚠️ Experimental / Proof of concept

- Not production-ready

- Data model and APIs are still evolving

- Intended for exploration, research, and prototyping

---

## Quick start

To get started with the project, read the following files in this order:

**GETTING_STARTED.md**
   Setup instructions and local development workflow

**PROJECT.md**
   Scientific motivation, conceptual foundations, and detailed rationale

**ARCHITECTURE.md**
   System architecture, component responsibilities, and design constraints

**DATABASE_SCHEMA.md**
   Canonical logical data model and schema definitions

**STRUCTURE.md**
   Project file structure and organization

**UX.md**
   Design brief and user experience principles

---

## Tech stack

- Backend: FastAPI, PostgreSQL, SQLAlchemy (async)

- Frontend: React

- Authentication: Custom JWT-based system (OAuth2 password flow)
  - **Note**: We do NOT use FastAPI Users or similar authentication frameworks
  - Rationale: FastAPI Users is in maintenance mode, and we prefer explicit, auditable authentication logic over framework magic
  - Simple User model with JWT access tokens
  - Explicit permission checks for authorization

- LLM (optional): used in a constrained way for claim extraction and structuring
(not for generating conclusions)


---

## Testing

### Unit & Integration Tests

**Backend (pytest)**:

```bash
cd backend
pytest
```

**Frontend (Vitest)**:

```bash
cd frontend
npm test
```

### E2E Tests (Playwright)

End-to-end tests cover complete user workflows across the entire stack.

**Quick Start**:

```bash
# Install dependencies
cd e2e
npm install

# Start E2E environment
cd ..
docker-compose -f docker-compose.e2e.yml up -d

# Run tests
cd e2e
npm test
```

**Test Coverage**:

- Authentication flows (login, registration, password reset)
- Entity CRUD operations
- Source CRUD operations
- Relation CRUD operations
- Inference viewing and filtering
- Explanation trace visualization

See `e2e/README.md` for detailed documentation.

---

## Contributing

Contributions are welcome.

Before contributing, please read the Markdown files containing essential documentation.
