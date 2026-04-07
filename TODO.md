# Current Work

**Last updated**: 2026-04-07 (source summary creation UX)

## Active Plan: Source Creation Summary UX

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
