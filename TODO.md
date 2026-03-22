# Current Work

**Last updated**: 2026-03-22 (ORM audit — all findings resolved)

---

## Open Findings

_(none — ORM audit C1/M1/M2/m1–m4 all resolved 2026-03-22)_

---

## Deferred Items

From completed audits — low priority, no blocking risk.

- **Entity legacy fields** (kind, label, synonyms, ontology_ref on `EntityRead`) — still consumed as fallbacks in 10+ frontend files; cannot retire until frontend migrates to slug+summary exclusively.
- **subject_slug / object_slug on `ExtractedRelation`** — still used in CSV export and LLM backward-compat path; documented deprecated, cannot retire yet.
- **Rejected-extraction visibility** (Audit 20 M4) — no `rejection_flagged` column; rejected extractions remain visible with status="rejected". Defer until a post-v1.0 moderation sprint.
- **Plaintext reset/verification token storage** (Audit 22) — low risk given short expiry + single-use; defer post-v1.0.
- **Expired refresh token purge** (Auth audit m2) — old expired/revoked rows accumulate in `refresh_tokens`; add a periodic cleanup job post-v1.0.
- **Cross-tab refresh lock busy-wait** (Auth audit m3) — `client.tsx` polls every 100 ms; replace with `StorageEvent` listener post-v1.0.
- **LLM singleton not invalidated on key rotation** (LLM audit m3) — `_llm_provider` in `llm/client.py` persists across API key changes; restart required. Add `reset_llm_provider()` for tests post-v1.0.

---

## Post-v1.0 Backlog

- **Graph visualization** — Explicitly not MVP.
- **TypeDB integration** — Optional reasoning engine.
- **Advanced auth** — 2FA (TOTP), OAuth providers (Google, GitHub).
- **Real-time collaboration** — WebSocket/SSE for live updates.
- **Multi-tenancy / RBAC** — Organization model, role-based access control.

---

## Audit Reports Index

- `.temp/audit_entity_creation_2026-03-22.md`
- `.temp/audit_relation_creation_2026-03-22.md`
- `.temp/audit_llm_integration_2026-03-22.md`
- `.temp/audit_relation_extraction_2026-03-22.md`
- `.temp/audit_login_2026-03-22.md`
- `.temp/audit_payload_flows_2026-03-21.md`
- `.temp/full_audit_report_2026-03-21b.md`
- `.temp/full_audit_report_2026-03-21_prev.md`
- `.temp/audit_inference_pipeline_2026-03-21.md`
- `.temp/audit_smart_discovery_2026-03-22.md`
- `.temp/audit_orm_2026-03-22.md`
- `.temp/audit_database_operations_2026-03-22.md`
- `.temp/audit_smart_discovery_2026-03-20.md`
- `.temp/full_audit_report_2026-03-18.md`
- `.temp/knowledge_integrity_report_v1.md`
- `.temp/revision_architecture_provenance_report_v1.md`
- `.temp/security_authentication_report_v2.md`
- `.temp/api_service_boundary_report_v2.md`
- `.temp/dead_code_compatibility_shims_report_v2.md`
- `.temp/typed_contract_discipline_report_v3.md`
- `.temp/test_suite_health_report_v2.md`
