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
