# Current Work

**Last updated**: 2026-04-05 (story implementation pass)

## Open Findings

- [x] **STORY-NAV-M1** `frontend/src/components/layout/MobileDrawer.tsx:208` — `US-NAV-02` footer now shows signed-in user identity and profile access while preserving the language switcher. Verified by `frontend/src/components/__tests__/MobileDrawer.test.tsx`.
- [x] **STORY-NAV-m1** `frontend/src/components/Layout.tsx:35` — persistent navigation now includes an explicit Account entry matching `US-NAV-01`. Verified by `frontend/src/components/__tests__/Layout.test.tsx`.
- [x] **STORY-SRC-M1** `frontend/src/views/SourcesView.tsx:418` — sources list now exposes authority score and graph usage count from the API contract and renders them in list rows. Verified by `backend/tests/test_source_service.py` and `frontend/src/views/__tests__/SourcesView.test.tsx`.
- [x] **STORY-REL-M1** `frontend/src/views/RelationsView.tsx:5` — `/relations` is now a real relations index with export and batch-create entry points backed by a paginated relations API. Verified by `backend/tests/test_relation_endpoints.py` and `frontend/src/views/__tests__/RelationsView.test.tsx`.
- [x] **STORY-EXP-M1** `frontend/src/views/EvidenceView.tsx:89` — property evidence now exposes and sorts by source authority as required by `US-EXP-02`. Verified by `frontend/src/views/__tests__/EvidenceView.table.test.tsx`.

Completed `[x]` items from the previous tracker were reviewed against the current
codebase and removed once they appeared fully implemented and covered well
enough to stop acting as live TODOs.

If new defects are found, add them here as unchecked items with:
- ID
- file path and line number
- problem statement
- concrete fix

---

## Defects Requiring Fixes

| ID | Severity | File | Description |
|----|----------|------|-------------|
| None | — | — | No open defects currently listed in this section after the 2026-04-05 story implementation pass. Add new verified issues above before repopulating this table. |

---

## Post-v1.0 Backlog

Do not implement unless specifically asked.

- **Graph visualization** — Explicitly not MVP.
- **TypeDB integration** — Optional reasoning engine.
- **Advanced auth** — 2FA (TOTP), OAuth providers (Google, GitHub).
- **Real-time collaboration** — WebSocket/SSE for live updates.
- **Multi-tenancy / RBAC** — Organization model, role-based access control.
