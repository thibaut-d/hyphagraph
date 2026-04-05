# Current Work

**Last updated**: 2026-04-05 (story remediation pass)

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
