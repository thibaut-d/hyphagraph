## Normalize Randomized Crossover Study Design Phrases

Prevent extraction from failing when an LLM emits a verbose study design such as
"randomized, double-blind, placebo-controlled crossover design" instead of the
controlled `randomized_controlled_trial` enum.

### Objective
Accept source-faithful free-text randomized controlled design phrases while
preserving the controlled evidence-context schema.

### Impacted modules
- `backend/app/llm/schemas.py`
- `backend/tests/test_llm_schemas.py`

### Assumptions
- A phrase containing randomized/randomised plus controlled design language
  should normalize to `randomized_controlled_trial`.
- The extraction contract should remain enum-based; free text should not be
  stored directly in `study_design`.

### Plan
1. Add regression coverage for the observed THC/FMS study-design phrase.
2. Extend the existing study-design normalizer to recognize randomized design
   wording.
3. Run focused schema tests and extraction orchestrator tests.

### Validation
- `docker compose -f docker-compose.local.yml exec api bash -c 'cd /app && uv run pytest tests/test_llm_schemas.py tests/test_batch_extraction_orchestrator.py -q'`

### Risks
- Over-mapping a randomized but uncontrolled phrase; require randomized wording
  plus study/trial/design or controlled/blinded/placebo/crossover context.

### Status
completed

## Prune Vague Aggregate Extraction Entities

Prevent extraction drafts from creating standalone reusable entities for broad
factor/tool buckets such as "patient-related factors" or "other imaging and
assessment tools" when the same relation already contains concrete named
participants.

### Objective
Keep source-grounded concrete entities and relations while dropping vague
aggregate placeholders from extracted entity/relation drafts before review.

### Impacted modules
- `backend/app/llm/prompts.py`
- `backend/app/services/extraction_semantic_normalizer.py`
- `backend/tests/test_batch_extraction_orchestrator.py`
- `backend/tests/test_llm_prompts.py`

### Assumptions
- Named mechanisms/tools such as `central-sensitization`, `eos-system`, and
  `predictive-simulation` should remain.
- Generic buckets ending in "factors" or introduced as "other ... tools" should
  be omitted when they are only contextual labels.
- Optional relation roles can be removed if the remaining role set still
  satisfies the relation schema.

### Plan
1. Add regression tests for the observed THA extraction shape.
2. Add deterministic pruning of vague aggregate entities and their optional
   relation roles.
3. Add prompt rules discouraging the vague entities at generation time.
4. Run focused backend tests.

### Validation
- `cd backend && uv run pytest tests/test_batch_extraction_orchestrator.py tests/test_llm_prompts.py -q`

### Risks
- Over-pruning a legitimately named risk factor class; keep rules tied to broad
  factor/tool wording and preserve roles when removal would invalidate a relation.

### Status
completed

## Improve Relation Typing for Pain Variability Extractions

Reduce avoidable `other` relation drafts when systematic-review summaries state explicit
clinical associations, mechanism-background context, or patient clustering.

### Objective
Map source-grounded pain-variability extraction spans to the existing controlled relation
types when the local text makes the relation semantics explicit.

### Impacted modules
- `backend/app/llm/schemas.py`
- `backend/app/services/extraction_semantic_normalizer.py`
- `backend/tests/test_batch_extraction_orchestrator.py`

### Assumptions
- "Associated with measures of clinical relevance" should use `associated_with`
  even when the associated item is modeled as an `outcome`.
- "Because of evidence for central sensitization" can be represented as a
  `mechanism` background relation when the roles include a mechanism participant.
- "Cluster patients based on degree of pain variability" is an explicit
  association between the patient population and pain-variability outcome.

### Plan
1. Add focused tests reproducing the observed `other` drafts.
2. Broaden deterministic association validation to allow outcome/symptom/biomarker
   partners without weakening source-span requirements.
3. Add a narrow mechanism cue for evidence-backed mechanism background spans.
4. Run targeted backend tests.

### Validation
- `docker compose -f docker-compose.local.yml exec api bash -c 'cd /app && uv run pytest tests/test_batch_extraction_orchestrator.py -q'`
- `docker compose -f docker-compose.local.yml exec api bash -c 'cd /app && uv run pytest tests/test_llm_schemas.py -q'`

### Risks
- Over-classifying vague relatedness language; keep rules tied to explicit local cues.

### Status
completed

## Add Bulk Imported-Study Extraction Job

Add a bulk tool that searches already imported studies for a term, selects up
to a user-defined study budget, and runs the existing automatic entity and
relation extraction pipeline for each selected study.

### Objective
Let users start one auditable job from a source search term instead of manually
opening each imported study and extracting one source at a time.

### Impacted modules
- `backend/app/api/document_extraction_routes/discovery.py`
- `backend/app/api/document_extraction_schemas.py`
- `backend/app/models/long_running_job.py`
- `backend/app/services/document_extraction_discovery.py`
- `frontend/src/api/longRunningJobs.ts`
- `frontend/src/api/extraction.ts`
- `frontend/src/types/extraction.ts`
- `frontend/src/views/PubMedImportView.tsx`
- `frontend/src/views/__tests__/PubMedImportView.test.tsx`

### Assumptions
- "Budget of n studies" means extract at most `n` already imported studies
  matching the query.
- LLM extraction remains non-authoritative: extracted entities and relations are
  staged for review, not silently materialized as confirmed graph facts.
- Sources with any existing staged extraction are treated as already extracted
  and are excluded from the proposal/job.
- A source must have stored document text before it can be selected for bulk
  extraction.

### Plan
1. Add typed request/response schemas and a new long-running job kind.
2. Implement service orchestration that searches imported source revisions,
   excludes already-extracted sources, and returns per-study status.
3. Add a protected API endpoint to start the bulk extraction job.
4. Add a frontend control for search-term bulk extraction.
5. Add focused backend and frontend tests.

### Validation
- `cd backend && uv run pytest tests/test_document_extraction_workflow.py`
- `cd frontend && npm test -- --run src/views/__tests__/PubMedImportView.test.tsx`

### Risks
- Large budgets can consume LLM/API quota; keep the backend budget capped.
- A single bad study should be reported per item without hiding failures.
- The "already extracted" rule is conservative: any staged extraction excludes
  the source, even if a prior run only partially succeeded.

### Status
completed

## Improve Extraction Rules for Observational Outcome Findings

Reduce strange `associated_with` drafts for cohort-study outcome findings,
especially intervention/exposure spans that report reduced odds and baseline
covariate differences.

### Objective
Make extraction prefer outcome/risk relations for measured intervention
findings and avoid materializing baseline characteristics as treatment
relationships.

### Impacted modules
- `backend/app/llm/prompts.py`
- `backend/app/services/extraction_semantic_normalizer.py`
- `backend/tests/test_batch_extraction_orchestrator.py`
- `backend/tests/test_llm_prompts.py`

### Assumptions
- "Associated with reduced odds of X" should be modeled as decreased risk/odds
  of X when the span has an agent and target/outcome.
- Baseline or post-matching covariate imbalances such as BMI/HbA1c being higher
  in a treatment cohort are study context unless the text explicitly states an
  intervention effect.
- Speculative "potentially reflecting" symptom-burden summaries should not
  become strong graph relations.

### Plan
1. Add prompt rules distinguishing outcome-reduction findings from generic
   association.
2. Add prompt rules to omit baseline/cohort-descriptor differences as graph
   relations.
3. Update deterministic semantic normalization for reduced odds and baseline
   covariate spans.
4. Add focused backend tests for the GLP-1RA extraction shapes.

### Validation
- `backend/tests/test_batch_extraction_orchestrator.py`
- `backend/tests/test_llm_prompts.py`

### Risks
- Some observational associations may be over-normalized into risk relations;
  keep the rule tied to explicit reduced/increased odds/risk wording.

### Status
completed

## Fix URL Extraction Failure on Incomplete Observational Relations

Prevent one malformed LLM `associated_with` relation from failing URL
extraction with a 500 while preserving the model-proposed type for review.

### Objective
Downgrade incomplete observational relation shapes to `other` before batch
schema validation rejects the whole extraction response.

### Impacted modules
- `backend/app/llm/schemas.py`
- `backend/tests/test_llm_schemas.py`
- `backend/tests/test_batch_extraction_orchestrator.py`

### Assumptions
- Incomplete observational relations are model shape errors, not authoritative
  graph facts.
- Downgrading preserves the malformed proposal for later normalization/review
  without accepting an invalid typed relation.

### Plan
1. Reproduce the missing-target observational relation at schema validation.
2. Downgrade incomplete observational relations to `other`.
3. Add orchestrator coverage proving malformed extraction output does not abort
   the batch.
4. Run focused backend tests.

### Validation
- `backend/tests/test_llm_schemas.py`
- `backend/tests/test_batch_extraction_orchestrator.py`

### Risks
- Over-retaining vague `other` relations; existing semantic cleanup should drop
  ambiguous `other` relations with no focal target.

### Status
completed

## Add Admin Graph Cleaning Tab

Add an admin surface for automatic and semi-automatic graph cleaning, starting
with human-reviewed entity deduplication candidates and read-only relation
quality analysis.

### Objective
Give admins a review-gated workflow for cleaning duplicate graph entities and
inspecting relation-level cleanup risks while keeping LLM/heuristic analysis
advisory and non-authoritative.

### Impacted modules
- `backend/app/api/entities.py`
- `backend/app/services/entity_merge_service.py`
- `backend/app/services/graph_cleaning_service.py`
- `backend/app/schemas/entity_merge.py`
- `backend/app/schemas/graph_cleaning.py`
- `frontend/src/views/AdminView.tsx`

### Assumptions
- Initial automatic cleaning should be dry-run only.
- Entity merge remains the only mutating graph-cleaning action in this slice.
- Relation deduplication and role-consistency cleanup are read-only analysis
  until source context and provenance-safe mutation rules are designed.

### Plan
1. Add a superuser-only duplicate-entity candidate endpoint.
2. Extend the admin merge tab into a graph-cleaning tab.
3. Keep manual merge available and require confirmation for candidate actions.
4. Add read-only duplicate-relation and role-consistency analysis.
5. Add focused backend and frontend tests.

### Validation
- backend entity merge service and endpoint tests
- backend graph-cleaning service and endpoint tests
- frontend AdminView test
- frontend build

### Risks
- Similarity-based candidates can be false positives and must remain
  review-gated.
- Future relation/role cleaning must preserve contradiction visibility and
  source provenance.

### Status
completed

## Complete Graph Cleaning Review Workflow

Extend the initial graph-cleaning tab into a full review workflow for advisory
LLM critique, persisted review decisions, and provenance-safe cleanup actions.

### Objective
Let admins think through and execute graph-cleaning actions without allowing
LLM output, heuristic scores, or convenience UI to hide evidence, contradictions,
or revision history.

### Impacted modules
- `backend/app/api/graph_cleaning.py`
- `backend/app/services/graph_cleaning_service.py`
- `backend/app/schemas/graph_cleaning.py`
- `backend/app/llm/`
- `backend/app/models/`
- `backend/alembic/versions/`
- `backend/tests/test_graph_cleaning_*.py`
- `frontend/src/views/AdminView.tsx`
- `frontend/src/api/`
- `frontend/src/components/admin/`
- `frontend/src/views/__tests__/AdminView.test.tsx`

### Assumptions
- LLM critique is advisory only and never performs writes.
- Relation cleanup must preserve the original relation and source trail, either
  by creating a new revision or marking a relation as rejected/duplicate with
  explicit provenance.
- Role corrections must create new relation revisions rather than mutating
  current or historical role rows in place.
- Candidate review decisions should be persisted so dismissed warnings do not
  reappear indefinitely.

### Plan
1. Define a persisted graph-cleaning review model.
   - Store candidate fingerprint, candidate type, decision status, reviewer,
     notes, timestamps, and optional linked action result.
   - Add Alembic migration and backend tests for decision persistence.
2. Add advisory LLM critical analysis.
   - Endpoint accepts current candidates or candidate IDs/fingerprints.
   - Response uses structured fields: `recommend`, `reject`,
     `needs_human_review`, rationale, risks, and evidence gaps.
   - Store no LLM conclusion as authoritative graph fact.
3. Add frontend review-state UI.
   - Filters for candidate type and status.
   - Detail drawer with candidate evidence, LLM critique, admin notes, and
     decision buttons.
   - Keep entity merge confirmation separate from LLM advice.
4. Add provenance-safe duplicate relation actions.

   - Define exact semantics for duplicate marking before implementation.
   - Prefer explicit rejected/duplicate status or new revision over deletion.
   - Preserve source, relation ID history, reviewer, and rationale.
5. Add role consistency action flow.
   - From a warning, open affected relations and propose a role edit.
   - Apply by creating a new relation revision with updated roles.
   - Require human confirmation and notes.
6. Move graph-cleaning frontend API calls into a typed client and wire the
   full workflow into the admin tab.
   - Add `frontend/src/api/graphCleaning.ts`.
   - Keep graph-cleaning actions human-confirmed in the UI.

### Validation
- Backend service tests for candidate generation, review persistence, LLM
  response parsing, and mutation invariants.
- Backend endpoint tests for superuser authorization and error responses.
- Migration test or upgrade check for any new review-decision tables.
- Frontend tests for loading, empty, error, reviewed/dismissed, and action
  confirmation states.
- Targeted relation revision tests proving cleanup creates auditable history
  and does not hide contradictions or evidence.
- Frontend build.

### Risks
- Relation deduplication can accidentally collapse separate evidence statements.
- Role consistency warnings can be false positives when source context differs.
- Persisted candidate fingerprints can become stale after graph edits.
- LLM critique can sound overconfident; UI must present it as advisory and
  expose risks/evidence gaps.

### Status
completed

## Make Long-Running Mobile Workflows Resumable

Persist smart discovery and URL extraction as resumable backend jobs so mobile
browser tab reloads do not discard in-flight work or completed previews.

### Objective
Let the frontend recover long-running smart discovery and source URL extraction
after a mobile browser reload by polling a persisted job status/result.

### Impacted modules
- `backend/app/models/long_running_job.py`
- `backend/app/services/long_running_job_service.py`
- `backend/app/api/document_extraction_routes/`
- `frontend/src/api/`
- `frontend/src/hooks/useSmartDiscoveryController.ts`
- `frontend/src/views/SourceDetailView.tsx`

### Assumptions
- The first fix targets URL extraction and smart discovery. Uploaded-file
  extraction needs a separate file-staging design before it can be safely
  resumed after reload.
- In-process background tasks are acceptable for the current remote-dev stack;
  API container restarts may still interrupt running jobs.

### Plan
1. Add a persisted job table and API read contract.
2. Add start-job endpoints for smart discovery and source URL extraction.
3. Reuse existing extraction/discovery services inside background jobs.
4. Store job IDs in frontend local storage and poll until completion.
5. Add focused lifecycle tests and run targeted checks.

### Validation
- `backend/tests/test_long_running_job_service.py`
- frontend type/build check

### Risks
- Jobs are resumable across page reloads but not fully durable across backend
  process restarts without an external worker queue.

### Status
completed

## Harden Graph Cleaning UX and Scoring

Follow-up polish for graph-cleaning usability and candidate quality after the
core review/action workflow is in place.

### Objective
Improve review ergonomics and candidate ranking without changing the core rule
that cleaning actions require human confirmation.

### Impacted modules
- `backend/app/services/entity_merge_service.py`
- `backend/app/services/graph_cleaning_service.py`
- `frontend/src/views/AdminView.tsx`
- `frontend/src/components/admin/`

### Completed in initial hardening
- Replaced prompt-based duplicate-relation and role-correction confirmation
  with typed dialogs that require explicit reviewer rationale.
- Added review-status filtering so dismissed/applied candidates can be hidden
  from the default review flow.
- Split the graph-cleaning tab body out of `AdminView.tsx` into a focused
  admin component.
- Added candidate-type and LLM-recommendation filters.
- Exposed raw entity-merge score factors in the backend response and admin UI.
- Added focused frontend coverage for dialog-gated cleanup actions and score
  factor display, candidate-type filtering, and LLM-recommendation filtering.
- Added backend coverage for entity merge score factor calculation.

### Remaining plan
1. [x] Improve entity candidate scoring with aliases/terms, deeper summary matching,
   shared relation neighborhoods, and source co-occurrence.
2. [x] Add focused frontend tests for dialog validation error states.

### Validation
- Frontend tests for dialog validation and filtered states.
- Backend tests for score factor calculation.
- Frontend build.

### Risks
- More aggressive scoring can increase false positives.
- Component extraction can accidentally regress existing admin tabs.

### Status
completed

## Add Admin UI for Entity Graph Merge

Allow admins to merge two knowledge-graph entity nodes into one when they refer to the
same real-world concept (e.g. "aspirin" and "acetylsalicylic-acid").

**The backend service already exists**: `backend/app/services/entity_merge_service.py`
exposes `merge_entities(source_id, target_id, db)`. What is missing is the API endpoint
and the admin panel UI.

Note: this is a *graph-level* merge (entity nodes + their relations), distinct from the
*vocabulary-level* category merge above.

### Objective
Give admins a UI-driven way to deduplicate entity nodes without direct database access.

### Impacted modules
- `backend/app/api/entities.py` (or a new `entity_merge.py`) — `POST /entities/{entity_id}/merge-into/{target_id}` (superuser)
- `frontend/src/views/AdminView.tsx` — "Merge into…" search-and-select dialog, accessible from an Entities tab or from the entity detail page

### Plan
1. Add `POST /entities/{entity_id}/merge-into/{target_id}` (superuser only) that delegates to `EntityMergeService.merge_entities()`.
   - Returns a summary of re-parented relations and deleted source node.
2. Add an Entities tab (or context menu entry on the entity detail page) in the admin panel with a merge action.
   - Type-ahead search to find the target entity by slug or label.
   - Confirmation dialog showing which entity will be kept and which removed.

### Status
completed

## Expand Extraction Relation Types Beyond `other`

Reduce low-signal `other` relations in document extraction by adding explicit
types for non-causal association and prevalence findings, and by dropping
ambiguous leftover `other` relations before they reach review/materialization.

### Objective
Broaden the extraction taxonomy so observational/systematic-review findings can
land in typed relations, while making generic `other` stricter and rarer.

### Impacted modules
- `backend/app/llm/schemas.py`
- `backend/app/llm/prompts.py`
- `backend/app/services/extraction_semantic_normalizer.py`
- `backend/app/services/extraction_text_span_validator.py`
- `backend/alembic/versions/`
- `frontend/src/types/extraction.ts`
- `frontend/src/components/ExtractedRelationsList.tsx`
- `frontend/src/components/extraction/ExtractionCard.tsx`

### Assumptions
- `associated_with` and `prevalence_in` cover the main observational patterns
  that are currently collapsing into `other`.
- Recommendation-only screening language should not be materialized as a
  relation unless it also states a typed finding with clear participants.

### Plan
1. Extend the relation-type contract and static prompt vocabulary.
2. Seed the new system relation types in the database.
3. Reclassify common `other` patterns into the new types during normalization.
4. Drop ambiguous leftover `other` relations that still lack a clear focal target.
5. Update frontend/shared enum consumers and focused tests.

### Validation
- backend extraction schema/prompt/orchestrator tests
- frontend tests covering extracted relation rendering and review cards

### Risks
- Over-normalizing observational language into a typed relation when the source
  span is actually too vague.
- Existing databases need the new Alembic migration applied before dynamic
  prompts expose the new types.

### Status
completed

## Harden Extraction Statement Kind Validation

Prevent URL/document extraction from failing when the LLM emits section-heading
labels like "conclusion" instead of the canonical statement kinds.

### Objective
Normalize known statement-kind aliases at the extraction schema boundary so
preview generation stays deterministic and auditable.

### Impacted modules
- `backend/app/llm/schemas.py`
- `backend/tests/test_llm_schemas.py`
- `backend/tests/test_batch_extraction_orchestrator.py`

### Assumptions
- Section-heading labels such as "conclusion", "results", and "methods" are
  alias drift from the LLM, not intended stored semantics.
- The canonical response contract remains `finding`, `background`,
  `hypothesis`, and `methodology`.

### Plan
1. Reproduce the failure at the batch-extraction validation boundary.
2. Normalize a narrow alias set before literal validation.
3. Add focused tests for schema validation and orchestrator flow.
4. Re-run the targeted backend tests.

### Validation
- `backend/tests/test_llm_schemas.py`
- `backend/tests/test_batch_extraction_orchestrator.py`

### Risks
- Over-normalizing a genuinely distinct statement type and hiding model drift.
- Backend/frontend contract drift if aliases leak past the schema boundary.

### Status
completed

## Add Review Queue Entity Merge Action

Let reviewers merge a staged entity extraction into an existing likely duplicate
entity directly from `/review-queue`.

### Objective
Add a `Merge` action for staged entity items that shows likely existing entity
matches, approves/materializes the staged entity, then uses the existing entity
merge process to merge the new source node into the selected target.

### Impacted modules
- `backend/app/services/entity_merge_service.py`
- `backend/app/api/extraction_review.py`
- `backend/app/schemas/entity_merge.py`
- `frontend/src/api/entities.ts`
- `frontend/src/api/extractionReview.ts`
- `frontend/src/components/extraction/ExtractionCard.tsx`
- `frontend/src/views/ReviewQueueView.tsx`
- targeted backend/frontend tests

### Assumptions
- The staged entity must still be approved before graph mutation so review
  provenance remains explicit.
- Candidate suggestions are heuristic and must remain user-reviewed.
- Relation evidence and contradiction visibility are unchanged; this only
  changes entity deduplication before/after materialization.

### Plan
1. Add a targeted backend candidate endpoint for one staged entity extraction.
2. Add typed frontend clients for candidate lookup and merge execution.
3. Add `Merge` UI for entity staged items with candidate review and confirmation.
4. Add focused backend and frontend tests.
5. Run targeted pytest and Vitest checks.

### Validation
- `docker compose -f docker-compose.local.yml exec -T api bash -c 'cd /app && uv run pytest tests/test_entity_merge_service.py tests/test_extraction_review_endpoints.py -q'`
- `cd frontend && npm test -- --run src/views/__tests__/ReviewQueueView.test.tsx`

### Risks
- A reviewer could choose the wrong target; keep the dialog explicit about source
  and target direction.
- If materialization fails, merge must not run.

### Status
completed

## Fix Remote Dev Loading Regressions After Entity Merge

Repair two regressions observed on `algiagraph.com` after merging
`fibromyalgia-syndrome` into `fibromyalgia`.

### Objective
Keep `/entities` and Admin Graph Cleaning responsive after review-queue entity merges.

### Impacted modules
- `frontend/src/views/EntitiesView.tsx`
- `backend/app/services/entity_merge_service.py`

### Assumptions
- Graph-cleaning entity candidates are advisory and can use deterministic
  blocking before expensive fuzzy scoring.
- Infinite-scroll pagination should derive the next offset from loaded item
  count rather than a separate mutable offset state.

### Plan
1. Restart the blocked remote-dev API process.
2. Reproduce `/entities` loading via direct API calls.
3. Fix duplicate/concurrent infinite-scroll pagination calls.
4. Reproduce slow Admin Graph Cleaning candidate scan.
5. Add cheap entity-pair blocking before expensive term similarity scoring.
6. Run focused frontend/backend tests and verify remote endpoints.

### Validation
- `cd frontend && npm test -- --run src/views/__tests__/EntitiesView.test.tsx`
- `cd frontend && npm run build`
- `docker compose -f docker-compose.local.yml exec -T api bash -c 'cd /app && uv run pytest tests/test_entity_merge_service.py tests/test_graph_cleaning_service.py -q'`
- Remote direct service scan: entity merge candidates complete in about 10s instead of timing out.
- `https://algiagraph.com/api/entities/?limit=50&offset=0` returns `200`.
- `https://algiagraph.com/api/entities/filter-options` returns `200`.

### Risks
- Entity merge candidate scan now skips pairs that have neither similar slugs,
  containment, nor exact alias/name overlap before fuzzy term scoring.

### Status
completed
