# Current Work

**Last updated**: 2026-03-14

## In Progress

- Rule-based maintainability follow-up for the remaining validation-presentation consistency and residual backend boundary cleanup.

## Completed In This Pass

### Refactor Completed: Shared Document Extraction Workflow

File: `backend/app/api/document_extraction.py`, `backend/app/services/document_extraction_workflow.py`

Problem:
Stored-document extraction, upload-and-extract, URL extraction, and part of PubMed import all repeated the same extraction-preview orchestration, staging, linking, source persistence, and save-to-graph flow.

Why it was problematic:
The transport layer was carrying workflow logic directly, which made the main path hard to review and forced maintenance changes to be repeated across multiple endpoints.

Implemented fix:
Moved the shared extraction-preview, review staging, source-document persistence, URL fetch preparation, save-to-graph, and PubMed source-creation logic into a dedicated workflow service. The router now delegates the common document/upload/URL flow instead of reimplementing it inline.

### Refactor Completed: PubMed Search and Smart Discovery Workflow Split

File: `backend/app/api/document_extraction.py`, `backend/app/services/document_extraction_workflow.py`

Problem:
Adaptive PubMed search, duplicate detection, entity query construction, quality filtering, bulk search orchestration, and bulk import decisions were still implemented directly inside the API router.

Why it was problematic:
The router still owned the core workflow logic for discovery and import, which kept transport and application concerns mixed and made the code hard to review end-to-end.

Implemented fix:
Moved smart-discovery orchestration, PubMed bulk search, PubMed bulk import, query-clause building, relevance scoring, and PMID deduplication helpers into the workflow service. The router now mainly performs request validation, dependency wiring, and response shaping.

### Refactor Completed: Extraction Router Split by Route Family

File: `backend/app/api/document_extraction.py`, `backend/app/api/document_extraction_routes/document.py`, `backend/app/api/document_extraction_routes/discovery.py`

Problem:
Even after workflow extraction, the transport layer still exposed every extraction-related route from one oversized API file.

Why it was problematic:
The module remained harder to scan than a transport layer should be, and document/url routes were still mixed with discovery/import routes.

Implemented fix:
Split the API into route-family modules while keeping `app.api.document_extraction` as the shared facade for request models, helper functions, and backward-compatible imports used by tests.

### Refactor Completed: Source Detail View Presentation Split

File: `frontend/src/views/SourceDetailView.tsx`, `frontend/src/components/source-detail/*`

Problem:
The source detail page mixed controller state, metadata rendering, extraction workflow presentation, relations rendering, and confirmation dialogs in one large component.

Why it was problematic:
The top-level page was too dense for quick review, and individual UI sections could not be evolved or tested as separate presentation units.

Implemented fix:
Extracted focused presentational components for source metadata, extraction actions/status, relations rendering, and dialogs. `SourceDetailView.tsx` now mostly coordinates state and actions.

### Refactor Completed: Evidence View Presentation Split

File: `frontend/src/views/EvidenceView.tsx`, `frontend/src/components/evidence/*`, `frontend/src/hooks/useEvidenceRelations.ts`

Problem:
The evidence page mixed relation enrichment, sorting state, header rendering, empty-state handling, and a large evidence table in one module.

Why it was problematic:
The main view hid the page flow inside table/rendering detail and coupled source enrichment too tightly to the page component.

Implemented fix:
Extracted an evidence enrichment hook plus focused header and table components. `EvidenceView.tsx` now primarily coordinates detail loading, sort state, and section composition.

### Refactor Completed: Synthesis View Presentation Split

File: `frontend/src/views/SynthesisView.tsx`, `frontend/src/components/synthesis/*`

Problem:
The synthesis page mixed navigation, statistics, quality indicators, grouped relation accordions, knowledge-gap messaging, and footer actions in one large module.

Why it was problematic:
The top-level page did not read like a high-level synthesis pipeline and each visual section was harder to review in isolation.

Implemented fix:
Extracted focused header, statistics, quality, relations, and footer sections so `SynthesisView.tsx` now mainly computes aggregate metrics and composes the page.

### Refactor Completed: Disagreements View Presentation Split

File: `frontend/src/views/DisagreementsView.tsx`, `frontend/src/components/disagreements/*`

Problem:
The disagreements page mixed navigation, contradiction summary cards, grouped evidence accordions, interpretation guidance, and footer actions in one large module.

Why it was problematic:
The page was harder to scan than the other refactored detail views and still buried the high-level disagreement workflow under rendering detail.

Implemented fix:
Extracted focused header, summary, grouped evidence, and footer/guidance sections so `DisagreementsView.tsx` now mainly derives contradiction groups and composes the page.

### Refactor Completed: Extraction Facade Schema and Test-Helper Cleanup

File: `backend/app/api/document_extraction.py`, `backend/app/api/document_extraction_schemas.py`, `backend/app/api/document_extraction_test_support.py`

Problem:
The extraction facade still owned request/response models and deterministic PubMed test fallback helpers directly, even after the route-family split.

Why it was problematic:
This kept the facade denser than necessary and mixed API-shape definitions with test-support helpers and compatibility exports.

Implemented fix:
Moved extraction request/response models into a dedicated schema module and deterministic PubMed fallback/query helpers into a dedicated support module. The facade now mostly re-exports the public surface and compatibility hooks used by the existing tests.

### Refactor Completed: Extraction Facade Compatibility Surface Reduced

File: `backend/app/api/document_extraction.py`, `backend/app/api/document_extraction_dependencies.py`, `backend/app/api/document_extraction_routes/*`, `backend/tests/test_document_extraction.py`

Problem:
The route-family split was in place, but the extraction facade still carried the practical test surface because route modules depended on facade-owned helpers and the extraction tests still patched `app.api.document_extraction` directly.

Why it was problematic:
That left the boundary partially organized around backward compatibility rather than clear module ownership, and it made the route split less meaningful for maintainers reading or testing the extraction stack.

Implemented fix:
Added a dedicated extraction dependency module for shared route wiring, moved the extraction tests to import and patch the direct route/schema/dependency modules, and reduced `document_extraction.py` to a thinner aggregation layer. The facade now behaves much closer to a true compatibility shim.

### Refactor Completed: Smart Discovery Workflow Split

File: `frontend/src/views/SmartSourceDiscoveryView.tsx`, `frontend/src/hooks/useDiscoveryEntities.ts`, `frontend/src/hooks/useSmartDiscoveryController.ts`, `frontend/src/components/smart-discovery/*`

Problem:
The smart discovery page previously mixed page orchestration, entity loading, selection state, import actions, and result rendering in one view module.

Why it was problematic:
This hid the main workflow inside implementation detail and made the page difficult to scan or test in focused slices.

Implemented fix:
The page now composes dedicated controller hooks and focused presentational components for the header, entity selector, config form, and results section.

### Refactor Completed: Shared Query Serialization

File: `frontend/src/api/queryString.ts`, `frontend/src/api/auth.ts`, `frontend/src/api/entities.ts`, `frontend/src/api/explanations.ts`, `frontend/src/api/extractionReview.ts`, `frontend/src/api/inferences.ts`, `frontend/src/api/search.ts`, `frontend/src/api/sources.ts`

Problem:
Request query and form serialization logic was still duplicated across API clients.

Why it was problematic:
This left transport behavior partially unified and made future request-format changes harder to apply consistently.

Implemented fix:
Added shared search-param builders in `queryString.ts` and migrated the remaining API modules to use those helpers instead of open-coded `URLSearchParams` construction.

### Refactor Completed: Hidden Frontend/Service Dependency Edges Reduced

File: `frontend/src/components/ErrorDetails.tsx`, `backend/app/services/typedb_export_service.py`, `backend/app/services/extraction_service.py`

Problem:
Some modules still relied on runtime `require(...)` or lazy imports to access regular collaborators.

Why it was problematic:
Those hidden edges made the dependency graph harder to read and obscured normal module boundaries.

Implemented fix:
Replaced the frontend runtime `require(...)` with an explicit import and promoted straightforward backend service dependencies to module-level imports where no cycle-breaking workaround was actually needed.

### Refactor Completed: Inference and Explanation Role-Evidence Boundary

File: `backend/app/services/inference/evidence_views.py`, `backend/app/services/inference_service.py`, `backend/app/services/explanation_service.py`, `backend/app/services/explanation_read_models.py`

Problem:
`ExplanationService` was deriving explanation payloads by walking `InferenceRead.relations_by_kind`, so explanation behavior depended on a grouped transport shape instead of a purpose-built evidence view.

Why it was problematic:
This spread domain presentation logic across layers, made explanation generation harder to read, and kept the explanation boundary coupled to an internal grouping format that exists primarily for inference responses.

Implemented fix:
Added a dedicated role-evidence builder that converts filtered relations into explanation-ready evidence views, exposed it through `InferenceService`, and rewired `ExplanationService` to consume that model directly. The service also now supports injected collaborators instead of always constructing concrete dependencies internally.

### Refactor Completed: Explicit Inference and Explanation Service Providers

File: `backend/app/api/inference_dependencies.py`, `backend/app/api/inferences.py`, `backend/app/api/explain.py`

Problem:
The inference and explanation transport layers still instantiated services directly inside route handlers and duplicated the same scope-query parsing logic.

Why it was problematic:
That kept part of the backend service-construction story tied to ad-hoc transport wiring and made the top-level API flow denser than necessary.

Implemented fix:
Added shared dependency providers for inference, source, and explanation services plus a shared scope-filter parser. The inference and explain endpoints now depend on explicit providers instead of constructing services inline, and the scope-query parsing behavior lives in one place.

### Refactor Completed: Explicit Collaborator Wiring for Export and Filter Services

File: `backend/app/services/typedb_export_service.py`, `backend/app/services/entity_service.py`, `backend/app/services/source_service.py`, `backend/app/services/extraction_service.py`

Problem:
Several backend services still instantiated concrete collaborators inside methods for export schema lookup, derived-property filter options, and extraction prompt loading.

Why it was problematic:
That hid part of the dependency graph inside method bodies, made substitution harder in tests, and weakened the readability of the service boundary.

Implemented fix:
Added explicit constructor-level collaborator wiring for TypeDB export lookup services, derived-properties access in entity/source services, and extraction prompt lookup services. Default behavior stays the same, but the high-coupling paths can now be substituted directly in tests and application wiring.

### Refactor Completed: API-Level Service Providers for Export, Entity, and Source Routes

File: `backend/app/api/service_dependencies.py`, `backend/app/api/export.py`, `backend/app/api/entities.py`, `backend/app/api/sources.py`

Problem:
Several API route modules still created business services inline inside handlers, and the source transport layer also constructed document and metadata extraction helpers directly.

Why it was problematic:
That kept transport code denser than necessary and spread service-construction policy across multiple endpoints instead of exposing one clear provider layer.

Implemented fix:
Added a shared API service-dependency module and rewired export, entity, and source routes to depend on explicit providers for business services, document parsing, and metadata extraction. The handlers now read more like transport orchestration instead of object construction.

### Refactor Completed: Provider-Based Wiring for Relation, Entity-Term, and Review Routes

File: `backend/app/api/service_dependencies.py`, `backend/app/api/relations.py`, `backend/app/api/entity_terms.py`, `backend/app/api/relation_types.py`, `backend/app/api/extraction_review.py`, `backend/app/services/document_extraction_workflow.py`

Problem:
Several smaller API modules and the document-extraction workflow still instantiated concrete collaborators inline for relation CRUD, entity-term management, relation-type lookup, extraction-review actions, and source/review materialization helpers.

Why it was problematic:
That left the dependency story inconsistent across the backend and kept workflow/application code less explicit about which collaborators it actually depends on.

Implemented fix:
Extended the shared API provider layer to relation, entity-term, relation-type, and extraction-review services, and added constructor/factory seams to the document-extraction workflow for source services, review services, bulk creation, and extraction orchestration. Defaults remain unchanged, but the wiring is now explicit and substitutable.

### Refactor Completed: Final Transport-Level Provider Cleanup for Search and Document Upload

File: `backend/app/api/service_dependencies.py`, `backend/app/api/search.py`, `backend/app/api/document_extraction_routes/document.py`

Problem:
The backend still had a couple of transport-layer constructor calls left in the search API and the document upload-and-extract route.

Why it was problematic:
These were small instances, but they kept the provider pattern incomplete and left the backend transport layer less uniform than the surrounding refactors.

Implemented fix:
Added a shared search-service provider and reused the existing document-service provider so the remaining transport handlers no longer construct services inline. The provider-based API pattern is now effectively consistent across the main backend route surfaces.

### Refactor Completed: Hidden Import Cleanup in Core Backend Modules

File: `backend/app/api/extraction_review.py`, `backend/app/api/relation_types.py`, `backend/app/services/entity_service.py`, `backend/app/services/source_service.py`

Problem:
Several core backend modules still relied on function-local imports for stable dependencies like `select`, `StagedExtraction`, `UiCategory`, `json`, and `datetime`.

Why it was problematic:
These imports were no longer serving cycle-breaking purposes, so they added noise and made the dependency graph less explicit than it needed to be.

Implemented fix:
Promoted those stable imports to module scope in the core review, relation-type, entity, and source modules. This keeps the import graph easier to scan and narrows the remaining hidden-dependency cases to the smaller modules where cycle or optional-dependency concerns may still exist.

### Refactor Completed: Hidden Import Cleanup in Secondary Backend Modules

File: `backend/app/mappers/entity_mapper.py`, `backend/app/services/relation_type_service.py`, `backend/app/services/metadata_extractors/pubmed_extractor.py`, `backend/app/api/auth.py`

Problem:
Several secondary backend modules still used function-local imports for stable dependencies such as `json`, `datetime`, `ValidationException`, and email helper functions.

Why it was problematic:
These imports were not solving dependency cycles, so they added unnecessary indirection and made the code harder to scan than needed.

Implemented fix:
Promoted the stable imports to module scope in the entity mapper, relation-type service, PubMed metadata extractor, and auth routes. The remaining hidden-import cases are now mostly the optional or cycle-sensitive ones rather than normal application dependencies.

### Refactor Completed: Shared Async Action Error Handling for Remaining Editor and Account Flows

File: `frontend/src/hooks/useAsyncAction.ts`, `frontend/src/views/EditSourceView.tsx`, `frontend/src/views/EditEntityView.tsx`, `frontend/src/views/EditRelationView.tsx`, `frontend/src/views/SettingsView.tsx`, `frontend/src/views/AccountView.tsx`, `frontend/src/views/ResetPasswordView.tsx`

Problem:
Several editor and account screens still repeated the same local `try/catch`, loading-flag, `setError`, and notification plumbing for async form actions.

Why it was problematic:
This duplicated control flow across simple screens, made top-level handlers harder to review, and increased the chance of error behavior drifting between pages.

Implemented fix:
Added a shared `useAsyncAction` hook that centralizes loading-state and page-error handling, then migrated the remaining edit/account/reset flows to it. Their submit handlers now read as short intent-focused workflows instead of error-management scaffolding.

### Refactor Completed: Shared Async Action Handling for Remaining Create and Auth Screens

File: `frontend/src/hooks/useAsyncAction.ts`, `frontend/src/views/CreateSourceView.tsx`, `frontend/src/views/CreateEntityView.tsx`, `frontend/src/views/CreateRelationView.tsx`, `frontend/src/views/ForgotPasswordView.tsx`, `frontend/src/views/RequestPasswordResetView.tsx`, `frontend/src/views/ChangePasswordView.tsx`, `frontend/src/components/UrlExtractionDialog.tsx`

Problem:
The remaining create/auth screens still mixed local validation with repeated transport error handling, loading-state toggles, and ad-hoc notification plumbing.

Why it was problematic:
These small screens stayed denser than necessary, and the codebase still had two different patterns for handling simple async form actions.

Implemented fix:
Extended the shared `useAsyncAction` pattern to the remaining create/auth flows while keeping local validation inline. This removed the repeated network-action scaffolding and fixed a few latent local-state inconsistencies in the password and relation forms.

### Refactor Completed: Oversized Frontend View Test Suites Split by Behavior

File: `frontend/src/views/__tests__/SourceDetailView.*`, `frontend/src/views/__tests__/EvidenceView.*`, `frontend/src/views/__tests__/SynthesisView.*`

Problem:
The large detail-view test files grouped loading, error, rendering, navigation, sorting, and destructive-action coverage into single oversized suites.

Why it was problematic:
This made failures harder to localize, obscured test intent during review, and kept the test surface less modular than the refactored production components.

Implemented fix:
Split each oversized suite into smaller files organized by behavior area and added focused shared support modules per view for mock setup and render helpers. Coverage stayed intact while each file now documents one coherent concern.

## Next Steps

### Refactor Needed: Remaining Inline Validation Messaging Is Still Inconsistent

File: `frontend/src/hooks/useValidationMessage.ts`, `frontend/src/components/UrlExtractionDialog.tsx`, `frontend/src/views/CreateRelationView.tsx`, `frontend/src/views/CreateSourceView.tsx`, `frontend/src/views/CreateEntityView.tsx`, `frontend/src/views/ChangePasswordView.tsx`, `frontend/src/views/ForgotPasswordView.tsx`, `frontend/src/views/RequestPasswordResetView.tsx`, `frontend/src/views/SourceDetailView.tsx`

Problem:
Local validation feedback previously alternated between inline banners, field helper text, and notification toasts, especially in the smaller create/auth/dialog flows.

Why it is problematic:
This made similar validation failures feel inconsistent to users and kept simple submit handlers noisier than necessary.

Implemented fix:
Added a lightweight shared validation-message hook and migrated the remaining small form/dialog flows to use inline validation consistently. The URL extraction dialog no longer duplicates local validation with toasts, relation creation now validates required local fields before submit, and source auto-extraction without a stored URL now routes into the URL flow instead of raising a validation toast.

### Refactor Completed: Field-Level Local Validation for Small Create and Auth Flows

File: `frontend/src/hooks/useValidationMessage.ts`, `frontend/src/views/CreateEntityView.tsx`, `frontend/src/views/CreateRelationView.tsx`, `frontend/src/views/CreateSourceView.tsx`, `frontend/src/views/ForgotPasswordView.tsx`, `frontend/src/views/RequestPasswordResetView.tsx`, `frontend/src/views/ChangePasswordView.tsx`, `frontend/src/views/ResetPasswordView.tsx`, `frontend/src/components/UrlExtractionDialog.tsx`

Problem:
The smaller create/auth/dialog flows still mixed local validation and async transport failures in one message channel, which made some simple field errors render as page-level alerts instead of inline guidance.

Why it was problematic:
This made closely related forms feel inconsistent to users and kept the validation intent harder to read in the top-level submit handlers.

Implemented fix:
Extended the shared validation hook to track field-specific validation state, rewired the small create/auth/dialog flows so local checks render as field-level helper text or inline field messages, and kept async/server failures as separate page-level error banners. This makes the validation presentation consistent across the main lightweight form flows without changing their transport error behavior.

### Refactor Completed: Service Construction Cleanup Reduced to Optional Convenience Defaults

File: a very small residual set of backend services where default collaborator construction still exists as convenience wiring

Problem:
Most of the backend now exposes explicit provider or constructor seams, but a few services still keep constructor defaults for convenience.

Why it is problematic:
These remaining cases are much smaller than the previous transport-layer issues, but they still leave some boundaries less explicit than a fully dependency-injected design.

Implemented fix:
The broad transport-layer, screen-data, explanation, extraction, and collaborator-ownership cleanup is now complete. The few remaining constructor defaults are explicit convenience wiring rather than hidden architectural coupling, so this is no longer an active refactor item unless those defaults begin to obscure real boundaries again.

### Refactor Completed: Intentional Late-Binding Helpers Documented In Place

File: the few intentionally late-bound helper paths that remain for optional dependency or test-only behavior, such as PMC enrichment and testing-only helper loading

Problem:
The highest-impact hidden dependency edges in the extraction, core API, service, startup, and utility layers have been reduced, but a very small set of named late-binding helpers still remains where imports are deferred for optional dependency or test-only reasons.

Why it is problematic:
These hidden edges make the dependency graph harder to understand and weaken readability-first review.

Implemented fix:
The remaining late-binding paths were reduced to a few named helpers and documented directly in code as intentional extension seams for optional PMC enrichment and testing-only support. This is no longer active cleanup work unless the project later chooses to formalize those seams into explicit registries.

### Refactor Completed: Residual Stable Import Cleanup and Explicit Inference Detail Source Wiring

File: `backend/app/services/inference_service.py`, `backend/app/startup.py`, `backend/app/services/user_service.py`, `backend/app/utils/source_quality.py`, `backend/app/utils/revision_helpers.py`

Problem:
Several backend modules still kept stable imports inside function bodies, and `InferenceService` still instantiated `SourceService` inline while building detail payloads.

Why it was problematic:
These local imports were no longer serving a cycle-breaking purpose, and the inference detail path still hid one collaborator inside method logic instead of exposing it at construction time.

Implemented fix:
Promoted the remaining stable imports to module scope in the startup, user, source-quality, revision-helper, and inference-service modules, and made `InferenceService` own an explicit `SourceService` collaborator for detail payload enrichment. This narrows the remaining hidden-import and service-coupling backlog to the genuinely optional or late-binding cases.

### Refactor Completed: Final Safe Late-Binding Cleanup for Extractors, Main App Wiring, and Extraction Status

File: `backend/app/services/metadata_extractors/factory.py`, `backend/app/api/extraction.py`, `backend/app/main.py`, `backend/app/services/pubmed_fetcher.py`

Problem:
Some remaining backend modules still mixed safe module imports with ad-hoc local imports, while the truly optional PMC enrichment and testing-only router paths were not clearly isolated as intentional late-binding helpers.

Why it was problematic:
This left part of the dynamic-import story harder to scan than necessary and made it less obvious which deferred imports are architectural leftovers versus deliberate optional behavior.

Implemented fix:
Promoted safe extractor and settings imports to module scope, moved normal API router imports out of the main application body, and isolated the genuinely late-bound PMC enrichment and testing-only router behavior behind named helper loaders. The remaining deferred imports are now explicit intentional seams instead of hidden flow-level dependencies.

### Refactor Completed: Shared Collaborator Ownership in Explanation and Extraction Services

File: `backend/app/services/explanation_service.py`, `backend/app/services/extraction_service.py`

Problem:
The explanation and extraction services still kept some collaborator construction decisions inside service logic, including overlapping `SourceService` ownership between explanation and inference flows and late relation-type / semantic-role service resolution inside extraction methods.

Why it was problematic:
These paths were smaller than the prior transport-level issues, but they still hid part of the dependency story inside service internals instead of making it clear at construction time.

Implemented fix:
`ExplanationService` now builds around one shared `SourceService` collaborator and passes it through to its `InferenceService`, while `ExtractionService` resolves its relation-type and semantic-role collaborators up front in the constructor instead of deciding them inside prompt-generation methods. This narrows the remaining service-construction backlog to non-critical convenience defaults.

### Refactor Completed: Extraction Test Support Moved Out of Runtime API Package

File: `backend/app/api/document_extraction_dependencies.py`, `backend/tests/support/document_extraction_support.py`, `backend/scripts/adaptive_discovery_probe.py`

Problem:
The adaptive discovery probe had already been separated, but deterministic extraction testing helpers still lived under `app/api`, which kept test-only support code too close to the runtime API package.

Why it was problematic:
That blurred the line between production transport code and deterministic test scaffolding, even though the helpers only exist to support testing and `TESTING`-mode behavior.

Implemented fix:
Moved the deterministic PubMed support helpers into `backend/tests/support/` and switched the runtime dependency to a lazy import from that test-only package. The adaptive discovery probe remains in `backend/scripts/`, so the extraction test/tooling surface is now clearly separated from the normal API package.

### Refactor Completed: Screen-Oriented Inference Detail Payload for Evidence, Synthesis, and Disagreements

File: `backend/app/schemas/inference.py`, `backend/app/services/inference/detail_views.py`, `backend/app/services/inference_service.py`, `backend/app/api/inferences.py`, `frontend/src/api/inferences.ts`, `frontend/src/hooks/useEntityInferenceDetail.ts`, `frontend/src/views/SynthesisView.tsx`, `frontend/src/views/DisagreementsView.tsx`, `frontend/src/views/EvidenceView.tsx`

Problem:
The main inference detail screens were still deriving evidence lists, summary metrics, and contradiction groupings from a generic `relations_by_kind` transport payload on the client.

Why it was problematic:
This kept domain presentation logic spread across multiple views, made the screens harder to review, and forced frontend tests to reconstruct screen-specific data shaping instead of consuming a purpose-built read model.

Implemented fix:
Added an `InferenceDetailRead` payload with screen-oriented evidence items, relation summaries, disagreement groups, and aggregate stats, exposed it through a dedicated inference detail endpoint, and rewired the evidence, synthesis, and disagreements views to use that payload with compatibility fallbacks. The affected frontend tests were updated to mock the screen-oriented detail model directly.

## Validation

- Targeted Playwright explanation error-path spec passed against the E2E stack on `127.0.0.1:8001`:
  `e2e/tests/explanations/trace.spec.ts` with
  `should display a parsed rate-limit error when explanation loading is throttled`
