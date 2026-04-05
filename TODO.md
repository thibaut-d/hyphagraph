# Current Work

**Last updated**: 2026-04-05

## Open Findings

_Items verified correct are marked `[x]`. Items with confirmed defects remain `[ ]` with the defect described. New defects found during review are prefixed **[NEW]**._

---

### Authentication & Authorization

- [x] Refresh token rotation — old token invalidated, replay rejected, test present. (`tokens.py`)
- [x] Token version column — `token_version` in JWT, stale tokens rejected, incremented on state changes, migration 012 correct. (`user.py`, `dependencies/auth.py`)
- [x] Access token in-memory — no localStorage, cross-tab restoration via refresh cookie on mount. (`authStorage.ts`, `AuthContext.tsx`)
- [x] Superuser guards — `get_current_active_superuser` on all extraction review, revision review, review queue, and admin endpoints. Frontend `SuperuserRoute` in place.
- [x] Confirmed-only read isolation — entity/source/relation list+get, entity linking all filter `status == "confirmed"`. `test_draft_isolation.py` present.

---

### Search

- [x] Auth boundary — both `/search` and `/search/suggestions` require `get_current_user`; suggestions filter confirmed. (`search.py`)
- [x] Confirmed-only sub-searchers — entity, source, relation all filter `status == "confirmed"`.
- [x] Cross-type pagination — single slice after merge, not per-type. (`common.py`)
- [x] Relation search N+1 — role revisions batch-loaded in one query after collecting revision IDs. (`relation_search.py:56-63`)
- [ ] **[NEW-SEARCH-M1]** `backend/alembic/versions/` — `pg_trgm` GIN indexes were claimed (DF-SCH-m1) but are absent from all migrations. Search uses `.contains()` which requires sequential scans. Add a migration creating GIN trigram indexes on all searched text columns (slug, title, summary, authors, origin, term).

---

### Inference & Computed Relations

- [ ] **[NEW-INF-C1]** `backend/app/services/explanation_read_models.py:23-26` — `build_contradiction_detail()` accumulates `supporting_sources` and `contradicting_sources` correctly in lines 14–21, then discards them by hardcoding empty lists at lines 23–26. The returned `ContradictionDetail` always has `supporting_sources=[]` and `contradicting_sources=[]`. Fix: pass the accumulated lists into the constructor.
- [ ] **[NEW-INF-M1]** `backend/app/models/relation_role_revision.py` — per-role `confidence` column is absent. The claim (DF-INF-M1) stated both `disagreement` and `confidence` would be stored per-role; only `disagreement` is present. Confidence is computed at `RoleInference` level but never persisted to the revision row. Clarify whether the column is intentionally deferred or needs to be added.
- [x] Per-role disagreement stored in `RelationRoleRevision.disagreement`; populated during inference computation, not just as a global average. (`read_models.py:299`)
- [x] Inference cache invalidated on source `trust_level` change — entities linked via confirmed relations are found and their cache entries deleted. (`source_service.py:306-327`)
- [x] Canonical relation predicate used consistently across derived-properties, source-role classification, entity-query-builder, and export. (`query_predicates.py`)

---

### Extraction Pipeline

- [ ] **[NEW-EXT-M1]** `backend/app/api/document_extraction_routes/document.py:114-211` — the document storage/extraction order is reversed from the claim. Both `upload_and_extract()` and `extract_from_url()` run extraction first (commits staged records), then attempt to store the document. If document storage fails, the committed extraction preview is orphaned with no cleanup path. The fix requires either: (a) storing the document first and only running extraction on success, or (b) rolling back the extraction commit when document storage fails.
- [x] Staging batch transaction — `create_staged_extraction` uses explicit commit/rollback; auto-materialization path rolls back on failure. (`staging.py:53-77`)
- [x] Missing entity reference in materialization — raises `ValueError` with structured message, does not log and continue. (`materialization.py:92-96, 162-166`)
- [ ] **[NEW-EXT-m1]** `backend/app/services/batch_extraction_orchestrator.py:366-433` — text span validation is absent. Entity slug coherence (slugs cross-checked against extracted entity list) is implemented, but text spans are not verified against source text. This is a gap in the claimed semantic validation (DF-EXT-M6).
- [x] Workflow refactor — `document_extraction_workflow.py` is a narrow re-export shim; internal callers import from owning modules directly. (`document_extraction_workflow.py:1-49`)

---

### Extraction Review

- [ ] **[NEW-RVW-C1]** `backend/app/models/entity.py:39-41`, `backend/app/models/relation.py:44-46` — `is_rejected` columns and migration 014 exist, and the flag is correctly filtered from list/search/export queries. However, the flag is **never set** during the rejection flow. `StagedExtraction.status` is set to `REJECTED` but the `is_rejected` boolean on materialized `Entity` and `Relation` rows is never written. Any entity or relation that was materialized before rejection remains visible in all queries. Fix: in the rejection path of `document_extraction_processing.py` (around line 670), find and set `is_rejected = True` on all entity/relation rows that were created from the staged extraction being rejected.
- [x] Attribution — `created_by_user_id` set on `EntityRevision`, `RelationRevision`, and claim revisions during materialization. `auto_approved` column present in `StagedExtraction`, set in `auto_commit.py:85`. Migration 011 correct.
- [x] Batch review failure inspection — `submitBatchReview()` checks `response.failed > 0` and shows warning. (`useReviewDialog.ts:94-105`)

---

### Revision Review

- [x] `confirm()` sets `is_current=True` on confirmed revision, populates `confirmed_by_user_id` and `confirmed_at`. (`revision_review_service.py:152-154`)
- [ ] **[NEW-REV-M1]** `backend/app/services/revision_review_service.py:132, 142-149` — `SELECT FOR UPDATE` is applied only to the confirmed revision row. The sibling update (clearing `is_current=False` on all other revisions) runs outside the lock. A concurrent second confirm of a different revision for the same entity can race and leave two `is_current=True` rows. Fix: apply `with_for_update()` to the sibling query as well, or use a single `UPDATE ... WHERE entity_id = ? AND id != ? AND is_current = True` atomic statement.
- [ ] **[NEW-REV-m1]** `backend/tests/test_revision_review_service.py` — no test asserts that all sibling revisions have `is_current=False` after `confirm()`. This is a critical invariant with no coverage.
- [x] Partial unique index for `is_current=True` per revision parent present on entity/relation/source revision models.
- [x] `SELECT FOR UPDATE` on confirmed revision prevents double-confirm of the same row. (`revision_review_service.py:132`)
- [x] Optimistic item removal in `LlmDraftsPanel` — item removed on API success, background refresh failure surfaced separately. (`LlmDraftsPanel.tsx:87-113`)

---

### Entity Merge

- [x] Circular merge guard — rejects if either entity appears as `source_entity_id` in existing merge records. (`entity_merge_service.py:121-129`)
- [ ] **[NEW-MRG-M1]** `backend/app/services/entity_query_builder.py`, `backend/app/services/search/entity_search.py`, `backend/app/services/export_service.py` — `is_merged` is filtered in `canonical_entity_predicate()` (used for relation role lookups and inference) but is **not** filtered in entity list queries, entity search, or entity export. Merged entities remain fully visible in the public entity list, search results, and exports. Fix: add `is_merged == False` to `entity_query_builder.py` base query, `entity_search.py` search query, and the entity export query.
- [ ] **[NEW-MRG-m1]** `backend/tests/test_entity_merge_service.py` — no test verifies that the circular merge guard rejects the attempt. The guard is implemented but untested.
- [x] Inference cache invalidated for both source and target entity on merge. (`entity_merge_service.py:155-159`, covered by `test_merge_entities_invalidates_inference_cache`)

---

### Export & Import

- [x] Audit trail — `status`, `created_at`, `created_by_user_id`, `llm_review_status` present in entity, source, and relation export schemas. (`export.py`)
- [x] Import file size limit — 10 MB cap in `_check_file_size()` enforced before `file.file.read()`. HTTP 413 returned. (`import_routes.py:33-45`)
- [x] Summary round-trip — JSON export flattens `summary` to `summary_en`/`summary_fr`. (`export_service.py:147-148, 190-191`)
- [x] CSV N-ary roles — `roles_json` column, dynamic iteration over all roles, no 2-role assumption. (`export_service.py:450-465`)
- [x] Import UI — client-side 10 MB check, `CircularProgress` indicators, `handleReset()` cancel on both import views.

---

### Smart Discovery

- [x] PMID deduplication — `_find_existing_pmids()` called before import loop; already-imported PMIDs skipped. (`document_extraction_discovery.py:188, 370-386`)
- [x] Rate limiting — `@limiter.limit("5/minute")` on all three discovery endpoints. (`discovery.py:47, 90, 129`)
- [ ] **[NEW-DSC-M1]** `backend/app/services/document_extraction_discovery.py:109-117` — `discovery_query` is not stored in import provenance. `imported_at` and `import_method` are present, but the search query that led to the discovery is not recorded. Fix: pass the query string into the metadata dict as `"discovery_query"` when called from `run_smart_discovery()`.
- [ ] **[NEW-DSC-M2]** `backend/app/services/document_extraction_discovery.py:116`, `backend/app/models/source_revision.py` — `calculated_trust_level` is stored as a JSON value inside `source_metadata`, not as a dedicated typed column. This loses type safety, prevents indexed queries on trust level, and is inconsistent with how trust level is handled elsewhere. Fix: add a `calculated_trust_level: Mapped[float | None]` column to `SourceRevision`, write it directly, and remove it from the metadata blob.

---

### API & Data Contracts

- [x] API client auth separation — dispatches `AUTH_SESSION_EXPIRED_EVENT` instead of redirecting; `AuthContext` owns the state transition. (`client.tsx:205`, `AuthContext.tsx:69-82`)
- [x] Extraction discovery route validation — request invariants in schema helpers, routes delegate to service. (`discovery.py`)
- [x] Inference/explanation scope filter — typed query dependency shared across both route families.
- [x] Error envelope — all handlers return `{"error": {...}}`; no `"detail"` fallback. (`error_handler.py`)
- [x] `useAsyncAction` routing — `setError` provided → inline only; no `setError` → toast only. (`useAsyncAction.ts:39-47`)
- [x] Pagination wire contract — four real serialized fields (`items`, `total`, `limit`, `offset`); no phantom derived fields. (`pagination.py`)
- [x] `DocumentExtractionPreview` contract — `needs_review_count`, `auto_verified_count`, `avg_validation_score` on both backend schema and frontend type; `extracted_text` removed. (`source.py:143-154`, `extraction.ts:119-129`)
- [x] Revision-review counts — `DraftRevisionCountsResponse` declared as `response_model` on `/counts` endpoint. (`revision_review.py:53`, `review.py:41-46`)
- [x] Caddyfile routing — `handle /api/*` (prefix-preserving), not `handle_path`. (`Caddyfile:4`)
- [x] Core frontend types — `created_by_user_id` and `llm_review_status` present on entity, source, and relation types.

---

### LLM Provenance & Prompts

- [x] `llm_review_status` — present on all three revision models; `"pending_review"` on creation, `"auto_verified"` from auto-commit, `"confirmed"` on human confirm; in schemas, mappers, and export. (`bulk_creation_service.py:87`, `auto_commit.py:90-100`, `revision_review_service.py:156`)
- [x] LLM extraction prompts — explicit textual support required; unsupported items omitted; contradictions, negation, and hedging preserved as separate outputs. (`prompts.py:18-38, 45-100`)

---

### Frontend Pages & Navigation

- [x] Relation detail page — `/relations/:id` route defined; semantic summary, participant roles, source context, audit metadata rendered; all entry points updated; test present. (`RelationDetailView.tsx`, `routes.tsx:86`)
- [x] Explanation/PropertyDetail consolidation — `ExplanationView` redirects to canonical PropertyDetail URL; all inference entry points use `/entities/:id/properties/:roleType`.
- [x] Inferences index page — dense table with role/score direction/score/confidence/disagreement/evidence-count columns; failure strip above main table; test present.
- [x] Evidence deep-linking — `EvidenceTrace` links to `/sources/:id?relation=:relationId#relation-:relationId`; source detail scrolls and highlights target row; search relation results use same deep link.
- [x] `ProtectedRoute` `returnTo` — destination preserved in router state; `AccountView` redirects on login success.
- [x] Source detail layout — identity → evidence section → relations table → extraction controls.
- [x] Synthesis summary block — confidence/contradiction chips and evidence statement precede metric sections. (`SynthesisView.tsx:158-215`)
- [x] Review queue — tabs labeled "Staged Extraction Review" / "LLM Draft Review"; section order stable; selection cleared on filter context change.

---

### Frontend UX & Evidence Presentation

- [x] InferenceBlock — labeled ScoreBar axis, score-polarity labels via `getScoreInterpretation()`, interpretation copy. (`InferenceBlock.tsx:26-92`)
- [x] Explanation page — supporting and contradicting evidence in separate sections; contradictions rendered when disagreement present.
- [x] Disagreements — claim wording via `formatRelationClaim()` visible; scope/context before source link; side-by-side tables. (`DisagreementsGroupsSection.tsx:92-117`)
- [x] ScopeFilterPanel — guided dimension dropdown with `SCOPE_FILTER_SUGGESTIONS`; custom mode toggle available.
- [x] Source relations section — direction filter chips, accordion groups by kind, summary counts, row anchors and deep links preserved.
- [x] GlobalSearch — explicit `aria-label`, relation suggestions routed to `/relations/:id`.

---

### Deployment

- [x] Production compose — bind mounts live only in `docker-compose.dev-mounts.yml`; deployed stacks avoid app source mounts.
- [x] API migrations on start — deployed API startup runs `alembic upgrade head` before serving traffic.
- [x] Production web — deployed frontend is served as a static build, not via `vite preview`.
- [x] API health check — present in base compose; `caddy` depends on `service_healthy`.
- [x] Compose surface area — removed the redundant production-from-source stack; production docs now point to `docker-compose.self-host.yml` as the single supported prod path.

---

### E2E Coverage

- [x] `E2E-G1` Token refresh — three-test suite: silent re-auth, redirect when both tokens absent, replay rejection after rotation. (`token-refresh.spec.ts`)
- [x] `E2E-G2` Contradiction visibility — two contradictory relations seeded via API; disagreements page assertions present. (`viewing.spec.ts:115-186`)
- [x] `E2E-G3` Revision history — entity and relation both tested; `updated_at` diff and field-value change asserted via API. (`revision-history.spec.ts`)
- [x] `E2E-G4` Disagreements with real data — covered by E2E-G2 test with API-seeded contradictory data.
- [x] `E2E-G5` Non-admin authorization — regular user session tested for both UI navigation and API 403. (`panel.spec.ts:80-153`)
- [x] `E2E-G6` Pagination — entities created to exceed PAGE_SIZE; load-more verified; count asserted. (`pagination.spec.ts`)
- [x] `E2E-G7` Export content — source title verified in downloaded JSON file contents. (`export.spec.ts:51-87`)
- [x] `E2E-G8` Email verification — registration success message, unverified login denial, and conditional link-follow test all present. (`email-verification.spec.ts`)
- [x] `E2E-G9` Unknown ID 404 — navigates to non-existent entity UUID, asserts not-found text or 404 heading. (`crud.spec.ts:182-192`)

---

## Defects Requiring Fixes

| ID | Severity | File | Description |
|----|----------|------|-------------|
| NEW-INF-C1 | **Critical** | `explanation_read_models.py:23-26` | `build_contradiction_detail()` hardcodes `supporting_sources=[]`, discarding accumulated evidence. Contradictions shown with no source attribution. |
| NEW-RVW-C1 | **Critical** | `document_extraction_processing.py:~670` | `is_rejected` flag never set on `Entity`/`Relation` rows when an extraction is rejected. Column and migration exist; assignment is missing. |
| NEW-EXT-M1 | **Major** | `document.py:114-211` | Extraction commits before document is stored. If document storage fails, extraction preview is orphaned with no cleanup. |
| NEW-REV-M1 | **Major** | `revision_review_service.py:142-149` | Sibling `is_current=False` update runs outside the `SELECT FOR UPDATE` lock. Race condition can leave two `is_current=True` revisions for the same entity. |
| NEW-MRG-M1 | **Major** | `entity_query_builder.py`, `entity_search.py`, `export_service.py` | `is_merged` not filtered in entity list, search, or export. Merged entities remain fully visible. |
| NEW-DSC-M2 | **Major** | `document_extraction_discovery.py:116`, `source_revision.py` | `calculated_trust_level` stored as JSON blob value, not a typed column. Prevents indexed queries and type safety. |
| NEW-SEARCH-M1 | **Major** | `backend/alembic/versions/` | `pg_trgm` GIN indexes not present in any migration. All text searches are sequential scans. |
| NEW-INF-M1 | **Major** | `relation_role_revision.py` | Per-role `confidence` column absent. Only `disagreement` is stored per-role; confidence is computed but not persisted. |
| NEW-DSC-M1 | **Major** | `document_extraction_discovery.py:109-117` | `discovery_query` not stored in import provenance metadata. |
| NEW-EXT-m1 | **Minor** | `batch_extraction_orchestrator.py:366-433` | Text span validation missing. Only entity slug coherence is checked; spans not verified against source text. |
| NEW-REV-m1 | **Minor** | `test_revision_review_service.py` | No test asserts siblings have `is_current=False` after `confirm()`. |
| NEW-MRG-m1 | **Minor** | `test_entity_merge_service.py` | No test verifies circular merge guard rejects the attempt. |

---

## Post-v1.0 Backlog

- **Graph visualization** — Explicitly not MVP.
- **TypeDB integration** — Optional reasoning engine.
- **Advanced auth** — 2FA (TOTP), OAuth providers (Google, GitHub).
- **Real-time collaboration** — WebSocket/SSE for live updates.
- **Multi-tenancy / RBAC** — Organization model, role-based access control.
