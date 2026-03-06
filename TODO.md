# Current Work

**Last updated**: 2026-03-06

Frontend/backend contract alignment and runtime fix pass completed.

---

## Completed

1. Extraction client alignment: removed `/api/api` path duplication and fixed auth token key usage.
2. Property/Evidence routing alignment: `id` param used consistently where routes define `:id`.
3. `PropertyDetailView` aligned to current explanation contract (`summary`, `source_chain`, contradiction object).
4. Dead search relation navigation fixed (`/sources/:id` link instead of non-existent `/relations/:id` detail route).
5. `EditRelationView` entity loading fixed for paginated `listEntities()` response (`items`).
6. Inference entity links switched from slug-based routes to ID-based routes.
7. Extraction relation contract alignment:
   - relation keying now stable with role-aware helper
   - relation display supports both role array and legacy object form
   - added `measures` UI support in relation label/icon mappings
8. Relation notes type/rendering aligned (`string | i18n object` support).
9. Backend extraction prompt/schema alignment:
   - removed obsolete relation types from prompts (`compared_to`, `studied_in`, `correlated_with`)
   - relation examples now use `roles` arrays (not legacy object shape)
10. Fixed `PropertyDetailView` hook-order runtime bug (conditional `useMemo` violation).
11. Updated frontend tests to match new route params and explanation contract.

---

## Validation Results

1. `frontend`: `npm run -s build` -> PASS.
2. `frontend`: `npm run -s test -- --run src/views/__tests__/PropertyDetailView.test.tsx src/views/__tests__/EvidenceView.test.tsx src/components/__tests__/InferenceBlock.test.tsx` -> PASS (`28 passed`, `2 skipped`).
3. `backend`: `pytest tests/test_document_extraction.py -q` -> PASS (`15 passed`).
4. `frontend`: `npx tsc --noEmit` -> FAIL due to many pre-existing type errors outside this fix scope (existing project-wide TS debt).

---

## Next Steps

1. Decide if we want a dedicated cleanup pass for project-wide TypeScript errors (`npx tsc --noEmit` baseline currently red).
2. Run a broader frontend regression suite once the TS baseline is addressed.
