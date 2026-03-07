# HyphaGraph TODO

**Last Updated**: 2026-03-07 (Session 4)

---

## Current Status

| Area | Status | Details |
|------|--------|---------|
| **Backend tests** | ✅ 374/374 | All passing (+18 validation tests) |
| **Frontend tests** | ✅ 421/421 | All passing |
| **E2E tests** | ✅ **72/72** | **🎉 All passing!** |
| **Technical debt** | ✅ Minimal | All test issues resolved |

### Completed Phases

**Phase 1 — Core Value**: Inference engine, explainability system, authentication, CRUD with revision tracking.

**Phase 2 — Enhanced Usability**: Filter drawers, UX-critical views (PropertyDetail, Evidence, Synthesis, Disagreements), unified search, i18n (EN/FR).

**Phase 3**: Entity terms & UI categories, **complete E2E test coverage**, async bcrypt, responsive design, admin panel, consensus level filtering, year range filtering, E2E database reset infrastructure.

### E2E Test Status (2026-03-07) - ✅ COMPLETE

**Final Status**: **72/72 passing (100%)** - All tests fixed and passing!

**Fixes Applied Across Three Sessions**:

**Session 1**:
- ✅ Fixed source form summary fields visibility (6 tests)
- ✅ Updated frontend RoleInference schema to match backend (11 tests)

**Session 2**:
- ✅ Fixed test selectors for UI text changes (10 tests)
- ✅ Fixed validation test logic (1 test)

**Session 3** (2026-03-07 morning):
- ✅ Fixed 2 skipped EvidenceView tests (timing/mocking issues)
- ✅ Implemented consensus level filtering with SQL subquery
- ✅ Implemented year range calculation for entity filters
- ✅ Created E2E database reset infrastructure (test-only API endpoint)

**Session 4** (2026-03-07 afternoon):
- ✅ Implemented hallucination validation layer for LLM extractions
- ✅ Created TextSpanValidator with exact and fuzzy matching
- ✅ Integrated validation into extraction pipeline
- ✅ Added 18 comprehensive validation tests (all passing)

**All Test Categories Passing** (72 tests):
- ✅ Auth flows (15/15): Login, logout, registration, password reset
- ✅ Entity CRUD (9/9): Create, read, update, delete, search, filters
- ✅ Explanation traces (7/7): All explanation features working
- ✅ Inference viewing (6/6): Navigation, filtering, detail view, scores
- ✅ Relation CRUD (5/5): Create, edit, delete, validation
- ✅ Source CRUD (6/6): Create, view, edit, delete, search, validation
- ✅ Document upload (5/5): Upload flow, extraction, components, error handling
- ✅ URL extraction (7/7): Dialog, validation, PubMed/web detection, workflow
- ✅ PubMed import (9/9): Search, selection, import, metadata display

See `E2E_TEST_FIXES_SUMMARY.md` and `E2E_TEST_ANALYSIS.md` for detailed technical analysis.

---

## Remaining Work

### High Priority

#### LLM Integration
- ✅ Document ingestion pipeline with LLM-assisted extraction
- ✅ Entity linking / terminology normalization
- ✅ Hallucination validation layer (text span verification)
- Human-in-the-loop review workflow (staging/approval system)
- Track LLM model version and provider in metadata
- Claim extraction to Relations (auto-materialization)

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
