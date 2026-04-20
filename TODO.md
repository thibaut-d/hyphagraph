# Current Work

**Last updated**: 2026-04-20

## Tighten Benchmark-Driven Extraction Normalization

Use the new gold benchmark to improve automatic extraction quality at the
semantic-normalization layer instead of relying only on prompt wording.

### Objective
Reduce the benchmark's remaining relation failures by normalizing three common
LLM error modes before validation and staging:
- `other` relations that are actually typed findings
- null efficacy findings mislabeled as `contradicts` instead of `neutral`
- intervention-arm/group noun drift such as `ssri-groups` instead of `ssris`

### Impacted modules
- `backend/app/services/extraction_semantic_normalizer.py`
- `backend/app/services/batch_extraction_orchestrator.py`
- `backend/app/llm/prompts.py`
- `backend/tests/test_batch_extraction_orchestrator.py`
- `backend/tests/test_extraction_evaluation.py`
- `backend/tests/test_document_extraction_workflow.py`

### Assumptions
- The best place for these fixes is one bounded semantic-normalization pass
  after schema validation but before text-span validation.
- The normalization rules must stay conservative and source-local; if a span is
  too ambiguous, it should remain unchanged and let validation reject it.
- Prompt improvements are still useful, but they should reinforce the same
  semantics as the normalizer rather than compensate for missing backend logic.

### Plan
1. Add a semantic normalizer for extracted entities and relations.
2. Normalize narrow, justified cases:
   relation `other` -> `treats` or `causes` when roles and span language make the type explicit
   `comparator` -> `control_group`
   null efficacy wording -> `finding_polarity=neutral`
   intervention group/arm entities -> canonical intervention slugs when locally obvious
3. Tighten prompt wording to bias GPT-5 toward the same normalized shapes.
4. Add focused regressions around the benchmark failure modes and the extraction workflow path.
5. Re-run targeted tests and the live extraction benchmark.

### Validation
- Backend: `cd backend && uv run pytest tests/test_batch_extraction_orchestrator.py tests/test_extraction_evaluation.py tests/test_document_extraction_workflow.py -q`
- Backend: `cd backend && uv run python scripts/run_extraction_eval.py --json`

### Risks
- Over-aggressive normalization could silently change source meaning if the
  span is not explicit enough.
- Relation upgrades from `other` to typed relations must not bypass required
  role semantics or local grounding.
- Group/arm alias cleanup must not collapse genuinely distinct study arms into a
  single intervention entity when the source keeps them distinct.

### Status
completed

## Add Gold Extraction Benchmark And Metrics Runner

Create a persistent, source-grounded extraction benchmark so prompt, validator,
and model changes can be measured against the same hard scientific cases instead
of judged by anecdotal spot checks.

### Objective
Establish an auditable gold benchmark for entity and relation extraction that
measures precision, recall, and relation-semantic validity against curated
study snippets.

### Impacted modules
- `backend/app/services/extraction_evaluation.py`
- `backend/scripts/run_extraction_eval.py`
- `backend/tests/test_extraction_evaluation.py`
- `TODO.md`

### Assumptions
- The benchmark should reuse the runtime extraction schemas and validation
  logic instead of inventing a separate scoring contract.
- A small gold set that targets known failure modes is more useful now than a
  larger but loosely curated benchmark.
- Relation scoring should be semantic: compare relation type, role assignment,
  comparator/context roles that materially change meaning, and finding polarity,
  while ignoring prose fields like notes.

### Plan
1. Add a curated benchmark dataset with compact scientific snippets and
   expected entities/relations for known hard cases.
2. Implement deterministic scoring utilities for:
   entity precision / recall / F1
   relation precision / recall / F1
   relation semantic-validity rate against the current validator
3. Add a small CLI runner that executes the current batch extractor on the gold
   cases and prints a case-by-case plus aggregate report.
4. Add focused tests that prove the scorer catches the known failure modes and
   rewards semantically correct outputs.

### Validation
- Backend: `cd backend && uv run pytest tests/test_extraction_evaluation.py`

### Risks
- A benchmark that is too strict about optional context roles could penalize
  valid extractions that are semantically equivalent.
- A benchmark that is too loose about polarity or comparator roles would fail
  to catch the exact extraction mistakes we most care about.
- Once introduced, benchmark cases need active maintenance when the extraction
  contract evolves.

### Status
completed

## Tighten LLM Extraction Prompts From Literature Comparison

Use the prompt-process patterns from the closest literature-review implementations
(`GraphRAG`, `HyperGraphRAG`, `Hyper-RAG`) to improve HyphaGraph extraction
without weakening provenance or contradiction visibility.

### Objective
Strengthen entity and relation extraction prompts so they are more complete and
less noisy, especially around missed claim spans, speculative language, and
generic non-entity document nouns.

### Impacted modules
- `backend/app/llm/prompts.py`
- `backend/tests/test_llm_prompts.py`

### Assumptions
- The most reusable ideas from the comparison are process constraints
  (coverage audit, relation-bearing entity focus, source-vs-normalization
  separation), not the external projects' storage formats.
- HyphaGraph should keep its current evidence-first schema rather than adopt
  GraphRAG-style binary edges or Hyper-RAG-style free-form summaries.

### Plan
1. Compare the closest literature-review implementations that publicly expose
   prompt-driven entity/relationship extraction.
2. Pull the strongest prompt tactics that fit HyphaGraph's evidence-first
   constraints.
3. Tighten local prompts and add focused prompt regression checks.
4. Run the prompt test target.

### Validation
- Backend: `cd backend && uv run pytest tests/test_llm_prompts.py`

### Risks
- Over-constraining prompt wording may reduce recall on short or noisy inputs.
- A prompt-only pass cannot guarantee GraphRAG-style completeness without a later
  multi-turn gleaning loop.

### Status
completed

## Add Multi-Turn Gleaning Loop To Extraction

Add a bounded multi-turn gleaning loop to the LLM extraction pipeline so the
model can append missed entities, relation participants, and null/contradictory
findings after the first pass.

### Objective
Increase extraction recall on dense scientific text without weakening
provenance, contradiction visibility, or source-bounded validation.

### Impacted modules
- `backend/app/services/batch_extraction_orchestrator.py`
- `backend/app/services/extraction_service.py`
- `backend/app/llm/prompts.py`
- `backend/app/llm/base.py`
- `backend/app/llm/openai_provider.py`
- `backend/tests/test_llm_prompts.py`
- extraction workflow / orchestrator backend tests

### Assumptions
- The safest HyphaGraph version is append-only: follow-up turns may add missed
  items but must not rewrite earlier extracted items.
- We should cap the loop at 1-2 extra passes to limit cost and noise.
- Every gleaned item must still pass the existing schema and text-span
  validation pipeline before preview/save.

### Plan
1. Trace the current batch extraction call path and identify the smallest place
   to keep prior LLM history for follow-up extraction turns.
2. Add one or two follow-up prompts:
   `add only missed items`
   `is anything important still missing? yes/no`
3. Merge follow-up outputs into the first-pass batch response with stable
   dedupe rules for entities and relations.
4. Keep gleaning focused on missed claim-bearing spans, missed role
   participants, and missed null/contradictory findings.
5. Run the existing validation/dedupe path on the merged result.
6. Add focused tests for:
   second-pass additions
   no duplicate rewrites
   bounded loop stopping
   null/contradictory finding recovery

### Validation
- Backend: `cd backend && uv run pytest tests/test_llm_prompts.py`
- Backend: focused pytest targets for batch extraction orchestration and
  extraction workflow merge/dedupe behavior

### Risks
- Extra turns can add latency and cost to source extraction.
- Loose follow-up prompts can create noisy or duplicate items.
- If merge rules are weak, later passes may attach roles or evidence context to
  the wrong relation.

### Inspiration
- Internal survey: [docs/research/HYPERGRAPH_RAG_PAPERS.md](/srv/hyphagraph/docs/research/HYPERGRAPH_RAG_PAPERS.md)
- GraphRAG indexing methods:
  https://github.com/microsoft/graphrag/blob/main/docs/index/methods.md
- GraphRAG prompt tuning:
  https://github.com/microsoft/graphrag/blob/main/docs/prompt_tuning/manual_prompt_tuning.md
- GraphRAG claim extraction loop prompts:
  https://github.com/microsoft/graphrag/blob/main/packages/graphrag/graphrag/prompts/index/extract_claims.py
- HyperGraphRAG prompt and operate flow:
  https://github.com/LHRLAB/HyperGraphRAG/blob/main/hypergraphrag/prompt.py
  https://github.com/LHRLAB/HyperGraphRAG/blob/main/hypergraphrag/operate.py
- Hyper-RAG prompt and operate flow:
  https://github.com/iMoonLab/Hyper-RAG/blob/main/hyperrag/prompt.py
  https://github.com/iMoonLab/Hyper-RAG/blob/main/hyperrag/operate.py

### Status
completed

## Collapse Review Into One Extraction Queue

Remove the separate LLM draft revision review flow so extraction review uses one
mechanism and one queue end to end.

### Objective
Keep staged extraction review as the single review path. User-approved or
review-queue-approved extraction materialization should create current,
visible revisions directly instead of creating secondary draft revisions that
require another queue.

### Impacted modules
- `backend/app/services/bulk_creation_service.py`
- `backend/app/services/document_extraction_processing.py`
- `backend/app/services/extraction_review/materialization.py`
- `backend/app/services/extraction_review_service.py`
- `backend/app/api/revision_review.py`
- `backend/app/services/revision_review_service.py`
- `backend/app/schemas/review.py`
- `backend/app/main.py`
- `frontend/src/views/ReviewQueueView.tsx`
- `frontend/src/components/review/LlmDraftsPanel.tsx`
- `frontend/src/api/revisionReview.ts`
- focused backend/frontend review and extraction tests

### Assumptions
- The intended single review workflow is the staged extraction review flow, not
  the later revision-draft confirmation flow.
- `save_extraction_to_graph()` represents explicit human approval and should
  therefore materialize confirmed revisions immediately.
- Keeping `created_with_llm` and `llm_review_status` on revisions preserves LLM
  provenance without requiring a second queue.

### Plan
1. Trace all production write paths that currently create extraction-driven draft revisions.
2. Change those writes to create confirmed/current revisions with explicit review provenance.
3. Remove the separate revision-review queue API and frontend tab/panel.
4. Update focused tests around extraction save/materialization and review queue behavior.
5. Run targeted backend and frontend validation.

### Validation
- Backend: focused pytest for document extraction workflow and extraction review service/endpoints
- Frontend: focused Vitest for `ReviewQueueView` and affected extraction/review UI

### Risks
- If any non-extraction flow still depends on draft revisions, removing the separate queue could strand those rows.
- Review provenance must stay explicit when creation happens from user save vs queue approval vs auto-verification.
- Frontend/backend contract cleanup must remove all revision-review references to avoid dead navigation or pact drift.

### Status
completed

## Stabilize URL Knowledge Extraction

Improve the source-page "Auto-Extract Knowledge from URL" workflow so proposed relations
are more consistent across runs and carry explicit study/evidence context.

### Objective
Make extraction outputs more deterministic and more faithful to scientific-study structure by
enforcing tighter hypergraph relation semantics, clearer finding vs assumption separation, and
explicit proof-level metadata.

### Impacted modules
- `backend/app/llm/prompts.py`
- `backend/app/llm/schemas.py`
- `backend/app/services/batch_extraction_orchestrator.py`
- `backend/app/services/document_extraction_processing.py`
- `backend/app/services/bulk_creation_service.py`
- `backend/app/services/extraction_review/materialization.py`
- `backend/app/schemas/source.py`
- `frontend/src/types/extraction.ts`
- `frontend/src/components/ExtractionPreview.tsx`
- `frontend/src/components/ExtractedRelationsList.tsx`
- `backend/tests/test_llm_prompts.py`
- extraction workflow / document extraction backend tests
- extraction preview frontend tests

### Assumptions
- The main instability comes from an under-specified batch prompt and a relation schema that does
  not force the model to separate study findings, evidence quality, and methodological context.
- Relation revisions can safely carry additional structured extraction context in `scope` without
  requiring a schema migration because `scope` is already JSON.
- The source-page preview is the right place to expose study-quality context before save.

### Plan
1. Tighten the extraction contract for study-grounded hypergraph relations.
2. Add structured relation metadata for finding polarity/status and study-quality qualifiers.
3. Pass that metadata through preview and save/materialization flows.
4. Update the source extraction preview UI to show study context clearly.
5. Add focused backend/frontend tests and run targeted validation.

### Validation
- Backend: focused pytest targets for prompts, document extraction workflow, and extraction APIs
- Frontend: focused Vitest targets for extraction preview / extracted relations UI

### Risks
- Backend/frontend contract drift if new extraction fields are not wired through everywhere.
- Over-constraining the prompt could reduce recall on shorter or noisier source texts.
- Long documents may still need a later chunking strategy if response budget remains a bottleneck.

### Status
completed

## Fix URL Extraction Evidence-Strength Alias Crash

Prevent URL knowledge extraction from failing when the LLM emits confidence-style
evidence labels (`low`, `medium`, `high`) in relation study metadata,
and ensure internal extraction failures still use the structured API error contract.

### Objective
Make `extract-from-url` resilient to known evidence-strength alias drift and stop
frontend fallbacks from collapsing into opaque `object`-type errors.

### Impacted modules
- `backend/app/llm/schemas.py`
- `backend/app/api/document_extraction_dependencies.py`
- `backend/tests/test_llm_schemas.py`

### Assumptions
- The live crash is caused by schema validation rejecting `study_context.evidence_strength="low"`.
- Mapping `high -> strong`, `medium -> moderate`, and `low -> weak` is semantically safe at the schema boundary.
- Structured API errors are preferable to raw `HTTPException.detail` strings for extraction failures.

### Plan
1. Normalize evidence-strength aliases at the LLM schema boundary.
2. Keep internal extraction failures inside the standard API error envelope.
3. Add focused regression coverage for alias normalization.
4. Re-run targeted validation and the real source reproduction.

### Validation
- Backend: focused pytest for the new schema regression
- Backend: reproduce extraction for source `28932f7d-569d-4a55-b9b3-1e1010c4c42a`

### Risks
- Alias normalization could hide prompt drift if we broaden it too far.
- Internal error messages must stay structured without leaking unnecessary implementation detail.

### Status
completed

## Fix Save Extraction Reviewed-At Timestamp Crash

Prevent `save-extraction` and related review flows from crashing on PostgreSQL
when staged extraction review metadata writes a timezone-aware datetime into the
naive `reviewed_at` column.

### Objective
Keep extraction save/review flows compatible with the current staged extraction
schema by normalizing review timestamps to UTC-naive values at the write boundary.

### Impacted modules
- `backend/app/utils/datetime.py`
- `backend/app/services/document_extraction_processing.py`
- `backend/app/services/extraction_review/auto_commit.py`
- `backend/app/services/extraction_review/queries.py`
- `backend/tests/test_document_extraction_workflow.py`
- `backend/tests/test_extraction_review_service.py`

### Assumptions
- `staged_extractions.reviewed_at` is intentionally stored as a naive UTC timestamp today.
- The safest short-term fix is to normalize writes, not to change the database schema in this task.
- The same timestamp bug can affect save reconciliation, manual review, and auto-commit flows.

### Plan
1. Add a small helper for UTC-naive timestamps.
2. Use it on every `reviewed_at` write path.
3. Add focused regression assertions in extraction workflow and review service tests.
4. Re-run targeted backend validation and reproduce the original save flow.

### Validation
- Backend: focused pytest for extraction workflow and review service review paths
- Backend: reproduce `POST /api/sources/920b8d18-8ee3-464d-aa83-15dd7c8463d9/save-extraction`

### Risks
- If other naive timestamp columns are written with aware datetimes elsewhere, they may still need separate cleanup.
- This preserves the current schema contract; a future migration to timezone-aware review timestamps would need coordinated changes.

### Status
completed

## Keep Error Notifications Open and Copyable During Interaction

Prevent shared frontend error notifications from auto-dismissing while the user is
hovering, expanding, or copying developer-facing error details, and add a direct
copy action with richer debug context.

### Objective
Keep the shared error snackbar readable and copyable, and make copied error reports
more useful for debugging without changing the normal manual close behavior or the
queued notification flow.

### Impacted modules
- `frontend/src/notifications/NotificationContext.tsx`
- `frontend/src/notifications/__tests__/NotificationContext.test.tsx`

### Assumptions
- The reported "box closes while copying" behavior is caused by the custom auto-dismiss timer continuing during interaction.
- Pausing auto-dismiss on pointer and keyboard interaction is safer than making all error toasts permanently sticky.
- Dev-detail text should remain selectable for copy/paste.

### Plan
1. Inspect the shared notification component and confirm where dismiss timing is controlled.
2. Pause auto-dismiss while the current notification has pointer or focus interaction.
3. Add richer debug metadata and a copy-to-clipboard action to the dev-details panel.
4. Add focused regression tests for copy payload and timed interaction behavior.
5. Re-run the notification test target.

### Validation
- Frontend: `npm test -- --run src/notifications/__tests__/NotificationContext.test.tsx`

### Risks
- Interaction pause must not break manual dismiss or queued notification sequencing.
- Focus handling must not leave the snackbar permanently paused after focus moves away.

### Status
completed

## Remove Legacy Extraction Layer

Eliminate the legacy separate extraction/review object and keep `relation` as the
single source-grounded assertion type, with source/reference provenance carried by
relations and their revisions.

### Objective
Simplify the extraction and review model so user-facing workflows operate on
entities and relations only. LLM output should be normalized into
relation payloads instead of flowing through separate legacy contracts, review
types, and UI concepts.

### Impacted modules
- `backend/app/api/extraction.py`
- `backend/app/schemas/extraction.py`
- `backend/app/schemas/staged_extraction.py`
- `backend/app/llm/schemas.py`
- `backend/app/services/extraction_service.py`
- `backend/app/services/batch_extraction_orchestrator.py`
- `backend/app/services/document_extraction_processing.py`
- `backend/app/services/extraction_review_service.py`
- `backend/app/services/extraction_review/materialization.py`
- `backend/app/services/extraction_review/queries.py`
- `frontend/src/types/extraction.ts`
- `frontend/src/api/extractionReview.ts`
- extraction/review frontend components and focused tests
- focused backend extraction/review tests

### Assumptions
- The safest first slice is to remove the legacy third extraction type from user-facing extraction and review
  contracts while preserving compatibility for legacy rows where needed.
- Extracted statement text can be represented as a relation with participant roles plus
  structured provenance in `notes`, `scope`, and evidence-context metadata.
- Existing inference logic can remain relation-based in this task; deeper doc/math
  terminology cleanup can follow separately.

### Plan
1. Remove legacy request/response and review enum exposure from typed backend/frontend contracts.
2. Normalize extracted statement payloads into relation payloads before they reach preview/review flows.
3. Simplify staged extraction handling and stats so only entity/relation items are exposed.
4. Update UI copy/tests to remove the separate legacy extraction concept from extraction/review screens.
5. Run focused backend/frontend validation for extraction and review workflows.

### Validation
- Backend: focused pytest targets for extraction schemas/services and extraction review workflows
- Frontend: focused Vitest targets for extraction/review API clients and preview/review components

### Risks
- Legacy staged rows using the removed third extraction-type value are now migrated into relation-shaped staged rows; single-entity legacy rows will materialize as duplicated-role `other` relations if a reviewer approves them.
- Existing production data outside staged extractions was not schema-migrated in this task because those records were already materialized as relations.

### Status
completed

## Add Bounded Chunked Extraction For Long Documents

Improve automatic extraction coverage on long papers and dense web pages by running
bounded chunk-level extraction and merging the results deterministically instead of
relying on one large prompt over the entire truncated document body.

### Objective
Increase recall on long sources without weakening provenance or flooding the graph
with duplicate entities and relations. Long documents should be processed in
chunk-sized passes with overlap and stable merge rules.

### Impacted modules
- `backend/app/services/batch_extraction_orchestrator.py`
- `backend/app/services/extraction_service.py`
- `backend/tests/test_batch_extraction_orchestrator.py`
- focused extraction workflow tests if orchestrator behavior changes at integration boundaries

### Assumptions
- The biggest remaining extraction-quality gap is document coverage, not one more
  prompt wording tweak.
- Chunking should stay bounded in cost and latency; a small maximum chunk count is
  better than unbounded fan-out.
- Existing entity and relation merge rules are good enough for a first chunking
  slice if overlap is modest and relation dedupe remains conservative.

### Plan
1. Add bounded chunk splitting to the batch orchestrator with sentence/paragraph-aware boundaries and small overlap.
2. Run the existing batch extraction flow per chunk and merge entities/relations across chunks with stable dedupe.
3. Keep the single-pass path for short texts unchanged.
4. Add focused regression tests for multi-chunk coverage, overlap dedupe, and bounded tail coverage.
5. Run targeted backend pytest coverage for batch extraction orchestration and affected extraction workflow paths.

### Validation
- Backend: `cd backend && uv run pytest tests/test_batch_extraction_orchestrator.py tests/test_document_extraction_workflow.py -q`

### Risks
- Overlap that is too small may miss findings near chunk boundaries.
- Overlap that is too large may increase duplicate candidate volume and latency.
- If chunk merge keys are too coarse, distinct repeated findings from different
  sections could collapse into one extracted relation.

### Status
completed

## Add Role-Level Source Mentions To Extraction

Improve extraction fidelity by capturing the exact local mention for each relation
participant, then using those mentions during validation so abbreviation-heavy and
alias-heavy study text grounds more reliably.

### Objective
Make automatic extraction more precise by requiring or strongly preferring each
relation role to carry a short exact source mention from the relation span, while
keeping the contract backward-compatible for older staged rows and saved previews.

### Impacted modules
- `backend/app/llm/prompts.py`
- `backend/app/llm/schemas.py`
- `backend/app/services/extraction_text_span_validator.py`
- `backend/tests/test_llm_prompts.py`
- `backend/tests/test_llm_schemas.py`
- `backend/tests/test_extraction_validation.py`
- `frontend/src/types/extraction.ts`

### Assumptions
- The extraction contract can safely grow with an optional role mention field without
  breaking existing previews or staged extraction rows.
- Role-level mentions will improve grounding for abbreviations and aliases more
  effectively than trying to infer every variant from the entity summary alone.
- The prompt should strongly prefer exact shortest mentions, but the validator must
  still support older payloads that do not include them.

### Plan
1. Extend extracted relation roles with an optional exact local source mention field.
2. Update relation and batch prompts to require or strongly prefer per-role mentions.
3. Improve local grounding to use role mentions first, then fallback mention variants derived from entity text spans and slugs.
4. Add focused regression tests for abbreviation grounding and backward-compatible schema handling.
5. Run targeted backend pytest coverage for prompts, schemas, and extraction validation.

### Validation
- Backend: `cd backend && uv run pytest tests/test_llm_prompts.py tests/test_llm_schemas.py tests/test_extraction_validation.py -q`

### Risks
- Prompt strictness could reduce recall if the model skips a relation when it cannot
  easily emit every role mention.
- Some valid spans use pronouns or shorthand that still require fallback grounding
  beyond the explicit role mention field.
- Frontend extraction types must remain backward-compatible because older API
  responses will not include the new field.

### Status
completed

## Tighten Relation Semantic Validation In Extraction

Strengthen extraction-time relation validation so bad semantic shapes are rejected
before preview/save, especially around collapsed multi-outcome findings, comparator
hitchhiking, and polarity values that do not map cleanly into inference.

### Objective
Improve extraction quality by validating not just that a relation span exists, but
that the relation type, role mix, role participants, and stored polarity are
semantically coherent with the claimed source span and with downstream inference.

### Impacted modules
- `backend/app/services/extraction_text_span_validator.py`
- `backend/app/services/extraction_validation_service.py`
- `backend/app/services/document_extraction_processing.py`
- `backend/app/llm/schemas.py`
- `backend/app/services/bulk_creation_service.py`
- focused backend extraction workflow and validation tests

### Assumptions
- The highest-value next step is stricter validation, not another prompt rewrite.
- Relation-local participant grounding can be implemented conservatively by checking
  that core and contextual role participants are justified by the relation span or a
  tightly matched local excerpt, rather than anywhere in the document.
- Inference should continue to use canonical stored directions
  `supports` / `contradicts` / `neutral`; richer extraction polarity can remain in
  `evidence_context`.

### Plan
1. Trace the current structural validation path and define the smallest new semantic checks that belong there.
2. Add relation-local participant grounding checks so comparator, population, and target roles cannot hitchhike from unrelated spans.
3. Tighten relation-shape rules for core finding types so collapsed multi-target findings are flagged and split upstream instead of passing validation.
4. Normalize extracted polarity to canonical stored direction values while preserving rich `finding_polarity` in `evidence_context`.
5. Add focused regression tests using real bad-shape examples from study extraction failures.
6. Run targeted backend pytest coverage for validation, extraction preview, and save/materialization paths.

### Validation
- Backend: `cd backend && uv run pytest tests/test_extraction_validation.py tests/test_document_extraction_workflow.py tests/test_extraction_review_service.py -q`
- Backend: add/update focused tests for relation-local participant grounding and direction normalization

### Risks
- Over-strict local grounding may reject valid relations when the source uses pronouns,
  abbreviations, or nearby shorthand instead of repeating every participant name.
- Shape constraints must still allow legitimate combination-therapy relations with
  multiple agent roles.
- Direction normalization must not hide `mixed` or `uncertain` extraction context in
  the saved relation scope payload.

### Status
completed

## Verify Gleaning Loop Runs on Document Extraction Path

Investigate whether the multi-turn gleaning loop is actually executed during
document/URL extraction, or only on some paths. The fibromyalgia SSRI meta-analysis
extraction missed a statistically significant QOL finding (SMD -0.30, p=0.02,
5 RCTs, n=301) that a genuine second pass should have surfaced.

### Objective
Confirm the gleaning loop fires for document extraction and that its second-pass
prompt is specific enough to recover missed statistical findings.

### Impacted modules
- `backend/app/services/batch_extraction_orchestrator.py`
- `backend/app/services/document_extraction_processing.py`

### Assumptions
- The gleaning loop task was marked completed but may not be wired into the
  document extraction path, only into a different extraction entry point.
- If it is wired in, the follow-up prompt may not be specific enough to recover
  missed outcome findings.

### Plan
1. Trace the document extraction call path end-to-end and confirm whether the
   orchestrator invokes a second LLM pass.
2. If the loop is missing from this path, wire it in.
3. If it is present but ineffective, tighten the follow-up prompt to explicitly
   ask for missed outcome findings and missed statistical results.
4. Add a regression test with a dense multi-outcome abstract to verify recovery.

### Validation
- Backend: trace logs or add a temporary probe to confirm second-pass invocation
- Backend: focused pytest for orchestrator gleaning path

### Risks
- Adding a second pass to document extraction increases latency and cost.
- An overly broad follow-up prompt can introduce noise rather than recovering
  genuine misses.

### Status
pending

---

## Prune Orphan Entities After Extraction

Remove extracted entities that participate in zero extracted relations before
the preview/save step. Entities with no relation participation add noise to the
review queue and pollute the knowledge graph with unanchored concepts.

Observed in practice: `fatigue` and `cognitive-difficulties` extracted from a
fibromyalgia meta-analysis as background-mention entities with no relations.

### Objective
Keep the extraction result set clean by dropping entities that are provably
unused after the full extraction pass, without discarding entities that would
be valid if a missed relation were later recovered.

### Impacted modules
- `backend/app/services/batch_extraction_orchestrator.py`
- `backend/app/services/document_extraction_processing.py`
- `backend/tests/test_document_extraction_workflow.py`

### Assumptions
- An entity is orphaned if no extracted relation references its slug in any role.
- Pruning should happen after all extraction passes (including gleaning) so
  entities recovered by a second pass are not incorrectly removed.
- The `fibromyalgia` entity matched an existing KB entity and should never be
  pruned even if no new relation was extracted for it in this batch.
- Linked entities (matched to existing KB records) should be exempt from pruning
  since they may already participate in stored relations.

### Plan
1. After the final extraction pass, collect the set of entity slugs referenced
   by at least one relation role.
2. Remove from the entity list any entity whose slug is not in that set and which
   is not a linked/existing-KB entity.
3. Log pruned entity slugs for debugging.
4. Add focused regression tests: orphan pruning removes background-mention
   entities, linked entities are exempt, entities used in gleaned relations
   are retained.

### Validation
- Backend: focused pytest for document extraction orchestration

### Risks
- If the gleaning loop has not run yet, orphan pruning may discard entities that
  the second pass would have linked. Always prune after all passes.
- Linked entities must be exempt because their KB participation is not visible
  in the current extraction batch.

### Status
pending

---

## Propagate Document-Level Study Type to All Extracted Relations

When a document title or abstract identifies it as a meta-analysis, systematic
review, or guideline, all extracted relations should inherit that study type as
their `study_design` instead of each relation independently re-inferring it.

Observed failure: a meta-analysis of 9 RCTs had its main relation labelled
`randomized_controlled_trial`, corrupting downstream evidence weighting.

### Objective
Eliminate the class of errors where individual relation study_design fields
contradict the document's own declared methodology.

### Impacted modules
- `backend/app/llm/prompts.py`
- `backend/app/services/batch_extraction_orchestrator.py`
- `backend/app/services/document_extraction_processing.py`
- `backend/tests/test_llm_prompts.py`
- `backend/tests/test_document_extraction_workflow.py`

### Assumptions
- Document-level study type can be reliably inferred from the title/abstract
  using a short classification step before the main extraction prompt.
- Injecting the inferred study type as a constraint into the relation extraction
  prompt is safer than a post-processing override, because it lets the model
  preserve per-relation nuance (e.g. one background statement inside a
  meta-analysis may still be `background`).
- The classification step should be a lightweight prompt or heuristic, not a
  full extraction pass.

### Plan
1. Add a short pre-classification step in the orchestrator that reads the
   document title and first 300–500 characters of abstract and returns a
   `study_design` label.
2. Inject the classified study type into the batch extraction prompt as a
   document-level constraint: "This document is a meta-analysis. Prefer
   study_design=meta_analysis for primary findings unless a span clearly
   indicates a different design."
3. Add a focused test: meta-analysis document produces `meta_analysis`
   study_design on primary finding relations.

### Validation
- Backend: focused pytest for document extraction orchestration and prompts

### Risks
- Pre-classification can mis-classify mixed-design documents (e.g. an RCT paper
  that includes a mini meta-analysis in the discussion).
- Injecting a document-level constraint may suppress legitimate per-relation
  design variation.

### Status
pending

---

## Propagate Author-Stated Evidence Quality to Evidence Strength

When a source explicitly states that evidence quality is low or very low
(e.g. GRADE assessment, author conclusion), that caveat should prevent
`evidence_strength` from being assigned `strong` or `moderate` based solely
on statistical significance.

Observed failure: a meta-analysis explicitly concluding "overall evidence quality
was very low to low due to heterogeneity and risk of bias" had its main relation
assigned `evidence_strength: strong`.

### Objective
Make `evidence_strength` reflect the author's own methodological assessment,
not just the presence of a p-value.

### Impacted modules
- `backend/app/llm/prompts.py`
- `backend/tests/test_llm_prompts.py`

### Assumptions
- The author-stated quality assessment is usually in the conclusion or
  limitations section and is extractable as a short span.
- The safest prompt fix is an explicit rule: if the source states low or very
  low evidence quality, cap `evidence_strength` at `weak` regardless of the
  statistical result.
- This is a prompt-only change; no schema migration is needed.

### Plan
1. Add a rule to the relation extraction and batch prompts: if the source
   explicitly states that evidence quality is low, very low, or insufficient
   (e.g. GRADE low/very low, high risk of bias, heterogeneity concerns), cap
   evidence_strength at weak even if the statistical result is significant.
2. Add a focused prompt regression test: a passage with a significant p-value
   but explicit quality caveat should produce evidence_strength=weak.

### Validation
- Backend: `cd backend && uv run pytest tests/test_llm_prompts.py -q`

### Risks
- Authors sometimes over-state quality concerns in conclusions while the
  individual studies are genuinely robust. The rule should apply only when
  the caveat is explicit and document-level.
- Adding this rule may reduce strength assignment on borderline papers that
  use hedged language without a formal quality rating.

### Status
pending

---

## Enforce Named Comparator Entity Extraction

When a relation span explicitly names a comparator or control group participant,
require that entity to be extracted. Currently named comparators are left out if
the entity list is incomplete, producing structurally incomplete relations.

Observed failure: a relation referencing "acupuncture and aerobic exercise" as
comparators had no corresponding entities extracted, leaving the control_group
role unresolvable.

### Objective
Ensure that every named participant in an extracted relation — including
comparators and control groups — has a corresponding entity in the extraction
result, so relations are structurally complete before preview/save.

### Impacted modules
- `backend/app/services/extraction_validation_service.py`
- `backend/app/services/extraction_text_span_validator.py`
- `backend/app/llm/prompts.py`
- `backend/tests/test_extraction_validation.py`

### Assumptions
- A named comparator that appears in a relation's `text_span` but has no
  matching entity in the extraction batch is a structural defect, not a
  valid extraction.
- The fix has two parts: a prompt reminder and a validation check.
- Validation should reject or flag relations where a named role participant
  has no corresponding entity record.

### Plan
1. Add a prompt rule: if a relation span names a comparator or control group
   (e.g. "compared to acupuncture", "versus aerobic exercise"), that entity
   MUST appear in the entities array; do not emit the relation without it.
2. Add a validation check: for each relation role slug, verify a matching
   entity exists in the batch or in the existing KB; flag relations with
   unresolvable named roles as incomplete.
3. Add focused regression tests for named-comparator resolution and the
   unresolvable-role flag.

### Validation
- Backend: `cd backend && uv run pytest tests/test_extraction_validation.py -q`

### Risks
- Strict enforcement may cause the model to omit relations it cannot fully
  ground, reducing recall on comparison-heavy study designs.
- Existing-KB lookup adds a round-trip; consider caching slug presence checks.

### Status
pending

---

## Build Relation Type Proposal Page

Allow curators to formally propose a new relation type when the model invents
one that isn't in the controlled vocabulary. Ensure no duplicate is created
by showing all existing types first, and use an LLM to challenge the need.

### Objective
Give curators a governed path from "the model used `coexists_with`" to either
reassigning to an existing type or creating a justified new one, with LLM
review acting as a first gatekeeping step.

### Background
The review queue already shows a "proposed: coexists_with" warning chip on
relations where the model invented a type. That chip links to
`/relation-types/propose?name=coexists_with`. This page needs to be built.

### Impacted modules
- `frontend/src/views/RelationTypeProposeView.tsx` (new)
- `frontend/src/api/relationTypes.ts` (new — existing types list + propose endpoint)
- `backend/app/api/relation_types.py` (new — GET list + POST propose + LLM evaluation)
- `backend/app/models/relation_type.py` (already has the right schema)
- `backend/app/llm/prompts.py` (new prompt: evaluate proposed type)
- `frontend/src/App.tsx` or router (add route `/relation-types/propose`)

### Plan
1. Add `GET /api/relation-types` backend endpoint returning all active types with
   description, aliases, examples, and category.
2. Add `POST /api/relation-types/evaluate` endpoint that calls the LLM with the
   proposed name plus all existing types and returns one of:
   - `{ recommendation: "create", rationale: "..." }`
   - `{ recommendation: "reject", rationale: "...", suggested_existing: "treats" }`
   - `{ recommendation: "rename", rationale: "...", suggested_name: "diagnoses" }`
3. Add `POST /api/relation-types` (admin only) to create a new type row.
4. Build `RelationTypeProposeView`:
   - Show all existing types in a scrollable list with descriptions.
   - Only enable the "Propose" form after the user has scrolled to the bottom
     (or explicitly clicked "I have read all existing types").
   - Proposal form: name, description, example sentence, category.
   - On submit, call the evaluate endpoint and show the LLM recommendation
     prominently (green/yellow/red card) before any confirmation button.
   - If recommendation is "reject", show the suggested existing type as a link
     back to the review queue.
   - Admin-only "Create anyway" button visible regardless of recommendation.
5. Wire the route into the app router.

### LLM prompt shape
```
You are evaluating whether a new relation type should be added to a biomedical
knowledge graph. Existing types: {list with descriptions}.
Proposed type: "{name}" — "{description}".
Example: "{example}".

Respond with JSON: { "recommendation": "create"|"reject"|"rename",
  "rationale": "...", "suggested_existing": null|"<type>",
  "suggested_name": null|"<name>" }
```

### Validation
- Backend: focused pytest for relation-type list and evaluate endpoints
- Frontend: manual smoke-test of the scroll-gate, LLM card, and create flow

### Risks
- LLM recommendation is advisory, not blocking; admins can override.
- The scroll-gate is a soft UX constraint, not a security control.
- New types added here must also be added to the backend `RelationType` Literal
  and `ALL_RELATION_TYPES` frontend array to become extractable — document this
  as a separate manual step in the admin UI.

### Status
pending

---

## Run Benchmark Against Current gpt-5.4 Extraction Stack

Re-run the gold extraction benchmark now that the model, token limits,
validation normalizers, and relation types have all changed significantly.

### Objective
Get a current baseline score and identify the top remaining failure modes
before further prompt or schema work.

### Plan
1. `cd backend && uv run python scripts/run_extraction_eval.py --json`
2. Review case-by-case failures.
3. Add new benchmark cases for `diagnoses` and `predicts` relation types.
4. Open new TODO items for systematic failure patterns found.

### Validation
- Backend: `cd backend && uv run python scripts/run_extraction_eval.py --json`

### Status
pending

---

## Open Findings

If new defects are found, add them here as unchecked items with:
- ID
- file path and line number
- problem statement
- concrete fix

- [ ] `REL-AUD-001` `backend/app/services/extraction_review/materialization.py:74`, `backend/app/services/bulk_creation_service.py:169`, `backend/app/services/relation_service.py:57` — Relation creation still happens through multiple independent procedures with diverged mapping rules for confidence, provenance, notes/text-span fallback, and role snapshots. Consolidate all relation writes behind one shared persistence helper and add parity tests across manual, staged, and save-to-graph paths.
- [ ] `REL-AUD-002` `backend/app/services/document_extraction_processing.py:906` — Staged relation reconciliation matches only on relation type plus role set, so same-type/same-role duplicate findings from one source can be linked to the wrong created relation ID. Replace the coarse matcher with an exact contextual fingerprint or explicit ambiguity handling, and add regression tests for repeated-role findings.
- [ ] `REL-AUD-003` `backend/alembic/versions/023_remove_legacy_claim_extractions.py:55` — Legacy removed-type rows are silently converted into synthetic generic relations, including duplicated self-roles for single-entity rows, and can still flow through normal review. Quarantine or explicitly rewrite these legacy rows before they enter standard relation approval/materialization.

---

## Defects Requiring Fixes

| ID | Severity | File | Description |
|----|----------|------|-------------|
| None | — | — | No open defects. |

---

## Post-v1.0 Backlog

Do not implement unless specifically asked.

- **Graph visualization** — Explicitly not MVP.
- **TypeDB integration** — Optional reasoning engine.
- **Advanced auth** — 2FA (TOTP), OAuth providers (Google, GitHub).
- **Real-time collaboration** — WebSocket/SSE for live updates.
- **Multi-tenancy / RBAC** — Organization model, role-based access control.
