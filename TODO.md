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
