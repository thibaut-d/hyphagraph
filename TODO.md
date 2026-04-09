# Current Work

**Last updated**: 2026-04-08

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
evidence labels (`low`, `medium`, `high`) in relation or claim study metadata,
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

## Open Findings

If new defects are found, add them here as unchecked items with:
- ID
- file path and line number
- problem statement
- concrete fix

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
