# Current Work

**Last updated**: 2026-04-07 (auto-extract preview visibility)

## Active Plan: Auto-Extract Preview Visibility

### Objective
Make the source detail auto-extract action visibly surface extraction results when the preview is inserted above the current extraction controls.

### Impacted modules
- `frontend/src/views/SourceDetailView.tsx`
- `frontend/src/views/__tests__/SourceDetailView.rendering.test.tsx`
- `frontend/src/components/source-detail/__tests__/SourceExtractionSection.test.tsx`

### Assumptions
- The primary URL extraction handler is callable, but its preview is rendered above the extraction controls and can be outside the current viewport.
- The correct fix is to reveal the produced review UI, not to add a second extraction pathway.

### Plan
1. Add an explicit preview scroll target to `SourceDetailView`.
2. Scroll the preview into view whenever a new extraction preview is set.
3. Stabilize source-detail rendering assertions that depended on relation accordions already being expanded.
4. Add regression coverage for the primary auto-extract URL button.
5. Run targeted frontend validation.

### Validation
- `cd frontend && npm test -- --run src/views/__tests__/SourceDetailView.rendering.test.tsx src/components/source-detail/__tests__/SourceExtractionSection.test.tsx`
- `cd frontend && npm run build`
- `git diff --check`

### Risks
- Automatic scrolling should only run when a preview exists so normal source page load and relation deep-link behavior remain unchanged.
- If the backend returns an error, the existing error notification path should remain the only failure surface.

### Status
validated

## Previous Plan: N-ary Extraction Relation Context

### Objective
Make extracted relations reflect HyphaGraph hyperedges by preserving explicitly stated contextual roles and previewing all roles as first-class relation context.

### Impacted modules
- `backend/app/llm/prompts.py`
- `backend/tests/test_llm_prompts.py`
- `frontend/src/components/ExtractedRelationsList.tsx`
- `frontend/src/components/__tests__/ExtractedRelationsList.test.tsx`

### Assumptions
- The backend schema and relation materialization already support more than two roles.
- The current issue is that extraction guidance and preview rendering still bias toward binary subject/object relations.
- Extra contextual roles must only be extracted when explicitly present in the source span.

### Plan
1. Strengthen relation and batch prompts to ask for n-ary hyperedges when source text includes population, comparator, outcome, dosage, duration, mechanism, or study context.
2. Ensure contextual role fillers are also extracted as entities with valid slugs, including prefixed numeric slugs such as `dose-60mg-daily`.
3. Keep the evidence-first guard against adding unstated contextual roles.
4. Render extracted relation roles directly instead of subject/object plus additional roles.
5. Add focused prompt and frontend display regression coverage.
6. Run targeted backend/frontend validation.

### Validation
- `docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml exec -T api uv run pytest tests/test_llm_prompts.py`
- `cd frontend && npm test -- --run src/components/__tests__/ExtractedRelationsList.test.tsx`
- `cd frontend && npm test -- --run src/components/__tests__/ExtractionPreview.test.tsx src/views/__tests__/SourceDetailView.rendering.test.tsx`
- `cd frontend && npm run build`
- `git diff --check`

### Risks
- Prompt changes can encourage over-extraction if they are not explicitly bounded to source-stated context.
- Preview changes must not break binary relations; binary relations should render as a two-role hyperedge.

### Status
validated

## Previous Plan: Mobile Extraction Preview UX

### Objective
Keep extraction review and source quality/trust metadata usable on small screens without hiding important evidence signals.

### Impacted modules
- `frontend/src/components/ExtractionPreview.tsx`
- `frontend/src/components/EntityLinkingSuggestions.tsx`
- `frontend/src/components/ExtractedRelationsList.tsx`
- `frontend/src/components/source-detail/SourceMetadataSection.tsx`
- `frontend/src/components/source-detail/SourceVerificationSummary.tsx`
- `frontend/src/views/__tests__/SourceDetailView.rendering.test.tsx`
- `frontend/src/views/__tests__/SourceDetailView.test-support.tsx`

### Assumptions
- The issue is responsive layout rather than missing data.
- The quality/trust metadata should remain visible on mobile and should wrap instead of being clipped.
- Compact extraction tables are too dense for phones; mobile should use card review only.

### Plan
1. Make extraction preview padding, stats, quick-save, and action rows responsive.
2. Make extracted entity and relation cards wrap chips/actions instead of squeezing content.
3. Hide compact entity table mode on narrow screens and use card review there.
4. Make source metadata and verification summary wrap trust/quality chips on small screens.
5. Update focused tests and run targeted frontend validation.

### Validation
- `cd frontend && npm test -- --run src/components/__tests__/ExtractionPreview.test.tsx`
- `cd frontend && npm test -- --run src/components/__tests__/ExtractionPreview.test.tsx src/views/__tests__/SourceDetailView.rendering.test.tsx`
- `cd frontend && npm run build`
- `git diff --check`

### Risks
- Desktop table mode remains available, but mobile review should avoid dense columns.
- Changing responsive wrapping must not remove or conditionally hide trust/quality signals.

### Status
validated

## Previous Plan: Empty Extraction Root-Cause Fix

### Objective
Prevent blank fetched documents from being stored and extracted as valid zero-item previews, while preserving PubMed abstract text when optional PMC enrichment returns an empty body.

### Impacted modules
- `backend/app/services/pubmed_fetcher.py`
- `backend/app/services/document_extraction_processing.py`
- `backend/tests/test_pubmed_fetcher.py`
- `backend/tests/test_document_extraction_workflow.py`
- `frontend/src/components/ExtractionPreview.tsx`
- `frontend/src/i18n/en.json`
- `frontend/src/i18n/fr.json`
- `frontend/src/components/__tests__/ExtractionPreview.test.tsx`

### Assumptions
- The juvenile fibromyalgia source had a source summary, but its stored extraction document body was empty.
- PubMed abstract text is preferable to replacing the document body with empty PMC enrichment output.
- Blank fetched document text is a fetch/parsing failure, not a legitimate extraction input.
- The UI must not present an empty extraction as high-confidence or quick-saveable.

### Plan
1. Guard high-confidence frontend logic so it only applies when the preview contains extracted items.
2. Add an explicit empty-state alert and suppress save/quick-save affordances for empty previews.
3. Preserve PubMed abstract text when PMC enrichment returns empty text.
4. Reject blank fetched URL/PubMed document text before storing the document or running extraction.
5. Add focused frontend and backend regression coverage.

### Validation
- `cd frontend && npm test -- --run src/components/__tests__/ExtractionPreview.test.tsx`
- `docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml exec -T api uv run pytest tests/test_pubmed_fetcher.py tests/test_document_extraction_workflow.py`
- `docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml exec -T api uv run ruff check app/services/pubmed_fetcher.py app/services/document_extraction_processing.py tests/test_pubmed_fetcher.py tests/test_document_extraction_workflow.py`
- `cd frontend && npm run build`
- `git diff --check`

### Risks
- Existing translations must remain valid JSON.
- Relation-only previews should still be reviewable and saveable if relation creation is supported by linked entities.
- The backend now returns a validation error for empty fetched text, so the frontend error path must surface the error instead of showing a preview.

### Status
validated

## Previous Plan: Source Creation Summary UX

### Objective
Align source creation summary entry with the more capable entity creation summary editor.

### Impacted modules
- `frontend/src/hooks/useCreateSourceForm.ts`
- `frontend/src/views/CreateSourceView.tsx`
- `frontend/src/views/__tests__/CreateSourceView.test.tsx`

### Assumptions
- The source API already accepts `summary` as a language-keyed map.
- This is a frontend-only UX/payload construction change.
- Existing URL metadata extraction should keep preserving English and French summaries when returned.

### Plan
1. Store source creation summaries as a language-keyed map.
2. Render one language-selectable summary field with filled-language chips.
3. Submit all filled summaries in the payload.
4. Update focused component tests and run targeted validation.

### Validation
- `cd frontend && npm test -- --run src/views/__tests__/CreateSourceView.test.tsx`
- `cd frontend && npm test -- --run src/views/__tests__/CreateEntityView.test.tsx src/views/__tests__/CreateSourceView.test.tsx`
- `git diff --check`

### Risks
- Source metadata autofill could regress if extracted summaries are not merged into the new map.
- Test selectors that expected fixed English/French fields need to follow the new language-selector workflow.

### Status
validated

## Previous Plan: Slug Entity URLs

### Objective
Use current entity slugs as canonical public entity URLs while keeping UUID URLs working for compatibility.

### Impacted modules
- `backend/app/api/entities.py`
- `backend/app/api/inferences.py`
- `backend/app/api/explain.py`
- `backend/app/services/entity_service.py`
- `backend/app/repositories/entity_repo.py`
- `frontend/src/views/`
- `frontend/src/components/`
- `frontend/src/hooks/`
- targeted backend/frontend tests

### Assumptions
- Current entity revision slugs are unique and safe as human-facing identifiers.
- UUIDs remain the internal identifier for writes, entity terms, and deletion.
- Slug lookup must not change inference computation, evidence visibility, or revision provenance.

### Plan
1. Add backend current-slug lookup and ref resolution.
2. Accept either UUID or slug for read/inference/explanation endpoints.
3. Generate entity links with slugs where slug data is available.
4. Resolve slug routes to UUIDs before frontend mutation or term operations.
5. Add focused regression coverage and run targeted checks.

### Validation
- Backend pytest for entity endpoints and inference/explanation affected paths.
- Frontend Vitest for entity detail, edit, list/search/link generation, and affected evidence/synthesis navigation.
- `git diff --check`.

### Risks
- Frontend/backend contract drift if a route starts passing slugs to UUID-only write endpoints.
- Evidence filtering can break if route slug is compared to relation `entity_id`; resolved UUID must be used there.

### Status
validated

## Open Findings

- [x] **STORY-REL-M2** `frontend/src/views/CreateRelationView.tsx:146` — successful relation creation now navigates to the created relation detail page. Verified by `frontend/src/views/__tests__/CreateRelationView.test.tsx`.
- [x] **STORY-REL-M3** `frontend/src/views/RelationDetailView.tsx:189` — relation detail now exposes delete with confirmation, satisfying the direct-detail delete flow. Verified by `frontend/src/views/__tests__/RelationDetailView.test.tsx`.
- [x] **STORY-REL-m4** `frontend/src/views/RelationDetailView.tsx:302` — relation detail now surfaces `created_with_llm` / `llm_review_status` in the audit section when present. Verified by `frontend/src/views/__tests__/RelationDetailView.test.tsx`.
- [x] **STORY-ADM-m1** `frontend/src/components/SuperuserRoute.tsx:17` — authenticated non-superusers now receive an explicit forbidden state instead of a silent redirect. Verified by `frontend/src/components/__tests__/ProtectedRoute.test.tsx`.
- [x] **STORY-I18N-m1** `frontend/src/views/CreateSourceView.tsx:123` — create-source placeholders now route through translation keys instead of hardcoded English literals. Verified by `frontend/src/views/__tests__/CreateSourceView.test.tsx`.

If new defects are found, add them here as unchecked items with:
- ID
- file path and line number
- problem statement
- concrete fix

---

## Defects Requiring Fixes

| ID | Severity | File | Description |
|----|----------|------|-------------|
| None | — | — | No open defects currently listed in this section after the 2026-04-05 story remediation pass. Add new verified issues above before repopulating this table. |

---

## Post-v1.0 Backlog

Do not implement unless specifically asked.

- **Graph visualization** — Explicitly not MVP.
- **TypeDB integration** — Optional reasoning engine.
- **Advanced auth** — 2FA (TOTP), OAuth providers (Google, GitHub).
- **Real-time collaboration** — WebSocket/SSE for live updates.
- **Multi-tenancy / RBAC** — Organization model, role-based access control.
