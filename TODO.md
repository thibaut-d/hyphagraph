# Current Work

**Last updated**: 2026-03-22 (E2E test suite review — all findings resolved)

---

## Open Findings

### E2E Test Suite — Soundness and Coverage (2026-03-22)

Review identified systemic correctness problems and coverage gaps across the full E2E suite.
Source: E2E review session 2026-03-22.

#### Critical — false-positive tests (no failure mode)

- [x] **E2E-C1** `inferences/viewing.spec.ts:62-63` — "should navigate to inferences page" asserts `expect(url).toBeTruthy()`. Replace with `toHaveURL(/\/inferences/)` or a heading assertion.
- [x] **E2E-C2** `inferences/viewing.spec.ts:71-78` — "should filter inferences" has zero assertions. Add at minimum an assertion that the page still renders after attempting a filter interaction.
- [x] **E2E-C3** `explanations/trace.spec.ts:57-58` — "should display explanation trace" calls `.isVisible().catch(() => false)` with no `expect()`. Always passes. Add a real assertion or remove the test.
- [x] **E2E-C4** `auth/login.spec.ts:117-121` — "should redirect to account page when accessing protected route without auth" — `url.includes('account')` is always true after redirect; tautological. Assert login form visibility without the URL fallback.
- [x] **E2E-C5** `auth/register.spec.ts:55-62` — "should show error when registering with invalid email" only checks the URL. Add an assertion that a validation error message is visible.
- [x] **E2E-C6** Eliminate pervasive conditional-test anti-pattern — `if (await x.isVisible()) { await expect(x).toBeVisible() }` throughout `entities/filters.spec.ts`, `sources/filters.spec.ts`, `relations/export.spec.ts`, `sources/export.spec.ts`, `relations/batch.spec.ts`, `review-queue/queue.spec.ts`. Each of these silently passes when the feature is absent. Replace with direct assertions backed by API-seeded preconditions.

#### Critical — structural defects

- [x] **E2E-C7** `relations/edit-delete.spec.ts` — if API relation creation fails in `beforeEach`, `relationId` is `''` and all tests skip silently. Replace silent skip with a thrown error so broken setup is visible.
- [x] **E2E-C8** `relations/crud.spec.ts:138-156` — "should remove roles from relation" iterates all buttons looking for those with no text/aria-label to find a delete button. This is fragile and documents an accessibility defect. Add `aria-label="Remove role"` to delete IconButtons in the relation form, then update the test to use `getByRole('button', { name: /remove role/i })`.

#### Major — weak or misleading assertions

- [x] **E2E-M1** `auth/register.spec.ts:64-81` — weak-password test matches the Zod internal key `string_too_short`. Require a user-facing message instead (e.g. "at least 8 characters").
- [x] **E2E-M2** `auth/login.spec.ts:55-64` — "should show error with empty credentials" only checks the URL. Assert that the login button is still visible and no auth token was set.
- [x] **E2E-M3** `relations/edit-delete.spec.ts:98-118` — test is titled "should save a relation update and create a new revision" but never verifies a new revision exists. Add an API call or UI check that confirms revision count increased.
- [x] **E2E-M4** `account/settings.spec.ts:84-129` — "should successfully change password for a test user" silently returns (passes) if the newly registered user cannot log in due to email verification requirements. Add an explicit skip or assertion that makes the precondition failure visible.
- [x] **E2E-M5** `inferences/viewing.spec.ts:16-54` — "should view inferences on entity detail page" creates two entities but no relation, so inference computation is never triggered. Add an API-seeded relation between the entities before navigating to the detail page.
- [x] **E2E-M6** `entities/crud.spec.ts:113-114` — `waitForTimeout(1000)` before delete click. Replace with `waitForLoadState('networkidle')` or a condition on a specific element.
- [x] **E2E-M7** `sources/crud.spec.ts:114-117` — delete confirmation `getByRole('button', { name: /confirm|yes|delete/i })` is unscoped and could match the wrong button. Scope to `locator('[role="dialog"]')` as `entities/crud.spec.ts` correctly does.
- [x] **E2E-M8** `entities/crud.spec.ts` — missing `afterEach` with `clearAuthState`. Add it for consistency with all other suites.
- [x] **E2E-M9** `relations/batch.spec.ts:59` — source creation in the batch test fills `summary.*english` which is inside a collapsed "Advanced" section. Remove that fill (title + URL are sufficient, per `sources/crud.spec.ts`).
- [x] **E2E-M10** `document-upload.spec.ts:64-81` — 60-second LLM-dependent assertion. Either mock the extraction API response or mark the test as requiring LLM availability and move it to a separate slow suite.
- [x] **E2E-M11** `relations/crud.spec.ts` — heavy `beforeEach` creates source + 2 entities for every test including ones that don't need them (e.g. "should view relations list"). Move resource creation to only the tests that require it, or use a `beforeAll` with API calls.

#### Coverage gaps — missing tests

- [x] **E2E-G1** **Token refresh flow** — no test exercises `refresh_token`. Add a test that sets an expired `auth_token` (or clears it while keeping `refresh_token`) and verifies the app silently re-authenticates.
- [x] **E2E-G2** **Contradiction visibility** — core HyphaGraph invariant has zero E2E coverage. Add a test: create two relations with contradictory claims for the same entity+role, navigate to the entity detail or disagreements page, and assert both are visible and neither is suppressed.
- [x] **E2E-G3** **Entity and relation revision history** — edits are tested at the UI level but no test verifies a new revision was persisted. Add post-edit API checks or UI assertions that show a revision history entry was created.
- [x] **E2E-G4** **Disagreements with real contradictory data** — all `disagreements/viewing.spec.ts` tests create fresh entities with no relations; only the empty-state path is exercised. Add a test with API-seeded contradictory relations that asserts actual disagreement groups are displayed.
- [x] **E2E-G5** **Non-admin frontend authorization** — `admin/panel.spec.ts` tests the API 403 but no test verifies what a regular-user session sees when accessing admin-restricted UI surfaces.
- [x] **E2E-G6** **Pagination correctness** — existing pagination tests only click "next" if visible; no test asserts that page 2 data differs from page 1.
- [x] **E2E-G7** **Export content correctness** — export tests confirm a download event fires and the filename extension is correct; no test validates the file's actual contents.
- [x] **E2E-G8** **Email verification flow** — registration tests acknowledge verification may be required but no test exercises the verification link or confirms the post-verification login state.
- [x] **E2E-G9** **Unknown ID 404 handling** — no test navigates to `/entities/00000000-0000-0000-0000-000000000000` or a similar non-existent ID and asserts a user-facing not-found state.

#### Minor / docs inconsistency

- [x] **E2E-m1** `playwright.config.ts` — comment says "English only (no i18n testing)" but `i18n/language-switch.spec.ts` exists and runs. Update the comment.
- [x] **E2E-m2** `playwright.config.ts` — Firefox and WebKit projects are commented out; `E2E_TESTING_GUIDE.md` lists all three browsers as active. Either enable them or update the guide.
- [x] **E2E-m3** `auth/register.spec.ts:83-106` — "should allow login after successful registration" uses `expect(loggedIn || needsVerification).toBeTruthy()`. The `needsVerification` text could match unrelated page content. Tighten the locator or split into two tests for the verified and unverified paths.

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

- `.temp/audit_entity_write_flow_2026-03-22.md`
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
