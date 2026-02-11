# HyphaGraph TODO

**Last Updated**: 2026-02-11

---

## Current Status

| Area | Status | Details |
|------|--------|---------|
| **Backend tests** | 253/253 | All passing |
| **Frontend tests** | 420/420 | All passing |
| **E2E tests** | 49/49 | All passing (Playwright) |
| **Technical debt** | Zero | All known issues resolved |

### Completed Phases

**Phase 1 — Core Value**: Inference engine, explainability system, authentication, CRUD with revision tracking.

**Phase 2 — Enhanced Usability**: Filter drawers, UX-critical views (PropertyDetail, Evidence, Synthesis, Disagreements), unified search, i18n (EN/FR).

**Phase 3 (partial)**: Entity terms & UI categories, E2E tests, async bcrypt, responsive design, admin panel.

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
