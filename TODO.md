# Current Work

**Last updated**: 2026-04-19

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
planned

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
