# HyphaGraph TODO

**Last Updated**: 2026-03-21 (M3 LLM draft review; all audit findings resolved; test debt cleared)

---

## Current Status

| Area | Status | Details |
|------|--------|---------|
| **Backend tests** | ✅ 651/651 | All passing |
| **Frontend tests** | ✅ 613/613 | All passing (+16 BatchCreateRelationsView tests) |
| **E2E tests** | ✅ **166/167** | 1 skipped (mobile drawer `.skip`), 0 failed |
| **Technical debt** | ✅ None | All audit findings resolved, all test debt cleared |

### Completed Phases

**Phase 1 — Core Value**: Inference engine, explainability system, authentication, CRUD with revision tracking.

**Phase 2 — Enhanced Usability**: Filter drawers, UX-critical views (PropertyDetail, Evidence, Synthesis, Disagreements), unified search, i18n (EN/FR).

**Phase 3**: Entity terms & UI categories, **complete E2E test coverage**, async bcrypt, responsive design, admin panel, consensus level filtering, year range filtering, E2E database reset infrastructure.

**Phase 4**: Full-system audit (payload flows, inference engine, security, API boundaries), M3 LLM draft/review workflow (status field on revisions, review queue UI, confirm/discard API), complete test debt elimination (651 backend tests clean).

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
  - Created TextSpanValidator with exact and fuzzy matching
  - Integrated validation into extraction pipeline
  - Added 18 comprehensive validation tests (all passing)
- ✅ Implemented human-in-the-loop review system (COMPLETE - production ready)
  - **Visibility strategy: ALL extractions visible immediately, uncertain ones flagged**
  - Created StagedExtraction model and database migration
  - Built ExtractionReviewService with immediate materialization
  - Created review API endpoints (/api/extraction-review)
  - Auto-verification for high-confidence (score >= 0.9, no flags) → status="auto_verified"
  - Uncertain extractions visible with status="pending" → appear in review queue
  - Batch review operations for efficiency
  - Full audit trail with status transitions

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
- ✅ Human-in-the-loop review workflow (COMPLETE - production ready)
  - ✅ Database model (staged_extractions) and migration
  - ✅ Review service with immediate materialization
  - ✅ Full REST API (/api/extraction-review)
  - ✅ Auto-verification for high-confidence extractions
  - ✅ Visibility strategy: show all, flag uncertain
  - ✅ Integration with document extraction pipeline: stage_review_batch uses auto_materialize=False; save_extraction_to_graph calls reconcile_staged_extractions to link staged records to materialized IDs and mark APPROVED/REJECTED
  - ✅ Unit tests for review service (47 tests: auto-commit logic, relation/claim staging, materialization edge cases, filters, pagination, batch ops)
  - ✅ Frontend UI (review queue, badges, type/score/flag filters, batch approve/reject, View Entity/Relation links, 32 tests)
- ✅ Track LLM model version and provider (stored in staged_extractions)
- ✅ Claim extraction to Relations (auto-materialization): claims materialize as relations with kind=claim_type, notes=claim_text, scope=evidence_strength, participant roles

#### Batch Operations
- ✅ Bulk entity import (CSV, JSON) — preview + commit workflow, 500-row limit
  - ✅ `ImportService` with CSV/JSON parsing, duplicate detection, per-row status
  - ✅ `POST /api/import/entities/preview` and `POST /api/import/entities`
  - ✅ `ImportEntitiesView` — 3-stage UI (upload → preview table → done summary)
  - ✅ Import button wired into `EntitiesView` toolbar
  - ✅ i18n (EN + FR), 13 backend tests, 18 frontend tests
- ✅ Bulk source import (BibTeX, RIS, JSON) — 3-stage UI, 36 backend tests
- ✅ Batch relation creation — multi-row form, shared source selector, per-row results, 16 frontend tests
- ✅ Export functionality (JSON, CSV, RDF) — already complete
- ✅ Sources export button on SourcesView — `exportType="sources"` (JSON + CSV), dedicated backend endpoint
- ✅ Relations export button on SourcesView — `exportType="relations"` (JSON + CSV + RDF)

#### CI/CD Pipeline
- ✅ GitHub Actions for automated testing (backend + frontend + E2E)
- ✅ Coverage reporting

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
