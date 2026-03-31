# Current Work

**Last updated**: 2026-03-30 (entity inference UX fixes implemented)

---

## Open Findings

### LLM Prompt Audit — 2026-03-31

Source: `.temp/llm_prompt_audit_2026-03-31.md`

#### Major

- [x] **LLM31-M1** `backend/app/llm/prompts.py` - Extraction prompts allowed implied entities, relations, and claims instead of requiring explicit textual support. Fixed: tightened system, entity, relation, claim, and batch prompts to require explicit support and omission of unsupported items.
- [x] **LLM31-M2** `backend/app/llm/prompts.py` - Entity summaries and examples encouraged background synthesis beyond the source text. Fixed: summaries are now source-bounded and examples no longer inject unstated medical facts.
- [x] **LLM31-M3** `backend/app/llm/prompts.py` - Prompts did not explicitly preserve contradiction, hedging, and qualifiers as separate outputs. Fixed: added rules to preserve negation and uncertainty and to emit separate items for competing findings.

#### Minor

- [x] **LLM31-m1** `backend/app/llm/prompts.py` - Entity-linking prompt lacked a conservative uncertain-match rule. Fixed: prompt now requires `"NEW"` on uncertainty and forbids external-knowledge merges.

### Full Audit - 2026-03-30 (score 81/100)

Source: `.temp/full_audit_report_2026-03-30.md`

#### Critical

- [x] **AUD30-C1** `backend/app/services/document_service.py:101-106,162-167,223` - Document upload size limit is enforced only after `await file.read()` when `UploadFile.size` is missing, so oversized uploads can still be fully buffered into memory on extraction endpoints. Fixed: added `_read_bounded()` chunked reader (64 KB chunks); replaced unbounded `file.read()` calls in `extract_text_from_pdf` and `extract_text_from_txt`; added 8 unit tests in `backend/tests/test_document_service.py`.

#### Major

- [x] **AUD30-M1** `frontend/src/components/GlobalSearch.tsx:41-63` + `frontend/src/api/search.ts:106-119` - `AbortController` cleanup never reaches the actual network request, so stale suggestion fetches still run to completion after rapid typing or unmount. Fixed: `signal` was already wired through `getSuggestions()` → `apiFetch()`; added `AbortError` early-exit in `apiRequest` catch block (`client.tsx:162-165`) so aborted requests re-throw without logging or wrapping — `GlobalSearch` already guards state updates with `controller.signal.aborted`.
- [x] **AUD30-M2** `frontend/src/views/ResendVerificationView.tsx:7-178` + `frontend/src/views/VerifyEmailView.tsx:7-176` - Auth recovery views bypass shared MUI/i18n patterns and `ResendVerificationView` shows both inline and toast errors for the same failure. Fixed: both views rewritten to use `useTranslation` + `resend_verification`/`verify_email` i18n namespaces (en + fr); `ResendVerificationView` now uses `useAsyncAction(setSubmitError)` so errors are inline-only (no toast); `VerifyEmailView` missing-token path drops `showError` and sets local error state only.
- [x] **AUD30-M3** `frontend/src/views/CreateSourceView.tsx:153,170,178,328-340,354,368` + `frontend/src/components/layout/MobileDrawer.tsx:204` - Primary UI still ships hardcoded and malformed user-visible text. Fixed: removed redundant `✓` glyph from `create_source.autofilled` fallback (Alert icon handles it); PubMed/DOI chip labels use `t("create_source.pubmed_id_chip"/"doi_chip")` with interpolation; quality-scoring block (6 GRADE level strings + header) moved to `create_source.quality_level_*` keys (eliminates `•`/`⊕`/`◯` raw glyphs); summary placeholders use `t()`; `MobileDrawer` language label replaced with `t("menu.current_language")`; all keys added to en.json + fr.json.
- [x] **AUD30-M4** `e2e/tests/sources/filters.spec.ts:75`, `e2e/tests/review-queue/queue.spec.ts:121`, `e2e/tests/entities/revision-history.spec.ts:45,127` - New Playwright specs rely on fixed sleeps instead of observable conditions, making CI timing-dependent. Fixed: `filters.spec.ts` waits for `[role="presentation"]` to not be visible; `queue.spec.ts` drops the sleep (subsequent `toBeVisible` already polls); `revision-history.spec.ts` uses `waitForLoadState('networkidle')` to confirm the save request has settled before reading back.

#### Minor

- [x] **AUD30-m1** `frontend/src/components/EntityTermsManager.tsx:70-80,118-120,160-162,217-220,382` - The entity-terms editor hardcodes language labels, validation copy, and fallback display text in component code. Fixed: `LANGUAGE_OPTIONS` entries carry `key` fields consumed via `t(opt.key)` in render and `getLanguageLabel`; `"International"` fallback and `"Display order: …"` secondary text use `t()`; `"Term cannot be empty"` validation uses `t("entityTerms.validation_term_empty")`; redundant `showError` on validation path removed; three `console.error` pre-log calls removed (covered by `handlePageError`); all 26 `entityTerms.*` keys added to en.json + fr.json.

### Error Propagation to UI Audit — 2026-03-28 (score 62/100 → 100/100)

Source: `.temp/error_propagation_audit_report_2026-03-28.md`

#### Critical

- [x] **ERR-C1** `backend/app/middleware/error_handler.py:30-35` + `frontend/src/api/client.tsx:66-78` — Dual error envelope. Fixed: dropped `"detail"` key from `app_exception_handler` and `validation_exception_handler`; all handlers now return `{"error":{…}}` exclusively; simplified `extractBackendErrorPayload` in client; added 7 canonical-envelope tests in `test_error_handlers.py`.
- [x] **ERR-C2** `backend/app/utils/errors.py:17-79` + `frontend/src/utils/errorHandler.ts:15-74` — ErrorCode enum drift. Fixed: added `ENTITY_HAS_RELATIONS` to frontend enum; added `test_error_code_enum_matches_known_set` snapshot test to `test_error_handlers.py`.

#### Major

- [x] **ERR-M1** `frontend/src/hooks/useAsyncAction.ts` — Duplicate toast+inline display. Fixed: when `setError` is provided, `useAsyncAction` now sets local state and suppresses the Snackbar toast; without `setError` it delegates to `showError` (toast only). Rule documented in `CODE_GUIDE.md §15`.
- [x] **ERR-M2** `frontend/src/hooks/useAsyncAction.ts`, `useAsyncResource.ts`, `usePageErrorHandler.ts` — No selection guidance. Fixed: added §15 to `docs/development/CODE_GUIDE.md` with a table documenting when to use each hook.
- [x] **ERR-M3** `frontend/src/notifications/NotificationContext.tsx` — Developer details invisible. Fixed: added expandable "Dev details" section inside the Snackbar (dev builds only, gated on `import.meta.env.DEV`); shows `code`, `developerMessage`, `field`, `context`.
- [x] **ERR-M4** `backend/app/api/error_handlers.py:20-62` — `@handle_extraction_errors` discarded error context. Fixed: non-`AppException` errors now preserve `str(exc)` as the `details` field of the wrapped `EXTRACTION_FAILED` AppException.

#### Minor

- [x] **ERR-m1** `frontend/src/notifications/NotificationContext.tsx` — Ad-hoc console.error. Fixed: `showError()` now calls `formatErrorForLogging(parsedError)`.
- [x] **ERR-m2** `frontend/src/utils/errorHandler.ts` — `shouldShowErrorToUser()` undocumented fallback. Fixed: added JSDoc stating callers must still log via `formatErrorForLogging()` before redirecting.
- [x] **ERR-m3** `backend/app/utils/errors.py:211` — `LLMServiceUnavailableException` leaked `OPENAI_API_KEY`. Fixed: message changed to "AI service is unavailable. Please try again later."; hint moved to `details`.
- [x] **ERR-m4** `frontend/src/utils/errorHandler.ts:267-295` — Hardcoded status→i18n keys. Fixed: replaced if/else chain with `HTTP_STATUS_ERROR_CODES` and `HTTP_STATUS_MESSAGES` maps.

---

### Full Repository Audit — 2026-03-29

Source: `.temp/full_repository_audit_2026-03-29.md`

#### Critical

- [x] **AUD29R-C1** `Caddyfile:3-6` + `backend/app/main.py:129-147` — The default local dev proxy stripped `/api` with `handle_path` even though FastAPI routes are mounted under `/api`. Fixed by switching the local Caddy rule to `handle /api/*` so the prefix is preserved, and by adding `make dev-check`, which smoke-checks the proxied `/api/entities/filter-options` route instead of relying on the misleading `/api/docs` case.
- [x] **AUD29R-C2** `backend/app/api/extraction_review.py:36-45,71-75,118-127` + `frontend/src/app/routes.tsx:86` + `frontend/src/components/Layout.tsx:35-40` + `frontend/src/components/ProtectedRoute.tsx:9-24` — The review queue was effectively available to any authenticated user. Fixed by requiring `get_current_active_superuser` on the read endpoints, adding a frontend `SuperuserRoute` for `/review-queue`, and hiding the review-queue navigation item unless the current user is a superuser.

#### Major

- [x] **AUD29R-M1** `docker-compose.e2e.yml:35,48,50,52` + `backend/app/config.py:7,32,38,46` — The E2E API container set several environment variables that the backend did not read: `ENVIRONMENT`, `SMTP_USERNAME`, `SMTP_FROM_EMAIL`, and `REQUIRE_EMAIL_VERIFICATION`. Fixed by renaming them to `ENV`, `SMTP_USER`, `EMAIL_FROM`, and `EMAIL_VERIFICATION_REQUIRED`, and by strengthening the E2E API health check to assert `TESTING`, `ENV`, `EMAIL_FROM`, and `EMAIL_VERIFICATION_REQUIRED` through `/api/test/health`.
- [x] **AUD29R-M2** `frontend/src/api/extractionReview.ts:96-127` + `backend/app/api/extraction_review.py:37-58` + `backend/app/schemas/staged_extraction.py:216-236` + `backend/app/services/extraction_review/queries.py:24-57` — The pending-extractions contract was internally inconsistent. Fixed by parsing the full `StagedExtractionFilters` query model in the route, forcing only `status="pending"` at the boundary, and adding endpoint coverage that asserts `max_validation_score`, `auto_commit_eligible`, `sort_by`, `sort_order`, and pagination all survive the route layer.
- [x] **AUD29R-M3** `frontend/src/app/routes.tsx:75` + `frontend/src/components/ProtectedRoute.tsx:9-24` + `frontend/src/components/ProfileMenu.tsx:135-143` + `frontend/src/views/AdminView.tsx:123-130` — The admin page route was only authenticated, not superuser-gated. Fixed by reusing `SuperuserRoute` for `/admin`, so manual navigation now matches the existing superuser-only UI entry points and the backend authorization boundary.

### Small Bug Audit — 2026-03-29

Source: `.temp/small_bug_audit_2026-03-29.md`

#### Minor

- [ ] **AUD29S-m1** `frontend/src/components/BugReportDialog.tsx:35-45,53-66` — Anonymous bug-report CAPTCHA state is not cleared before reloading. If the dialog previously loaded a CAPTCHA successfully and a later reopen fails to fetch a fresh one, the old token/question remain in state and submission still uses stale CAPTCHA data. Reset `captcha` to `null` when the dialog opens and on fetch failure before showing the error.
- [ ] **AUD29S-m2** `frontend/src/components/GlobalSearch.tsx:41-62` + `frontend/src/api/search.ts:106-119` — Global search creates an `AbortController`, but the signal is never passed into `getSuggestions()`/`fetch()`. Cancellation is therefore cosmetic: slower responses from older queries can still win and overwrite newer suggestions. Thread an optional `signal` through `getSuggestions()` into `apiFetch()`, then pass `controller.signal` from `GlobalSearch`.
- [ ] **AUD29S-m3** `e2e/tests/account/settings.spec.ts:57-65` + `e2e/fixtures/test-data.ts:7-10` — The mismatch-password E2E test hardcodes the current admin password as `changeme123` instead of using `ADMIN_USER.password`. If the E2E admin fixture changes, the test fails for the wrong reason. Read the password from the shared fixture so the test stays aligned with container/bootstrap configuration.

### Design Audit — 2026-03-29

Source: `.temp/design_audit_2026-03-29.md`

#### Major

- [ ] **AUD29D-M1** `backend/app/api/document_extraction_routes/discovery.py:48-157,166-208,217-264` + `backend/app/api/document_extraction_schemas.py:4-40` — The extraction discovery routes are carrying domain validation and response-mapping logic that should live in schemas/services. `smart_discovery()` manually enforces slug/database/result constraints, `bulk_search_pubmed()` manually validates limits, and all three handlers hand-assemble response DTOs from service summaries. Move invariant checks into Pydantic validators/shared request models, move summary-to-response mapping into service/helper functions, and keep the routes at validate → authorize → call service → return schema.
- [ ] **AUD29D-M2** `frontend/src/api/client.tsx:95-115,147-233` + `frontend/src/auth/AuthContext.tsx:64-145` — The shared API client owns auth/session UX instead of staying a transport boundary. It refreshes tokens, mutates auth storage, logs parsed errors, and hard-redirects with `window.location.href`, while `AuthContext` separately owns session restoration/logout behavior. Return a typed auth-expired result from the client, keep token-state transitions explicit, and let `AuthContext` or a router-level auth boundary own logout + redirect decisions.
- [ ] **AUD29D-M3** `backend/app/api/inferences.py:12-44` + `backend/app/api/explain.py:23-71` + `backend/app/api/inference_dependencies.py:12-44` + `frontend/src/api/inferences.ts:10-25` + `frontend/src/api/explanations.ts:88-98` — Scope filtering for inference/explanation is defined as an opaque JSON string in a query parameter and parsed by hand in `parse_scope_filter()`. That duplicates a weakly typed contract across backend routes and frontend clients instead of using the project’s normal schema-first pattern. Promote scope filtering to a shared typed contract (query model or request body schema), reuse it across inference/explanation APIs, and delete the handwritten JSON parser.
- [ ] **AUD29D-M4** `backend/app/services/export_service.py:44-97,170-245,325-424,430-499` — `ExportService` is a 499-line monolith that mixes SQL loading, ad hoc dict assembly, and JSON/CSV/RDF rendering in one place. It duplicates source serialization between `export_sources()` and `export_full_graph()`, reparses its own JSON output to compose the full export, and still performs per-relation role queries. Split it into query loaders, typed export row models/serializers, and format renderers; batch-load relation roles once; and reuse shared source/entity/relation serializers when building the full-graph bundle.
- [ ] **AUD29D-M5** `backend/app/services/document_extraction_processing.py:62-200,227-776` + `backend/app/services/document_extraction_workflow.py:1-95` — The document-extraction workflow is concentrated in a god module plus a barrel-style facade. One 776-line module mixes protocol definitions, preview orchestration, URL/PubMed fetch logic, source-revision enrichment, staged-extraction reconciliation, and graph materialization, then `document_extraction_workflow.py` re-exports nearly all of it and hides ownership boundaries. Split this into focused modules by responsibility and remove the broad re-export layer so callers import from the actual owning module.

### Flow Audit — 2026-03-29

Source: `.temp/flow_audit_2026-03-29.md`

#### Critical

- [ ] **AUD29F-C1** `backend/app/api/entities.py:45-94` + `backend/app/services/entity_query_builder.py:47-79` + `backend/app/services/entity_service.py:101-121` + `backend/app/api/sources.py:111-168` + `backend/app/services/source_service.py:90-150` + `backend/app/api/relations.py:20-31` + `backend/app/services/relation_service.py:117-167` + `backend/app/repositories/relation_repo.py:16-40` — Regular entity/source/relation read flows still serve current draft revisions instead of only confirmed records. The review queue is meant to fence off unreviewed LLM output, but public/user-facing list and detail queries only check `is_current`, so draft revisions can leak through normal frontend views and direct API reads. Require `status == "confirmed"` on user-facing read paths by default, reserve draft visibility for review/superuser endpoints, and add regression coverage for entity/source/relation draft isolation.

#### Major

- [ ] **AUD29F-M1** `backend/app/services/entity_linking_service.py:140-183` — Extraction linking can match against draft entities. Both exact-slug and synonym lookups only require `is_current == True`, so extraction preview may suggest or auto-link to a draft entity that has not been reviewed yet, letting approved extraction output attach to non-authoritative graph nodes. Add `EntityRevision.status == "confirmed"` to both lookup paths and cover it with an extraction-preview test.
- [ ] **AUD29F-M2** `frontend/src/views/SourcesView.tsx:106-174` — Source domain/role filters reset the list UI but do not trigger a fresh fetch. `loadSources()` reads `filters.domain` and `filters.role`, yet its `useCallback` dependencies omit them, so changing those controls leaves the callback stale and the rendered results can stay unfiltered. Add both filters to the callback dependencies and cover the behavior with a frontend test that verifies a refetch when domain/role changes.
- [ ] **AUD29F-M3** `frontend/src/views/SourcesView.tsx:92-104,226-227` + `frontend/src/components/ExportMenu.tsx:23-30,54-60` + `frontend/src/api/export.ts:5-25` + `backend/app/api/export.py:62-128` + `backend/app/services/export_service.py:170-187,325-362` — Export flows do not honor the same filters the UI forwards. The Sources screen sends its active `kind/year/trust/search/domain/role` filters into source and relation exports and comments that exports reflect “currently visible” data, but `export_sources()` ignores `domain` and `role` and does not search `origin`, while `export_relations()` accepts no filters at all. Either implement the forwarded filters end-to-end or stop forwarding/advertising unsupported ones, and add an integration test that filtered exports match the visible subset.
- [ ] **AUD29F-M4** `backend/app/services/document_extraction_processing.py:727-775` + `backend/app/schemas/source.py:156-163` + `frontend/src/types/extraction.ts:139-145` — `SaveExtractionResult.created_entity_ids` is semantically wrong. The backend builds it from `entity_mapping` after merging `entity_links`, so it contains both newly created IDs and existing linked entity IDs even though the field name promises only created entities. Return only newly created IDs, or split the contract into `created_entity_ids` plus `linked_entity_ids`, then update frontend types/tests accordingly.

### Communication Audit — 2026-03-29

Source: `.temp/communication_audit_2026-03-29.md`

#### Major

- [ ] **AUD29K-M1** `backend/app/schemas/entity.py:34-53` + `backend/app/schemas/source.py:58-82` + `backend/app/schemas/relation.py:58-77` + `frontend/src/types/entity.ts:1-9` + `frontend/src/types/source.ts:3-15` + `frontend/src/types/relation.ts:25-36` — Core read contracts have drifted between backend and frontend bricks. The backend now returns provenance/review/document fields such as `updated_at`, `created_with_llm`, `created_by_user_id`, `llm_review_status`, `document_format`, `document_file_name`, and `document_extracted_at`, but the frontend’s handwritten resource types still model older, smaller payloads. Sync the frontend types with the backend schemas, then add contract coverage so future schema changes cannot silently widen the gap.
- [ ] **AUD29K-M2** `backend/app/schemas/review.py:15-29` + `backend/app/services/revision_review_service.py:57-116` + `frontend/src/api/revisionReview.ts:15-26` — The revision-review API contract is inconsistent across bricks: backend draft-revision responses include `llm_review_status`, but the frontend `DraftRevisionRead` type omits it. Add the missing field to the frontend client type and cover it in the review-queue contract tests so the queue UI and API agree on the shape.
- [ ] **AUD29K-M3** `backend/app/schemas/pagination.py:14-56` + `frontend/src/api/entities.ts:44-49` + `frontend/src/api/sources.ts:24-29` — Pagination is named like a shared abstraction but behaves like separate contracts. Backend `PaginatedResponse` defines derived metadata (`has_more`, `current_page`, `total_pages`) as Python properties that are not serialized, while frontend clients separately define narrower pagination interfaces. Either expose the derived fields as real API fields or remove them from the backend schema and standardize one documented wire contract mirrored in the frontend.

### Contract Audit — 2026-03-29

Source: `.temp/contract_audit_2026-03-29.md`

#### Major

- [ ] **AUD29T-M1** `backend/app/schemas/source.py:134-145` + `backend/app/services/document_extraction_processing.py:440-450` + `backend/app/services/document_extraction_processing.py:499-509` + `frontend/src/types/extraction.ts:119-127` + `frontend/src/components/ExtractionPreview.tsx:208-235` — The document-extraction preview contract drifts in both directions. Backend preview responses now carry `needs_review_count`, `auto_verified_count`, and `avg_validation_score`, but the frontend type drops those fields and instead advertises `extracted_text`, which the backend never returns. The UI still renders an extracted-text accordion behind that phantom field, while the real review metadata is unavailable to the type system. Define one canonical preview payload, remove or implement `extracted_text` end to end, add the real review metadata to the frontend type, and cover the payload with a contract test.
- [ ] **AUD29T-M2** `backend/app/api/revision_review.py:52-58` + `backend/app/services/revision_review_service.py:216-231` + `frontend/src/api/revisionReview.ts:38-61` — The revision-review counts endpoint has no backend schema even though the frontend treats it as a stable shared contract. `GET /review/revisions/counts` returns a raw `dict[str, int]` with no `response_model`, so keys like `entity`, `relation`, `source`, and `total` are only enforced by handwritten frontend assumptions. Add a dedicated backend response schema, declare it on the route, and add focused backend/frontend contract coverage for the exact shape.
- [ ] **AUD29T-M3** `backend/app/schemas/staged_extraction.py:97-103` + `frontend/src/api/extractionReview.ts:24-44` — Staged extraction responses include `auto_approved` backend-side, but the frontend review type drops it. That hides whether an item was manually approved or auto-approved even though the backend already exposes that provenance. Add `auto_approved` to the frontend `StagedExtractionRead` contract and extend review-queue tests so provenance fields stay synchronized.

#### Minor

- [ ] **AUD29T-m1** `frontend/src/types/domain.tsx:1-23` — The frontend still ships a second, stale set of domain contracts that do not match the actual API/resource types. For example, `Relation.direction` is modeled as `"positive" | "negative" | "null" | "mixed"`, which conflicts with the real relation/inference payloads. Delete this file or replace it with re-exports from the canonical typed contracts so there is only one importable source of truth.

### Frontend UX Audit — 2026-03-29

Source: `.temp/frontend_ux_audit_2026-03-29.md`

#### Major

- [ ] **AUD29U-M1** `frontend/src/components/ProtectedRoute.tsx:9-24` — Protected routes discard the user’s intended destination. Unauthenticated users are always redirected to `/account` with no `returnTo` or router-state context, so after login they are not taken back to the edit/create/review page they originally requested. Preserve the attempted location and make the auth flow redirect back after successful login.
- [ ] **AUD29U-M2** `frontend/src/views/SearchView.tsx:125-133` — Relation search results are not traceable to the evidence item the user searched for. Clicking a relation result only opens `/sources/:sourceId`, which forces the user to manually rediscover the relevant relation inside the source page. Add a relation-specific destination or deep-link/highlight support so search lands on the exact evidence row.
- [ ] **AUD29U-M3** `frontend/src/components/source-detail/SourceRelationsSection.tsx:104-110` — Source detail relation rows link to entities using semantic role names instead of entity labels. Users see links like `agent` or `target` rather than the connected entity slug/name, which weakens readability and graph traceability. Render entity-first labels such as `aspirin (agent)` by using `entity_slug` when available and moving the role type to supporting text.
- [ ] **AUD29U-M4** `frontend/src/views/AccountView.tsx:104-112` + `frontend/src/views/AccountView.tsx:136-147` + `frontend/src/views/AccountView.tsx:185-198` — The account page submits login when users press Enter during registration. Login and registration share one form, but `onSubmit` always calls `handleLogin()`, so a user filling the registration-only confirmation field and pressing Enter triggers the wrong action. Split login/register into explicit modes or make Enter submit the currently intended action.

#### Minor

- [ ] **AUD29U-m1** `frontend/src/views/ReviewQueueView.tsx:111-121` + `frontend/src/views/ReviewQueueView.tsx:190-199` + `frontend/src/views/ReviewQueueView.tsx:226-252` + `frontend/src/views/ReviewQueueView.tsx:257-260` — The review queue layout does not adapt cleanly to small screens. Several controls stay in fixed horizontal rows and the score field keeps `width: 200`, which can create cramped or overflowing admin controls on mobile despite the UX brief’s stackable-layout requirement. Add responsive `direction`/`flexWrap` rules and avoid fixed widths on xs screens.

### UI Information Design Audit — 2026-03-30

Source: `.temp/ui_information_design_audit_2026-03-30.md`

#### Major

- [ ] **AUD30E-M1** `frontend/src/views/HomeView.tsx:154-165` + `frontend/src/views/HomeView.tsx:235-296` + `frontend/src/views/HomeView.tsx:303-345` — The landing page leads with system jargon and object-management steps instead of evidence-analysis tasks. The hero copy foregrounds "Hypergraph-based Evidence Knowledge System" and "computed inferences", and the quick-start sequence teaches create/define/add mechanics before showing how to review evidence, inspect disagreement, or trace claims back to sources. Rewrite the home information hierarchy around scientist goals, move implementation terms into secondary copy, and make the primary actions about exploring evidence quality, contradictions, and provenance.
- [ ] **AUD30E-M2** `frontend/src/views/EntitiesView.tsx:268-282` + `frontend/src/views/EntitiesView.tsx:372-445` + `frontend/src/views/SourcesView.tsx:264-278` — Entity and source list pages announce active filters without revealing the actual analytical lens. Users only see "`n` filter(s) active" plus result counts, while the chosen category/trust/consensus/recency/domain filters stay hidden inside the drawer. Add inline active-filter summaries or chips on the page surface, with clear labels and remove affordances, so the visible list is self-describing without reopening the drawer.
- [ ] **AUD30E-M3** `frontend/src/views/SearchView.tsx:160-196` + `frontend/src/views/SearchView.tsx:216-219` + `frontend/src/views/SearchView.tsx:239-269` — The search screen uses system-centric taxonomy and an unlabeled ranking signal. It asks users to "Filter by type" using raw storage categories (`entity`, `source`, `relation`), reports filtered state with those same terms, and renders `relevance_score` as a bare `%` chip that can be mistaken for confidence or evidence quality. Reframe search filters/results in task-friendly language, label the match-strength signal explicitly, and separate result kind, match reason, and ranking into clearer visual roles.
- [ ] **AUD30E-M4** `frontend/src/components/source-detail/SourceMetadataSection.tsx:33-74` — Source detail metadata flattens bibliographic identity, provenance, and quality into one visual layer. Kind, year, trust, authors, origin, URL, PMID, and DOI are rendered as one shallow stack of chips and plain text, which weakens scanability and makes provenance cues feel incidental. Reorganize the section into distinct bibliographic, provenance, and assessment groups; label trust more explicitly; and replace raw URL display text with a concise external-link label.

#### Minor

- [ ] **AUD30E-m1** `frontend/src/views/ReviewQueueView.tsx:124-128` + `frontend/src/views/ReviewQueueView.tsx:136-184` + `frontend/src/views/ReviewQueueView.tsx:187-210` — The review queue information hierarchy relies on ambiguous labels and raw metrics. The staged-extractions tab is labeled with the generic `type_all` string, the stat cards expose counts and percentages without saying how they should guide review, and the filter controls read like admin implementation knobs rather than a guided triage flow. Rename the tabs to the actual queue concepts, add brief interpretive helper text for queue metrics, and rewrite filter labels/help around review decisions rather than backend terms.

### Entity Inference UX Audit — 2026-03-29

Source: `.temp/entity_inference_ux_audit_2026-03-29.md`

#### Major

- [x] **AUD29I-M1** `frontend/src/components/InferenceBlock.tsx:18-53` + `frontend/src/components/InferenceBlock.tsx:191-221` + `frontend/src/components/InferenceBlock.tsx:236-277` — Entity inference cards show score, confidence, coverage, and disagreement as raw numbers without enough scientist-facing interpretation. `ScoreBar` maps `[-1, 1]` into a generic progress bar with no labeled axis or explanation of what positive, negative, or near-zero scores mean, and the role cards do not explain how confidence and disagreement should be read together. Fixed 2026-03-30: added score-polarity labels, interpretation copy, metric guidance, and clearer source-evidence framing in the inference UI.
- [x] **AUD29I-M2** `frontend/src/views/ExplanationView.tsx:221-247` + `frontend/src/views/ExplanationView.tsx:250-263` — The explanation page acknowledges contradictions but does not structure the opposing evidence. When disagreement exists, the UI shows only a warning banner and then a mixed source trace, forcing scientists to reconstruct the competing sides manually. Fixed 2026-03-30: rendered explicit supporting-vs-contradicting evidence sections on the explanation page, each with its own trace table.
- [x] **AUD29I-M3** `frontend/src/components/disagreements/DisagreementsGroupsSection.tsx:37-99` + `frontend/src/components/disagreements/DisagreementsGroupsSection.tsx:157-185` — The disagreements view hides the actual claim content scientists need to compare. Each side-by-side table only shows relation kind, confidence, and a source link, so the page exposes contradiction existence without exposing the competing statements themselves. Fixed 2026-03-30: enriched disagreement tables with claim wording plus context from scope/notes before the source link.
- [x] **AUD29I-M4** `frontend/src/components/entity/ScopeFilterPanel.tsx:78-138` + `frontend/src/views/EntityDetailView.tsx:131-153` — Scope filtering is presented as raw key/value entry instead of domain-language filtering. Scientists must guess valid attribute names and type backend-style keys into free-text fields, which makes a powerful feature feel opaque and error-prone. Fixed 2026-03-30: replaced the raw attribute-first flow with guided scope-dimension selection, examples, clearer help text, and a still-available custom path.

#### Minor

- [x] **AUD29I-m1** `frontend/src/components/synthesis/SynthesisRelationsSection.tsx:124-153` — Synthesis relation rows look individually explorable, but every row under a relation kind navigates to the same destination and exposes little row-specific context. This adds repetitive visual detail without helping scientists understand why one row matters or differs from another. Fixed 2026-03-30: converted the section to representative evidence statements plus a single explicit property-detail action.

### Code Audit — 2026-03-29

Source: `.temp/code_audit_report_2026-03-29.md`

#### Critical

- [x] **AUD29-C1** `backend/app/api/revision_review.py:61-83` + `backend/app/services/revision_review_service.py:124-162` + `backend/app/models/entity_revision.py:64-70` — Draft revision confirmation still does not record reviewer provenance. The route does not pass the current superuser ID into `confirm()`, and the service never sets `confirmed_by_user_id` / `confirmed_at`, so confirmed LLM drafts remain unauditable. Pass `current_user.id` into the service, populate the confirmation fields for entity/relation/source revisions, and add a backend test that asserts both fields are written on confirm.

#### Major

- [x] **AUD29-M1** `backend/app/api/revision_review.py:34-58` — Review-queue list and count endpoints still depend on `get_current_user`, so any authenticated user can enumerate unreviewed LLM draft revisions and queue volume. Require `get_current_active_superuser` on both endpoints to match the confirm/discard authorization boundary.
- [x] **AUD29-M2** `backend/app/services/revision_review_service.py:216-231` — `get_draft_counts()` counts every row with `status == "draft"` and ignores `is_current`, while the queue list only shows current drafts. The review badge and summary can therefore overstate the actionable queue. Add `is_current == True` to all three count queries and cover it with a service test.
- [x] **AUD29-M3** `backend/app/api/explain.py:66-84` — The explanation endpoint catches every exception after `ValueError`, including `AppException`, and rewrites domain errors into generic 500s. Preserve existing `AppException`s with `except AppException: raise` before the generic fallback so auth/validation/not-found semantics survive.
- [x] **AUD29-M4** `backend/app/api/auth_handlers.py:26-40` — `_set_refresh_cookie()` writes the refresh cookie with `domain=settings.COOKIE_DOMAIN`, but `_clear_refresh_cookie()` deletes it without the domain. In deployments that set `COOKIE_DOMAIN`, logout may leave the browser cookie intact and permit unintended session restoration attempts. Delete the cookie with the same domain/path tuple used when setting it, and add an auth handler test for non-`None` `COOKIE_DOMAIN`.

### Deployment Audit v2 — 2026-03-28 (score 55/100 → 100/100 after fixes)

Source: `.temp/deployment_audit_report_2026-03-28_v2.md`

#### Critical

- [x] **DEPLOY2-C1** `docker-compose.prod.yml:23` + `docker-compose.yml:31` — `volumes: []` in prod override does NOT clear base bind mounts. Fixed: moved dev bind mounts and `UV_LINK_MODE` to new `docker-compose.dev-mounts.yml`; removed bind mounts from base `docker-compose.yml`; removed `volumes: []` from `docker-compose.prod.yml`; updated `COMPOSE` in Makefile to include dev-mounts overlay. Verified with `docker compose config`: prod has no bind mounts.

#### Major

- [x] **DEPLOY2-M1** `Makefile:190` — `make self-host-check` web health check always fails: `curl` not in nginx:1.27-alpine. Fixed: replaced `curl` with `wget -qO-`.
- [x] **DEPLOY2-M2** `docs/DEPLOY.md:100` — Section 3.4 documented redundant `make migrate-dev-server`. Fixed: removed step; added note that migrations run automatically on container start.

#### Minor

- [x] **DEPLOY2-m1** `docker-compose.e2e.yml:52` — E2E `web` depends_on `api` used `service_started`. Fixed: added health check to e2e `api`; changed web depends_on to `service_healthy`.
- [x] **DEPLOY2-m2** `Makefile:97,102,107` — `db-shell`, `db-dump`, `db-restore` used host shell vars for `-U`/dbname. Fixed: wrapped pg commands in `sh -c '...'` so `$POSTGRES_USER`/`$POSTGRES_DB` expand from container environment.

---

### Deployment Audit v1 — 2026-03-28 (score 62/100)

Source: `.temp/deployment_audit_report_2026-03-28.md`

#### Critical

- [x] **DEPLOY-C1** `docker-compose.prod.yml:20` — `api` command skips migrations. Fixed: added `alembic upgrade head` to api command; updated DEPLOY.md 6.3.
- [x] **DEPLOY-C2** `docker-compose.prod.yml:27` — `web` service used `vite preview`. Fixed: wired `Dockerfile.prod` (nginx) into prod compose; updated Caddyfile.prod proxy to `web:80`; added `VITE_API_URL` build arg to `Dockerfile.prod`.

#### Major

- [x] **DEPLOY-M1** `deploy/caddy/Caddyfile.prod:1` — Placeholder domain. Fixed: added prominent REQUIRED comment; added concrete `sed` update step to DEPLOY.md 6.2.
- [x] **DEPLOY-M2** `Makefile:173` — Backup `|| true` swallowed errors. Fixed: removed `|| true`; added `mkdir -p backups`.
- [x] **DEPLOY-M3** `docker-compose.yml` — No API health check. Fixed: added `healthcheck` to `api` in base and self-host compose; updated `caddy` depends_on to `service_healthy`; added `curl` to backend Dockerfile.
- [x] **DEPLOY-M4** `frontend/Dockerfile.prod` — Dead artifact. Fixed: wired into prod compose via DEPLOY-C2 fix.

#### Minor

- [ ] **DEPLOY-m1** `backend/.env.test:9,16` — Test-only credentials committed; left as-is per user decision.
- [x] **DEPLOY-m2** `scripts/setup-self-host.sh:116` — Not idempotent. Fixed: replaced sed with `cat >` heredoc; re-running now overwrites the file correctly.
- [x] **DEPLOY-m3** `Makefile:186-188` — `self-host-check` only checked API. Fixed: added web container curl check.
- [x] **DEPLOY-m4** `deploy/caddy/Caddyfile.dev:1` — Placeholder domain. Fixed: added concrete sed step to DEPLOY.md 3.3.

---

### Full System Audit — 2026-03-26 (score 83/100)

Source: `.temp/full_audit_report_2026-03-26.md`

#### Critical

- [x] **AUD26-C1** `backend/app/dependencies/auth.py:127-128` — `get_optional_current_user()` bare `except Exception` swallows all errors and returns `None`, making auth system failures indistinguishable from anonymous requests. Fixed: catch `HTTPException` only (covers `UnauthorizedException`/`ForbiddenException`); log and re-raise everything else. Tests added to `test_auth_endpoints.py::TestGetOptionalCurrentUser`.
- [x] **AUD26-C2** `backend/app/services/document_extraction_processing.py:683-689` — Extraction silently discards relations on parse failure; API reports success while data is lost. Fixed: added `SkippedRelationDetail` schema (extraction_id + relation_type + text_span + error); `reconcile_staged_extractions` now returns `list[SkippedRelationDetail]` instead of `None`; `save_extraction_to_graph` propagates list into `SaveExtractionResult.skipped_relations`; frontend type updated; `SourceExtractionSection` renders a warning `Alert` when any relations were skipped. 2 new tests in `test_document_extraction_workflow.py`.

#### Major

- [x] **AUD26-M1** `backend/app/api/admin.py:105,146,181` — Route handlers execute raw `select()` queries instead of delegating to `AdminService`. Fixed: added `list_categories`, `create_category`, `get_category`, `update_category`, `delete_category` + `_require_category` to `AdminService`; moved `_cat_to_read` helper there; category routes now inject `admin_svc` and delegate; raw `select`, `IntegrityError`, `AsyncSession`, `UiCategory` imports removed from `admin.py`.
- [x] **AUD26-M2** `backend/app/utils/audit.py:101-113` — Audit log failures are silently swallowed with no alerting. Fixed: added `_consecutive_audit_log_failures` counter + `_AUDIT_LOG_FAILURE_THRESHOLD = 5`; counter resets to 0 on success; emits `logger.critical(...)` on every failure at or above threshold, `logger.exception(...)` below it.
- [x] **AUD26-M3** `backend/app/api/error_handlers.py:51` — `handle_extraction_errors` merges all exception types into `EXTRACTION_FAILED`. Fixed: added `except LLMError` handler (503), `except ValidationError` handler (422 with field details), and `except ValueError` handler (422) before the generic fallback.
- [x] **AUD26-M4** `backend/app/services/pubmed_fetcher.py:188-190,338-340,467-469` — Generic `except Exception` handler drops PMID context and error type. Fixed: all three generic handlers now capture `exc` and pass `details=str(exc) or type(exc).__name__`.
- [x] **AUD26-M5** `backend/app/api/test_helpers.py:35,91,182,214` — All four test-support endpoints return untyped dicts with no `response_model`. Fixed: defined `DatabaseResetResponse`, `ReviewQueueSeedResponse`, `UICategoriesSeedResponse`, `TestHealthResponse` in `backend/app/schemas/test_helpers.py`; wired as `response_model` on all four endpoints.
- [x] **AUD26-M6** `backend/app/services/export_service.py:69,99-120` — Export service builds inline `dict` lists with no Pydantic schema. Fixed: defined `EntityExportItem`, `RelationExportItem`, `RelationRoleExportItem`, `SourceExportItem` in `backend/app/schemas/export.py`; all four collection loops now build typed model instances; `_export_*_json` methods use `model_dump(exclude_none=True)`.
- [x] **AUD26-M7** `frontend/src/components/layout/MobileDrawer.tsx:28,37` + `DesktopNavigation.tsx:18,25` — `icon: any` and `user: any` props defeat TypeScript safety. Fixed: `icon` → `ComponentType<SvgIconProps>`; `user` → `UserRead | null` (from `../../types/auth`) in both components.
- [x] **AUD26-M8** `e2e/tests/auth/token-refresh.spec.ts:20` — `waitForTimeout(1000)` anti-pattern causes flaky timing-dependent test. Fixed: removed sleep; preceding `waitForLoadState('networkidle')` already covers async token refresh network activity.
- [x] **AUD26-M9** `backend/app/api/document_extraction_dependencies.py:4-9` — Module-level re-exports of test helpers (suppressed with `# noqa: F401`) couple production module load to test scaffolding. Fixed: removed three noqa re-export lines; `test_document_extraction.py` imports `calculate_relevance` from `app.services.document_extraction_workflow`; `document.py` imports `UrlFetcher` from `app.services.url_fetcher`; `discovery.py` imports `infer_trust_level_from_pubmed_metadata` from `app.utils.source_quality`.

#### Minor

- [x] **AUD26-m1** `backend/app/utils/access_token_manager.py:34,72` — `SECRET_KEY` cached at init; runtime rotation won't take effect. Fixed: `__init__` stores optional overrides; lazy `@property` methods resolve from `settings` at call time if no override was given.
- [x] **AUD26-m2** `backend/app/api/service_dependencies.py` — Stateless service factories had no distinguishing comment. Fixed: added comment block explaining stateless vs DB-bound factories.
- [x] **AUD26-m3** `backend/app/services/` (disagreement visibility) — Magic threshold constants. Fixed: extracted `_STRONG_THRESHOLD`, `_MODERATE_THRESHOLD`, `_WEAK_THRESHOLD` in `derived_properties_service.py`; documented in §12 of `COMPUTED_RELATIONS.md`.
- [x] **AUD26-m4** `backend/app/main.py:45-46` — Token purge background task had no escalation. Fixed: added `_consecutive_token_purge_failures` counter + `_TOKEN_PURGE_FAILURE_THRESHOLD = 3`; `logger.critical(...)` fires at/above threshold.
- [x] **AUD26-m5** `backend/app/services/bug_report_service.py:58-62` — CAPTCHA decode broad catch had no logging. Fixed: added `logger.warning(...)` in the malformed-token except block.
- [x] **AUD26-m6** E2E runtime `test.skip(true, ...)` calls. Fixed: `admin/panel.spec.ts` silent API failures → `throw new Error(...)`; `email-verification.spec.ts` login-ok → `test.skip(loginResp.ok(), '...')`; `document-upload.spec.ts` LLM key → `test.skip(!envCheck, '...')` at test top; `relations/edit-delete.spec.ts` `!relationId` guards → `expect(relationId, '...').toBeTruthy()`.
- [x] **AUD26-m7** `backend/tests/test_bug_report_service.py` — Missing boundary/concurrency coverage. Fixed: added `test_token_with_valid_base64_but_missing_colons_rejected` (no colon delimiters) and `test_concurrent_captcha_tokens_are_independent` (20 tokens, all unique, each verifies with its own answer).
- [x] **AUD26-m8** `backend/tests/test_auth_endpoints.py` + `e2e/tests/auth/token-refresh.spec.ts` — Token rotation tests didn't assert old token rejected. Fixed: added `test_old_refresh_token_rejected_after_rotation` to `TestRefreshToken` (side_effect sequence); added E2E test extracting raw refresh token and re-presenting it post-rotation expecting 401/403.
- [x] **AUD26-m9** `backend/app/services/inference/math.py:60` — Undocumented dict shapes. Fixed: defined `RelationEvidence` and `AggregationResult` TypedDicts; updated `aggregate_evidence` signature.
- [x] **AUD26-m10** `backend/app/services/inference/read_models.py:40` — `resolve_entity_slugs` return shape undocumented. Fixed: return type `dict[UUID, str]` already in signature; added `ScopeFilter` TypedDict and `TypedDict` import in same file.
- [x] **AUD26-m11** `backend/app/llm/prompts.py:10` — `TypedDict` import is actively used by `RelationPromptEntity`/`ExistingPromptEntity`; all format functions already carry `-> str` annotations. No change needed.
- [x] **AUD26-m12** `backend/app/services/inference/read_models.py:59` — Bare `dict` in `matches_scope`. Fixed: defined `ScopeFilter(TypedDict, total=False)`; updated parameter type.
- [x] **AUD26-m13** `backend/app/utils/auth.py:1-56` — Re-export facade with no documented rationale. Fixed: expanded module docstring to explain the single-import-point contract and direct-import prohibition.
- [x] **AUD26-m14** `frontend/src/i18n/fr.json` — Missing French translations. Fixed: added `menu.navigation`, `menu.all_entities`, and complete `evidence_trace` section (9 keys).
- [x] **AUD26-m15** `backend/app/api/test_helpers.py:35,91,182,214` — Functions missing return type annotations. Fixed as part of M5: `response_model` declarations make return types explicit via the schema classes.

---

### E2E Skipped Tests — 2026-03-25

Remaining `test.skip()` conditions after this session's fixes. All actionable skips resolved; remaining ones are intentional.

#### Fixed

- [x] **navigation.spec.ts** — Review queue link check: removed defensive skip; use `waitUntil:'networkidle'` + 10 s timeout for auth context hydration.
- [x] **navigation.spec.ts** — Mobile drawer entities link: removed defensive skip; use `expect(...).toBeVisible({ timeout: 10000 })`.
- [x] **relations/crud.spec.ts** — Entity select fields: `getByLabel(/^entity$/i)` doesn't find MUI v7 Select combobox buttons; changed to `getByRole('combobox', { name: /^entity$/i })`.
- [x] **admin/panel.spec.ts** — "should restrict admin API" test: missing `password_confirmation` in registration → 422; fixed.
- [x] **sources/crud.spec.ts** — Search test: search input is inside the filter drawer; updated test to open drawer first.
- [x] **DisagreementsHeaderSection** — Synthesis button absent when no disagreements; added `Button component={RouterLink}` to the always-rendered header.
- [x] **auth/email-verification.spec.ts** — Missing `password_confirmation` in registration call (prior session).
- [x] **admin/panel.spec.ts** — Missing `password_confirmation` + misleading skip messages (prior session).
- [x] **EntityDetailHeader** — No Synthesis or Disagreements navigation links (prior session).
- [x] **SynthesisView / DisagreementsView** — Error state rendered with no back button when inference API fails (prior session).
- [x] **LanguageSwitch** — Was `IconButton` with no text/aria-label; changed to `Button` showing next-language label ("FR"/"EN") (prior session).
- [x] **SettingsView** — No UI-categories section; added superuser-only section linking to `/admin` (prior session).

#### Intentional / acceptable skips

- **PubMed import** tests: live network required — not fixable without network access or mocking.
- **Review queue** tests: skip gracefully when `staged_extractions` table is empty — correct behavior.
- **RDF export / CSV export**: optional features — skip if menu item absent is correct.
- **Email verification** tests: skip when `EMAIL_VERIFICATION_REQUIRED=False` — correct for E2E env.
- **File input** (`entities/import.spec.ts`): preview button stays disabled after Playwright `setInputFiles` on hidden input — browser automation limitation; test skips descriptively.
- **LLM API key** (`document-upload.spec.ts`): requires `LLM_API_KEY` — environment-dependent.
- **UI categories filter** (`entities/filters.spec.ts`): skip when no categories seeded — correct data-dependent behavior.

---

### Data Flow Audit — Database to Frontend (2026-03-23)

Review identified correctness, security, and provenance problems across 12 data flows.
Source: Parallel agent audit session 2026-03-23.

---

#### AUTH

##### Critical

- [x] **DF-AUT-C1** `backend/app/models/user.py:29,36` — `reset_token` and `verification_token` stored as plaintext. Hash with SHA256 before storage (same pattern as refresh tokens). *(Supersedes deferred item "Plaintext reset/verification token storage".)*
- [x] **DF-AUT-C2** `backend/app/services/user/tokens.py:65-95` — Refresh token not rotated after use. Same token can be replayed indefinitely until expiry. Invalidate the old token and issue a new one on every refresh.

##### Major

- [x] **DF-AUT-M1** `backend/app/dependencies/auth.py:23-82` — `get_current_user` checks `is_active` but not `is_verified`. When `EMAIL_VERIFICATION_REQUIRED=True`, unverified users can access all protected resources. Add `is_verified` check when the setting is enabled.
- [x] **DF-AUT-M2** `frontend/src/auth/authStorage.ts` — Access token migrated from `localStorage` to in-memory module variable. Refresh token was already in an httpOnly cookie; AuthContext now auto-restores session on mount via the refresh cookie. Cross-tab localStorage lock replaced with in-memory Promise coalescing.
- [x] **DF-AUT-M3** `backend/app/services/user/account.py` — Added `token_version` column to `User`; embedded as `tv` claim in access tokens; `get_current_user` rejects tokens whose `tv` mismatches DB value; `delete_user` and `deactivate_user` increment `token_version`. Migration 012.
- [x] **DF-AUT-M4** `frontend/src/api/client.tsx:243-315` — Cross-tab refresh lock uses a 10-second timeout; stale lock allows concurrent refresh requests. Server-side rotation (C2 above) eliminates the replay risk; also replace the localStorage busy-poll with a `StorageEvent` listener.
- [x] **DF-AUT-M5** `backend/app/api/admin.py` + `admin_service.py` — Removed duplicate `require_superuser`; all admin endpoints now use `get_current_active_superuser` (live DB check). `update_user` increments `token_version` when `is_superuser` or `is_active` changes to immediately invalidate outstanding tokens.
- [x] **DF-AUT-M6** `frontend/src/api/client.tsx:317-321` — On 401 after failed refresh, unconditional `window.location.href = "/account"` redirect can loop if `AccountView` itself triggers auth. Guard with a check that the current path is not already `/account`.

---

#### SEARCH

##### Critical

- [x] **DF-SCH-C1** `backend/app/api/search.py:25-29,78-82` — Neither `POST /search` nor `POST /search/suggestions` declares an auth dependency. The entire knowledge graph is readable by unauthenticated HTTP requests. Add `get_current_user` dependency to both handlers.
- [x] **DF-SCH-C2** `backend/app/services/search_service.py:121-188` — Suggestions query filters on `is_current` but not `status == "confirmed"`. Draft revisions (LLM-created, pending review) are exposed to unauthenticated callers via autocomplete. Add `status == "confirmed"` filter.

##### Major

- [x] **DF-SCH-M1** `entity_search.py:23`, `source_search.py:19`, `relation_search.py:20` — Main search queries filter on `is_current` only, not `status`. Draft entities, sources, and relations appear in authenticated search results. Add `status == "confirmed"` filter to all three sub-searchers.
- [x] **DF-SCH-M2** `backend/app/services/search_service.py:76-78` + `common.py:55-56` — DB-level `limit`/`offset` is applied per type, then a second in-memory slice is applied to the merged list. Cross-type pagination is unsound: page 2 returns the wrong items. Remove the second slice or fetch all matches before paginating once.
- [x] **DF-SCH-M3** `backend/app/services/search/relation_search.py:39-44` — `map_row` issues a separate `SELECT` per relation result row to fetch `entity_ids`. N+1 queries. Batch-load role revisions with `WHERE relation_revision_id IN (...)` after collecting all IDs.
- [x] **DF-SCH-M4** `frontend/src/views/SearchView.tsx:91-93,104-107` — No debounce and no `AbortController`: a new request fires on every keystroke; the last response wins regardless of order, producing stale results. Add 300ms debounce and cancel in-flight requests.
- [x] **DF-SCH-M5** `backend/app/schemas/search.py:43` — `source_kind` is `Optional[List[str]]` with no enum validation. Unknown values silently return zero results. Change to a `SourceKind` literal/enum.

##### Minor

- [x] **DF-SCH-m1** `backend/app/services/search/common.py:17-21` — All queries use `ILIKE`/`LIKE`, no trigram or full-text index exists. The docstring claims "PostgreSQL full-text search" — this is false. Add `pg_trgm` GIN indexes on searched columns.
- [x] **DF-SCH-m2** `frontend/src/views/SearchView.tsx:123-124` — Entity links use `result.id` (UUID); verify the entity detail route accepts UUID not slug, or change to `result.slug`. *(Verified: `GET /entities/{entity_id}` accepts UUID; `result.id` is correct — no code change needed.)*

---

#### EXTRACTION REVIEW

##### Critical

- [x] **DF-RVW-C1** `backend/app/api/extraction_review.py:145-150,196-201` — Single and batch review endpoints use `get_current_user`, not `get_current_active_superuser`. Any authenticated user can approve/reject knowledge graph extractions. Add superuser guard.
- [x] **DF-RVW-C2** `backend/app/services/extraction_review/materialization.py:27-39,54-66,116-130` — `created_by_user_id` on `EntityRevision`/`RelationRevision` is never populated during materialization. All LLM-extracted items lack human attribution. Pass `reviewed_by` through to `create_new_revision()`.
- [x] **DF-RVW-C3** `backend/app/services/extraction_review/auto_commit.py:84-86` — Auto-approved extractions do not set `reviewed_by`; field remains NULL. Added `auto_approved: bool` column (migration 011) set to `True` in `_materialize_approved`; exposed in schema and filters.
- [x] **DF-RVW-C4** `frontend/src/hooks/useReviewDialog.ts:79-109` — `submitBatchReview()` does not inspect `response.failed`. Shows a single success message even when half the batch failed silently. Inspect `failed > 0` and show a detailed warning.

##### Major

- [x] **DF-RVW-M1** `backend/app/models/staged_extraction.py:12,38` — Rejecting a staged extraction only sets `status = "rejected"`; materialized entities/relations remain fully visible in the knowledge graph. Fixed: added `is_rejected` boolean flag (migration 014) to `entities` and `relations` base tables; `reject_extraction()` sets it; filtered from list/search/export queries; accessible by direct ID for audit.
- [x] **DF-RVW-M2** `backend/app/services/extraction_review_service.py:175` vs `222` — `approve_extraction()` only accepts `PENDING`; `reject_extraction()` accepts `PENDING` and `AUTO_VERIFIED`. Asymmetry prevents re-approval of auto-verified items. Fixed: both guards now use `{PENDING, AUTO_VERIFIED}` reviewable set.
- [x] **DF-RVW-M3** No mechanism to distinguish auto-approved items from human-reviewed items in queries or the UI. Fixed: see DF-RVW-C3 above.

---

#### REVISION REVIEW (Draft Confirm/Discard)

##### Critical

- [x] **DF-DRV-C1** `backend/app/services/revision_review_service.py:121-142` — `confirm()` sets `status = "confirmed"` but never touches `is_current`. If a prior confirmed revision exists with `is_current=True`, two revisions end up with `is_current=True`, violating the single-current-revision invariant. Fix: set confirmed revision to `is_current=True` and flip all sibling revisions to `is_current=False`.
- [x] **DF-DRV-C2** `backend/app/services/revision_review_service.py:124-162` — Regression: revision models now have `confirmed_by_user_id` / `confirmed_at`, but `confirm()` still never populates them, so draft confirmations are not auditable. Pass reviewer identity into `confirm()` and set both fields during confirmation.
- [x] **DF-DRV-C3** No DB constraint prevents multiple draft revisions for the same entity/source/relation. Add a partial unique index `UNIQUE (entity_id, status) WHERE status='draft'` (and equivalents) to enforce single-draft-per-parent.
- [x] **DF-DRV-C4** `backend/app/services/revision_review_service.py:121-142` — Two concurrent admin confirms of the same draft both succeed (no locking). Use `SELECT FOR UPDATE` or an atomic `UPDATE ... WHERE status='draft'` with rows-affected check.

##### Major

- [x] **DF-DRV-M1** `backend/app/api/revision_review.py:61-108` — All four revision-review endpoints use `get_current_user`, not `get_current_active_superuser`. Any authenticated user can confirm or discard LLM drafts. Add superuser guard.
- [x] **DF-DRV-M2** `backend/app/services/revision_review_service.py:62-115` — `_list_*_drafts()` methods filter on `status == "draft"` but not `is_current == True`. Non-current drafts appear in the review queue. Add `is_current=True` filter or document the intent.
- [x] **DF-DRV-M3** `frontend/src/components/review/LlmDraftsPanel.tsx:73-97` — After confirm/discard, `load()` is called unconditionally. On slow networks, if `load()` fails, the success message is contradicted by an error. Optimistically remove the item on API success; show refresh failure separately.

---

#### EXTRACTION PIPELINE

##### Critical

- [x] **DF-EXT-C1** `backend/app/schemas/source.py:126-137` vs `frontend/src/types/extraction.ts:121-129` — `DocumentExtractionPreview` backend schema includes `needs_review_count`, `auto_verified_count`, and `avg_validation_score`; frontend type omits all three. Add missing fields to the TypeScript interface.

##### Major

- [x] **DF-EXT-M1** `backend/app/services/extraction_review/materialization.py:78-84` — When an entity referenced in an extracted role cannot be found, the code logs a warning and silently creates the relation without that role. Relation is returned as successfully materialized. Treat missing entity references as a fatal error or return a structured failure result.
- [x] **DF-EXT-M2** `backend/app/services/extraction_review/staging.py:54-69` — Auto-materialization path: `db.flush()` succeeds for each materialization call but a final `db.commit()` failure leaves the in-memory `staged` object in a different state than the DB. Wrap all materializations in explicit transaction with rollback on any failure.
- [x] **DF-EXT-M3** `backend/app/services/document_extraction_processing.py:419-446` — No explicit transaction boundary wraps the full extraction pipeline (`run_validated_extraction` → `stage_review_batch` → `build_link_suggestions`). A mid-pipeline crash orphans `StagedExtraction` records. Wrap the full preview-build operation in a single `async with db.begin()`.
- [x] **DF-EXT-M4** `backend/app/api/document_extraction_routes/document.py:114-153` — If `build_extraction_preview()` fails after `store_document_in_source()` succeeds, the document is persisted but the extraction returns an error. Clean up the stored document on extraction failure (or defer storage until after successful extraction).
- [x] **DF-EXT-M5** `backend/app/services/batch_extraction_orchestrator.py:202-214` — Parallel filtering operations on `entities`/`entity_results` arrays may lose index alignment when both arrays are filtered independently. Use a unified list-of-tuples structure throughout the pipeline.
- [x] **DF-EXT-M6** `backend/app/services/batch_extraction_orchestrator.py:223-249` — Semantic validation of LLM output is absent: relation `entity_slug` values are not checked against the extracted entity list; text spans are not verified against source text. Add cross-field semantic validation after schema validation.
- [x] **DF-EXT-M7** `backend/app/api/extraction.py:248-258` — Status endpoint hardcodes `provider="OpenAI"` regardless of actual configured LLM provider. Query the actual provider from `get_llm_provider()`.

---

#### INFERENCES / COMPUTED RELATIONS

##### Critical

- [x] **DF-INF-C1** `backend/app/services/explanation_read_models.py:23-29` — `build_contradiction_detail()` returns a `ContradictionDetail` with empty source lists, expecting `attach_contradiction_sources()` to fill them. If `attach_contradiction_sources()` returns `None` (because only one direction is present), the contradiction detail is discarded entirely. Frontend shows "Disagreement: 45%" with no contradiction section. Fix: report contradictions whenever `disagreement > threshold`, even when only one direction is represented.
- [x] **DF-INF-C2** `backend/app/services/explanation_read_models.py:33-49` — Contradiction logic requires both supporting and contradicting sources to be non-empty. This is backwards: the disagreement metric can be >0 with unidirectional evidence (internal magnitude cancellation). Decouple contradiction visibility from bidirectional-source requirement.
- [x] **DF-INF-C3** `backend/app/services/inference/read_models.py:299-309` — Inference cache stores a global average disagreement in `ComputedRelation.uncertainty` but per-role disagreement values differ. When cached inferences are read back, all roles receive the same (incorrect) disagreement value. Store per-role disagreement in `RelationRoleRevision.disagreement`.

##### Major

- [x] **DF-INF-M1** `backend/app/services/inference/read_models.py:212-216` — Cached confidence is stored as `1.0` globally, while live inferences compute accurate per-role confidence. Store per-role confidence in `RelationRoleRevision` to keep cached and live inferences consistent.
- [x] **DF-INF-M2** `backend/app/services/relation_service.py` — Inference cache is invalidated on relation create/update but not on source update (trust_level change). Add cache invalidation for all entities linked to a source when that source is updated.
- [x] **DF-INF-M3** `backend/app/services/inference/detail_views.py:82` — `zip(source_ids, results, strict=False)` silently accepts mismatched lengths. A failed source fetch drops source metadata without warning. Change to `strict=True` and handle the resulting ValueError explicitly.
- [x] **DF-INF-M4** `frontend/src/views/InferencesView.tsx:206-234` — Inferences fetched in a loop read `items.length` from stale closure for index calculation; concurrent async updates can assign inferences to wrong positions. Use functional state updates with explicit index tracking.
- [x] **DF-INF-M5** `backend/app/services/inference/evidence_views.py:33-47` — `if role.weight:` treats explicit `0.0` as absent, falling back to relation direction. A role weight of 0 (neutral contribution) should be distinct from unset. Check `role.weight is not None` instead.

##### Minor

- [x] **DF-INF-m1** `backend/app/schemas/inference.py:14` — `score: Optional[float]` has no bounds constraint. Add `Field(..., ge=-1.0, le=1.0)` to catch out-of-range math errors before they reach the frontend.
- [x] **DF-INF-m2** `backend/app/repositories/inference_repo.py` — `InferenceRepository` class is never instantiated; cache is managed by `ComputedRelationRepository`. Remove dead class to avoid confusion.

---

#### ENTITY MERGE

##### Critical

- [x] **DF-MRG-C1** `backend/app/services/entity_merge_service.py` — No check prevents circular merges (A→B then B→A). Validate against `EntityMergeRecord` before proceeding: reject if either entity appears as a `source_entity_id` in any existing record.
- [x] **DF-MRG-C2** `backend/app/repositories/relation_repo.py:37-61` — `list_by_entity()` does not filter `RelationRevision.is_current == True`. After merge, stale role revisions from the deactivated entity's old revisions can pollute inference calculations. Add `is_current=True` filter to the join.
- [x] **DF-MRG-C3** `backend/app/services/entity_merge_service.py` — After merge, the source entity's revisions have `is_current=False` but the Entity row itself is not flagged. Direct entity queries can encounter an entity with no current revision in an ambiguous state. Add an `is_merged` flag (or `merged_into_entity_id` FK) to the `Entity` model and filter merged entities out of standard queries.

##### Major

- [x] **DF-MRG-M1** `backend/app/services/entity_merge_service.py` — No `source_entity_id != target_entity_id` guard. Self-merge partially succeeds and corrupts the entity. Add explicit validation before any DB operations.
- [x] **DF-MRG-M2** `backend/app/services/entity_merge_service.py` — After merge, `ComputedRelation` cache entries for the target entity are not invalidated. Subsequent inference reads return stale data. Delete cached computed relations for the target entity on merge.
- [x] **DF-MRG-M3** `backend/app/services/entity_merge_service.py:139-146` — The count query for `relations_moved` counts roles from all revisions, but the move operation only moves current-revision roles. `EntityMergeResult.relations_moved` is inflated. Add `is_current=True` filter to the count query.

---

#### RELATIONS

##### Critical

- [x] **DF-REL-C1** `backend/app/schemas/relation.py:16-20` + `backend/app/mappers/relation_mapper.py:55-67` — `RelationRoleRevision.disagreement` field exists in the DB model but is absent from `RoleRevisionRead` schema and mapper. Computed disagreement is silently dropped on every relation read. Add field to schema and mapper.
- [x] **DF-REL-C2** `backend/app/repositories/relation_repo.py:16-19` — `get_by_id()` does not eagerly load `revisions` or `roles`. Accessing these on the returned object triggers N+1 queries or a `lazy="raise"` error. Add `selectinload(Relation.revisions).selectinload(RelationRevision.roles)` to the query.

##### Major

- [x] **DF-REL-M1** `backend/app/services/validation_service.py:27-28` vs `backend/app/schemas/relation.py:32` — Schema marks `confidence` as `Optional[float] = None` but the validator rejects null confidence. Either make confidence required in the schema or remove the null check in the validator.
- [x] **DF-REL-M2** `backend/app/api/relation_types.py:26-27,39` — `active_only: bool = True` query parameter is declared but never used; the service always returns active types. Either wire the parameter or remove it.
- [x] **DF-REL-M3** `backend/app/models/relation_type.py:32` vs `backend/app/schemas/relation_type.py:13` — `description` is mapped as `JSON` in the model but expected as `str` in the schema. Standardize to `String` in the model.
- [x] **DF-REL-M4** `frontend/src/types/relation.ts:13` — `entity_id?: string` field exists in the frontend `RelationRead` type but is not sent by the backend schema. Remove the orphaned field or add it to the backend if needed.
- [x] **DF-REL-M5** `frontend/src/types/relation.ts:9-21` — `created_by_user_id` is present in backend `RelationRevisionRead` but absent from the frontend type. Add `created_by_user_id?: string | null`.

---

#### SOURCES

##### Critical

- [x] **DF-SRC-C1** `backend/app/schemas/source.py:86-101` vs `frontend/src/api/sources.ts:41-52` — `SourceMetadataSuggestion.summary` is `Optional[I18nText]` (nested dict) on the backend but the frontend type declares flat `summary_en?: string | null` and `summary_fr?: string | null`. Metadata autofill will fail to populate summary fields after URL extraction. Align frontend type to `summary?: Record<string, string>` and update the form mapping.

##### Major

- [x] **DF-SRC-M1** `backend/app/schemas/source.py:56-75` + `backend/app/mappers/source_mapper.py` — `SourceRead` does not expose `document_format`, `document_file_name`, or `document_extracted_at` from `SourceRevision`. Frontend cannot show whether a document is attached or its format. Add optional document fields to `SourceRead` and update mapper.
- [x] **DF-SRC-M2** `backend/app/schemas/source.py:56-75` — `SourceRead` omits `created_with_llm` and `created_by_user_id`. Provenance is invisible to frontend consumers. Add optional fields and update mapper.
- [x] **DF-SRC-M3** `backend/app/mappers/source_mapper.py:66-80` — Fallback branch accesses deprecated flat fields (`kind`, `title`, etc.) directly on `Source`; these fields no longer exist in the dual-table architecture. Remove the fallback or add `hasattr()` guards to prevent `AttributeError`.
- [x] **DF-SRC-M4** `frontend/src/views/CreateSourceView.tsx:28-37` + `EditSourceView.tsx:25-34` — Source kinds are hardcoded arrays. Changes to allowed kinds in the DB are not reflected. Use `filterOptions?.kinds` from the cache, falling back to the hardcoded list.

---

#### ENTITIES

##### Critical

- [x] **DF-ENT-C1** `backend/app/schemas/entity.py:34-51` — `EntityRead` does not expose `created_by_user_id` from `EntityRevision`. Audit chain of custody is invisible at the API level. Add `created_by_user_id: Optional[UUID] = None` and populate in `entity_mapper.py`.
- [x] **DF-ENT-C2** `backend/app/models/entity.py` — No `terms` relationship defined on `Entity`. `EntityTerm` references `entity_id` but the reverse relationship is missing, breaking cascades and making term loading require separate queries. Add `terms = relationship("EntityTerm", back_populates="entity", cascade="all, delete-orphan", lazy="raise")`.
- [x] **DF-ENT-C3** `backend/app/models/entity_term.py:32` — `entity = relationship("Entity")` has no `back_populates`. Change to `back_populates="terms"`.

##### Major

- [x] **DF-ENT-M1** `backend/app/services/entity_service.py:254-295` — `get_filter_options()` executes multiple separate queries sequentially and can return `clinical_effects = None`. Batch aggregation queries with `asyncio.gather()`; return empty list instead of `None` for missing aggregations.
- [x] **DF-ENT-M2** `frontend/src/views/EntitiesView.tsx:46-79` — `filterOptions?.clinical_effects.map(...)` will throw if `clinical_effects` is null. Add null coalescing: `filterOptions?.clinical_effects?.map(...) ?? []`.
- [x] **DF-ENT-M3** `frontend/src/views/EntitiesView.tsx` + `EntityDetailView.tsx` — The `status` field (`draft`/`confirmed`) is sent by the backend but never displayed or filtered. LLM-created draft entities are indistinguishable from confirmed ones. Add a status badge to list items and detail view; add a draft filter.

##### Minor

- [x] **DF-ENT-m1** `backend/app/services/entity_query_builder.py:154-212` — Recency filter uses INNER JOIN with a year subquery; entities whose sources have `NULL` year are excluded. Use `COALESCE` or OUTER JOIN to handle unknown years.
- [x] **DF-ENT-m2** `frontend/src/hooks/useEntityData.ts:23-76` — No `AbortController` on the fetch; unmounting during a request leaves a dangling promise. Add cleanup to cancel in-flight requests on unmount.

---

#### SMART DISCOVERY / PUBMED

##### Critical

- [x] **DF-DSC-C1** `backend/app/services/document_extraction_discovery.py:166-219` — `bulk_import_pubmed_articles()` has no PMID duplicate detection. The same PubMed article can be imported multiple times, creating duplicate Source records. Call `_find_existing_pmids()` before the import loop and skip already-imported PMIDs.
- [x] **DF-DSC-C2** `backend/app/api/document_extraction_routes/discovery.py:41-154` — Discovery and bulk-import endpoints have no rate limiting. An authenticated user can exhaust NCBI API quota or flood the DB with parallel bulk imports. Add `@limiter.limit("5/minute")` (or equivalent) to all three endpoints.

##### Major

- [x] **DF-DSC-M1** `backend/app/services/document_extraction_discovery.py:98-114` — Sources imported from PubMed store no `imported_at` timestamp or `discovery_query` provenance in metadata. Extend `source_metadata` with `imported_at`, `import_method`, and optionally `discovery_query`.
- [x] **DF-DSC-M2** `backend/app/services/document_extraction_discovery.py:320-325` — `trust_level` is LLM-inferred and stored directly as the canonical source trust level without any human review. Store it in a separate `calculated_trust_level` field and leave `trust_level` NULL pending user confirmation, or add a review step before bulk-import commit.
- [x] **DF-DSC-M3** `frontend/src/views/PubMedImportView.tsx` — Added `AbortController` for both search and import requests; Cancel buttons shown during in-flight operations; `AbortError` caught silently.
- [x] **DF-DSC-M4** `frontend/src/types/pubmed.ts:32-37` + `frontend/src/api/smart-discovery.ts:48-53` — Bulk import response type is declared twice with identical shapes. Remove the duplicate from `smart-discovery.ts` and import from `pubmed.ts`.

---

#### EXPORT / IMPORT

##### Critical

- [x] **DF-EXP-C1** `backend/app/services/export_service.py:39-77,162-222,312-369` — Export omits the `status` field (`draft`/`confirmed`) from entity, source, and relation revisions. On re-import, all records default to `confirmed`, bypassing review workflow for LLM-created drafts. Add `status` to all exported dicts.
- [x] **DF-EXP-C2** `backend/app/services/export_service.py:62-77,183-222,353-368` — Revision `created_at` is never exported (only base `entity.created_at`); relation `created_by_user_id` is not exported at all. Add both fields to preserve audit trail on round-trip.
- [x] **DF-EXP-C3** `backend/app/api/import_routes.py:34-61` — No file size limit on `UploadFile`. A multi-GB upload is read entirely into memory before validation. Add a size check (e.g., 10 MB cap) before `file.file.read()`.

##### Major

- [x] **DF-EXP-M1** `backend/app/services/export_service.py:63-67` vs `import_service.py:264-267` — JSON export serializes `summary` as `{"en": "...", "fr": "..."}` but JSON import expects flat `summary_en`/`summary_fr` keys. Round-trip import silently loses all summaries. Flatten summary in JSON export to match import expectations.
- [x] **DF-EXP-M2** `backend/app/schemas/import_schema.py` — `SourceImportRow` has no `trust_level` field; imported sources always get `trust_level=None`. Add `trust_level: float | None = None` and pass it through in `import_sources()`.
- [x] **DF-EXP-M3** `backend/app/services/export_service.py:258-273` — CSV export assumes exactly 2 roles (subject/object) per relation. N-ary relations lose extra roles silently. Store all roles as a JSON array in an additional column.
- [x] **DF-EXP-M4** `frontend/src/views/ImportEntitiesView.tsx` + `ImportSourcesView.tsx` — No file size validation in the UI; no progress indicator; no cancel mechanism for large imports. Add client-side size check, progress bar, and abort capability.
- [x] **DF-EXP-M5** `backend/app/services/export_service.py:144,298` — RDF/Turtle export does not escape quotes in string literals. Exported files fail to parse in RDF tools. Apply proper Turtle string escaping.

---

### Full System Audit — 2026-03-23 (score 95/100)

Source: `.temp/full_audit_report_2026-03-23.md`

#### Major

- [x] **AUD-M2** `backend/app/services/bulk_creation_service.py:83` + revision tables — Once materialized, LLM-generated revisions are structurally indistinguishable from human-authored ones. Added `llm_review_status: str | None` (nullable for human-authored rows; `"pending_review"` on creation, `"auto_verified"` from auto-commit, `"confirmed"` on human confirm) to all three revision models. Migration 013. Populated in `bulk_creation_service`, `materialization.py`, `auto_commit._materialize_approved`, and `revision_review_service.confirm`. Exposed in all read schemas, mappers, `DraftRevisionRead`, and export service.

#### Minor

- [x] **AUD-m1** `backend/app/services/export_service.py` — Dropped legacy `subject_slug`/`object_slug` CSV columns (always empty for N-ary roles); `roles_json` is the sole roles column. Fixed mismatched empty-result fallback header.

---

### E2E Test Suite — Soundness and Coverage (2026-03-22)

Review identified systemic correctness problems and coverage gaps across the full E2E suite.
Source: E2E review session 2026-03-22.

#### Critical — false-positive tests (no failure mode)

- [x] **E2E-C1** `inferences/viewing.spec.ts:62-63` — "should navigate to inferences page" asserts `expect(url).toBeTruthy()`. Replace with `toHaveURL(/\/inferences/)` or a heading assertion.
- [x] **E2E-C2** `inferences/viewing.spec.ts:71-78` — "should filter inferences" has zero assertions. Add at minimum an assertion that the page still renders after attempting a filter interaction.
- [x] **E2E-C3** `explanations/trace.spec.ts:57-58` — "should display explanation trace" calls `.isVisible().catch(() => false)` with no `expect()`. Always passes. Add a real assertion or remove the test.
- [x] **E2E-C4** `auth/login.spec.ts:117-121` — "should redirect to account page when accessing protected route without auth" — `url.includes('account')` is always true after redirect; tautological. Assert login form visibility without the URL fallback.
- [x] **E2E-C5** `auth/register.spec.ts:55-62` — "should show error when registering with invalid email" only checks the URL. Add an assertion that a validation error message is visible.
- [x] **E2E-C6** Eliminate pervasive conditional-test anti-pattern — `if (await x.isVisible()) { await expect(x).toBeVisible() }` throughout `entities/filters.spec.ts`, `sources/filters.spec.ts`, `relations/export.spec.ts`, `sources/export.spec.ts`, `relations/batch.spec.ts`, `review-queue/queue.spec.ts`. Each of these silently passes when the feature is absent. Replace with direct assertions backed by API-seeded preconditions.

#### Critical — structural defects

- [x] **E2E-C7** `relations/edit-delete.spec.ts` — if API relation creation fails in `beforeEach`, `relationId` is `''` and all tests skip silently. Replace silent skip with a thrown error so broken setup is visible.
- [x] **E2E-C8** `relations/crud.spec.ts:138-156` — "should remove roles from relation" iterates all buttons looking for those with no text/aria-label to find a delete button. This is fragile and documents an accessibility defect. Add `aria-label="Remove role"` to delete IconButtons in the relation form, then update the test to use `getByRole('button', { name: /remove role/i })`.

#### Major — weak or misleading assertions

- [x] **E2E-M1** `auth/register.spec.ts:64-81` — weak-password test matches the Zod internal key `string_too_short`. Require a user-facing message instead (e.g. "at least 8 characters").
- [x] **E2E-M2** `auth/login.spec.ts:55-64` — "should show error with empty credentials" only checks the URL. Assert that the login button is still visible and no auth token was set.
- [x] **E2E-M3** `relations/edit-delete.spec.ts:98-118` — test is titled "should save a relation update and create a new revision" but never verifies a new revision exists. Add an API call or UI check that confirms revision count increased.
- [x] **E2E-M4** `account/settings.spec.ts:84-129` — "should successfully change password for a test user" silently returns (passes) if the newly registered user cannot log in due to email verification requirements. Add an explicit skip or assertion that makes the precondition failure visible.
- [x] **E2E-M5** `inferences/viewing.spec.ts:16-54` — "should view inferences on entity detail page" creates two entities but no relation, so inference computation is never triggered. Add an API-seeded relation between the entities before navigating to the detail page.
- [x] **E2E-M6** `entities/crud.spec.ts:113-114` — `waitForTimeout(1000)` before delete click. Replace with `waitForLoadState('networkidle')` or a condition on a specific element.
- [x] **E2E-M7** `sources/crud.spec.ts:114-117` — delete confirmation `getByRole('button', { name: /confirm|yes|delete/i })` is unscoped and could match the wrong button. Scope to `locator('[role="dialog"]')` as `entities/crud.spec.ts` correctly does.
- [x] **E2E-M8** `entities/crud.spec.ts` — missing `afterEach` with `clearAuthState`. Add it for consistency with all other suites.
- [x] **E2E-M9** `relations/batch.spec.ts:59` — source creation in the batch test fills `summary.*english` which is inside a collapsed "Advanced" section. Remove that fill (title + URL are sufficient, per `sources/crud.spec.ts`).
- [x] **E2E-M10** `document-upload.spec.ts:64-81` — 60-second LLM-dependent assertion. Either mock the extraction API response or mark the test as requiring LLM availability and move it to a separate slow suite.
- [x] **E2E-M11** `relations/crud.spec.ts` — heavy `beforeEach` creates source + 2 entities for every test including ones that don't need them (e.g. "should view relations list"). Move resource creation to only the tests that require it, or use a `beforeAll` with API calls.

#### Coverage gaps — missing tests

- [x] **E2E-G1** **Token refresh flow** — no test exercises `refresh_token`. Add a test that sets an expired `auth_token` (or clears it while keeping `refresh_token`) and verifies the app silently re-authenticates.
- [x] **E2E-G2** **Contradiction visibility** — core HyphaGraph invariant has zero E2E coverage. Add a test: create two relations with contradictory claims for the same entity+role, navigate to the entity detail or disagreements page, and assert both are visible and neither is suppressed.
- [x] **E2E-G3** **Entity and relation revision history** — edits are tested at the UI level but no test verifies a new revision was persisted. Add post-edit API checks or UI assertions that show a revision history entry was created.
- [x] **E2E-G4** **Disagreements with real contradictory data** — all `disagreements/viewing.spec.ts` tests create fresh entities with no relations; only the empty-state path is exercised. Add a test with API-seeded contradictory relations that asserts actual disagreement groups are displayed.
- [x] **E2E-G5** **Non-admin frontend authorization** — `admin/panel.spec.ts` tests the API 403 but no test verifies what a regular-user session sees when accessing admin-restricted UI surfaces.
- [x] **E2E-G6** **Pagination correctness** — existing pagination tests only click "next" if visible; no test asserts that page 2 data differs from page 1.
- [x] **E2E-G7** **Export content correctness** — export tests confirm a download event fires and the filename extension is correct; no test validates the file's actual contents.
- [x] **E2E-G8** **Email verification flow** — registration tests acknowledge verification may be required but no test exercises the verification link or confirms the post-verification login state.
- [x] **E2E-G9** **Unknown ID 404 handling** — no test navigates to `/entities/00000000-0000-0000-0000-000000000000` or a similar non-existent ID and asserts a user-facing not-found state.

#### Minor / docs inconsistency

- [x] **E2E-m1** `playwright.config.ts` — comment says "English only (no i18n testing)" but `i18n/language-switch.spec.ts` exists and runs. Update the comment.
- [x] **E2E-m2** `playwright.config.ts` — Firefox and WebKit projects are commented out; `E2E_TESTING_GUIDE.md` lists all three browsers as active. Either enable them or update the guide.
- [x] **E2E-m3** `auth/register.spec.ts:83-106` — "should allow login after successful registration" uses `expect(loggedIn || needsVerification).toBeTruthy()`. The `needsVerification` text could match unrelated page content. Tighten the locator or split into two tests for the verified and unverified paths.

---

## Deferred Items

From completed audits — low priority, no blocking risk.

- **Plaintext reset/verification token storage** — elevated to DF-AUT-C1 above; no longer deferred.

---

## Post-v1.0 Backlog

- **Graph visualization** — Explicitly not MVP.
- **TypeDB integration** — Optional reasoning engine.
- **Advanced auth** — 2FA (TOTP), OAuth providers (Google, GitHub).
- **Real-time collaboration** — WebSocket/SSE for live updates.
- **Multi-tenancy / RBAC** — Organization model, role-based access control.

---

## Audit Reports Index

- `.temp/full_audit_report_2026-03-23.md` *(current — score 95/100, 1 major, 2 minor open)*

- `.temp/audit_entity_write_flow_2026-03-22.md`
- `.temp/audit_entity_creation_2026-03-22.md`
- `.temp/audit_relation_creation_2026-03-22.md`
- `.temp/audit_llm_integration_2026-03-22.md`
- `.temp/audit_relation_extraction_2026-03-22.md`
- `.temp/audit_login_2026-03-22.md`
- `.temp/audit_payload_flows_2026-03-21.md`
- `.temp/full_audit_report_2026-03-21b.md`
- `.temp/full_audit_report_2026-03-21_prev.md`
- `.temp/audit_inference_pipeline_2026-03-21.md`
- `.temp/audit_smart_discovery_2026-03-22.md`
- `.temp/audit_orm_2026-03-22.md`
- `.temp/audit_database_operations_2026-03-22.md`
- `.temp/audit_smart_discovery_2026-03-20.md`
- `.temp/full_audit_report_2026-03-18.md`
- `.temp/knowledge_integrity_report_v1.md`
- `.temp/revision_architecture_provenance_report_v1.md`
- `.temp/security_authentication_report_v2.md`
- `.temp/api_service_boundary_report_v2.md`
- `.temp/dead_code_compatibility_shims_report_v2.md`
- `.temp/typed_contract_discipline_report_v3.md`
- `.temp/test_suite_health_report_v2.md`
- `.temp/audit_dataflow_entities_2026-03-23.md` *(agent output)*
- `.temp/audit_dataflow_sources_2026-03-23.md`
- `.temp/audit_dataflow_relations_2026-03-23.md`
- `.temp/audit_dataflow_inferences_2026-03-23.md`
- `.temp/audit_dataflow_extraction_2026-03-23.md`
- `.temp/audit_dataflow_extraction_review_2026-03-23.md`
- `.temp/audit_dataflow_revision_review_2026-03-23.md`
- `.temp/audit_dataflow_search_2026-03-23.md`
- `.temp/audit_dataflow_auth_2026-03-23.md`
- `.temp/audit_dataflow_smart_discovery_2026-03-23.md`
- `.temp/audit_dataflow_entity_merge_2026-03-23.md`
- `.temp/audit_dataflow_export_import_2026-03-23.md`
