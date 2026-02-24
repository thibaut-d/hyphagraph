# HyphaGraph TODO

**Last Updated**: 2026-02-24

---

## Current Status

| Area | Status | Details |
|------|--------|---------|
| **Backend tests** | 349/349 | All passing |
| **Frontend tests** | 420/420 | All passing |
| **E2E tests** | ~63/72 | 44 passing (fixes in progress, see below) |
| **Technical debt** | Minimal | E2E test fixes needed |

### Completed Phases

**Phase 1 — Core Value**: Inference engine, explainability system, authentication, CRUD with revision tracking.

**Phase 2 — Enhanced Usability**: Filter drawers, UX-critical views (PropertyDetail, Evidence, Synthesis, Disagreements), unified search, i18n (EN/FR).

**Phase 3 (partial)**: Entity terms & UI categories, E2E tests, async bcrypt, responsive design, admin panel.

### E2E Test Status (2026-02-24)

**Current**: 44/72 passing (61%), 27 failing, 1 flaky

**Recent Fixes Applied**:
- ✅ Fixed source form summary fields visibility (fixes ~20 tests)
- ✅ Updated frontend RoleInference schema to match backend (fixes ~9 tests)
- 🔄 Awaiting rebuild and re-test to verify fixes

**Passing Areas** (44 tests):
- Auth flows (15/15): Login, logout, registration, password reset
- Entity CRUD (9/9): Create, read, update, delete, search, filters
- Explanation traces (5/7): Most explanation features working
- Inference viewing (4/6): Navigation, filtering, detail view
- PubMed import (8/9): Bulk search, selection, import

**Failing Areas** (27 tests - expecting ~90% to pass after fixes):
- Source CRUD (6 tests) - **Fix applied**: summary fields now visible
- Relation CRUD (5 tests) - **Fix applied**: schema compatibility fixed
- Document upload (5 tests) - **Fix applied**: depends on source form fix
- URL extraction (7 tests) - **Fix applied**: depends on source form fix
- Partial failures (4 tests) - **Fix applied**: schema compatibility fixed

---

## Remaining Work

### High Priority

#### LLM Integration
- Document ingestion pipeline with LLM-assisted extraction
- Claim extraction service (documents -> structured relations)
- Entity linking / terminology normalization
- Human-in-the-loop review workflow
- Validation layer to prevent hallucinations
- Track LLM model version and provider in metadata

#### Batch Operations
- Bulk entity import (CSV, JSON)
- Bulk source import (BibTeX, RIS, JSON)
- Batch relation creation
- Export functionality (JSON, CSV, RDF)
- Import validation, error reporting, and preview

#### CI/CD Pipeline
- GitHub Actions for automated testing (backend + frontend + E2E)
- Coverage reporting

---

### Low Priority (Post-v1.0)

- **Graph visualization** — Explicitly NOT MVP. Text-based traceability achieves the UX goal.
- **TypeDB integration** — Optional reasoning engine for advanced logic
- **Advanced auth** — 2FA (TOTP), OAuth providers (Google, GitHub)
- **Real-time collaboration** — WebSocket/SSE for live updates
- **Multi-tenancy** — Organization model, RBAC

---

## Design Principles (Non-Negotiable)

1. **Scientific honesty** — Contradictions never hidden
2. **Traceability** — Every conclusion links to sources (2 clicks max)
3. **Explainability** — Syntheses are computed, not authored
4. **Progressive disclosure** — Complexity revealed gradually
5. **AI constraint** — LLMs are non-authoritative workers only

---

## Documentation Map

See [README.md](../../README.md) for the full documentation index.
