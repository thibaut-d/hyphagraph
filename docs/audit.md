# Code Audits

Targeted audits to enforce the principles from [AGENTS.md](/home/thibaut/code/hyphagraph/AGENTS.md), [docs/development/CODE_GUIDE.md](/home/thibaut/code/hyphagraph/docs/development/CODE_GUIDE.md), and the core architecture documents. Run them regularly, especially before releases, after large refactors, and before AI-assisted edits to backend inference, extraction, or frontend synthesis surfaces.

**Output**: each audit saves findings to `.temp/<audit_name>_report.md` with a score, violation list (severity + file + fix), metrics, and previous score for regression tracking.

---

## Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| **Critical** | Risks incorrect knowledge, provenance loss, hidden contradictions, security issues, or broken contracts | Fix before merge |
| **Major** | Harms maintainability, clarity, or architectural consistency | Fix in current sprint |
| **Minor** | Worth fixing but not urgent | Fix opportunistically |

---

## Priority Order

When time is limited, run audits in this order:

1. Knowledge Integrity & Explainability
2. Revision Architecture & Provenance
3. Security & Authentication
4. API / Service Boundary Discipline
5. Frontend Uncertainty & Traceability
6. Silent Error Handling & Logging
7. Test Suite Health
8. Pydantic / Typed Contract Discipline
9. Type Coverage
10. Function Size & Modularity
11. Side Effects & Coupling
12. Pattern Consistency
13. Dead Code & Compatibility Shims
14. AI Edit Safety
15. Documentation & i18n Completeness

---

## 1. Knowledge Integrity & Explainability

> AI context core: "Knowledge is derived from documented statements, never written by humans or AI."
> AI context core: "Contradictions are preserved, not resolved by opinion."
> AI context core: "All conclusions must be explainable and recomputable."

**Scope**: `backend/app/services/inference*`, `backend/app/services/explanation*`, `backend/app/services/document_extraction*`, `backend/app/schemas/inference.py`, `backend/app/schemas/explanation.py`, frontend inference/explanation/synthesis/disagreement views.

**Checks**:
- [ ] No service stores or returns human-authored or LLM-authored conclusions as authoritative fact
- [ ] Inference remains deterministic and recomputable from stored relations and sources
- [ ] Explanation payloads trace conclusions back to evidence, roles, and sources
- [ ] Contradictions are preserved in backend outputs and visible in frontend presentation
- [ ] Confidence/quality indicators never imply certainty beyond available evidence
- [ ] LLM integration is formatting/extraction only, never consensus or fact storage

**How to search**:
```bash
rg "llm|openai|anthropic|prompt" backend/app frontend/src
rg "inference|explanation|synthesis|disagreement" backend/app/services backend/app/schemas frontend/src/views frontend/src/components
rg "certainty|consensus|final truth|resolved contradiction" backend/app frontend/src -i
```

**Metrics**: count of non-explainable outputs, count of places where contradictions are hidden, count of inference flows depending on LLM-generated content.

---

## 2. Revision Architecture & Provenance

> AI context core: "Claims are immutable in meaning (revision architecture)."
> CODE_GUIDE: all create/update operations accept optional `user_id`.

**Scope**: `backend/app/models/`, `backend/app/services/`, `backend/app/repositories/`, migrations, relation/entity/source write paths.

**Checks**:
- [ ] Mutable domain objects still follow the base-table + revision-table pattern
- [ ] New revision tables include `created_by_user_id` with `SET NULL` on user delete
- [ ] Write flows pass `user_id` through service boundaries where provenance should be recorded
- [ ] Current-revision updates do not mutate historical revisions in place
- [ ] API handlers and services do not bypass revision creation rules
- [ ] Tests cover provenance and current-revision semantics for changed write paths

**How to search**:
```bash
rg "created_by_user_id|is_current" backend/app/models backend/app/services backend/app/repositories backend/alembic
rg "user_id" backend/app/api backend/app/services
rg "update\\(|create\\(" backend/app/services backend/app/repositories
```

**Metrics**: count of write paths missing provenance propagation, count of revision tables missing required fields, count of tests missing revision-history assertions.

---

## 3. Security & Authentication

> CODE_GUIDE: custom JWT only, no auth frameworks, secrets from environment, explicit permission checks.

**Scope**: `backend/app/api/auth.py`, `backend/app/dependencies/auth.py`, `backend/app/utils/auth.py`, `backend/app/utils/permissions.py`, config, tests, repo-wide secrets handling.

**Checks**:
- [ ] No secrets, tokens, or password defaults committed in source, fixtures, or docs
- [ ] JWT secret and auth settings come from environment/config, not hardcoded literals
- [ ] Password hashing uses bcrypt via passlib, never plaintext or reversible storage
- [ ] Permission checks are explicit Python functions, not hidden decorators or framework magic
- [ ] Auth routes log failures without leaking credentials or token contents
- [ ] Tests cover login, refresh/authenticated access, inactive users, and unauthorized paths

**How to search**:
```bash
rg "SECRET|TOKEN|PASSWORD|API_KEY|sk-" backend frontend e2e -g '!e2e/node_modules/**'
rg "FastAPI Users|Auth0|Clerk|OAuth provider|RBAC" backend/app -i
rg "bcrypt|passlib|jose|jwt" backend/app
rg "can_[a-z_]+\\(" backend/app/utils/permissions.py backend/app/api backend/app/services
```

**Metrics**: count of hardcoded secret patterns, count of auth endpoints missing explicit permission checks, count of auth logs exposing sensitive data.

---

## 4. API / Service Boundary Discipline

> AI context core: "Business logic in services, never in API controllers."
> VIBE: "Respect the architecture. No cross-layer shortcuts."

**Scope**: `backend/app/api/`, `backend/app/services/`, `frontend/src/api/`, `frontend/src/views/`.

**Checks**:
- [ ] FastAPI route modules validate requests, call providers/services, and shape responses only
- [ ] Route handlers do not implement domain logic, inference logic, or extraction orchestration inline
- [ ] Services accept/return Pydantic schemas where appropriate, not ORM instances over the API boundary
- [ ] Frontend uses `frontend/src/api/` clients instead of ad-hoc fetch logic in views/components
- [ ] No frontend business logic duplicates backend inference, contradiction handling, or review decisions
- [ ] Dependency providers remain explicit and consistent across backend routes

**How to search**:
```bash
rg "@router\\.(get|post|put|patch|delete)" backend/app/api -n
rg "fetch\\(|axios|URLSearchParams|new Request" frontend/src/views frontend/src/components
rg "Session|AsyncSession|select\\(" frontend/src -n
rg "Depends\\(" backend/app/api
```

**Metrics**: count of route handlers containing business logic branches, count of frontend views making direct network calls, count of API responses returning ORM-shaped data instead of schemas.

---

## 5. Frontend Uncertainty & Traceability

> AI context core: "Never hide contradictions in the UI."
> UX rules: every conclusion must be traceable to sources within two clicks.

**Scope**: `frontend/src/views/`, `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/i18n/`.

**Checks**:
- [ ] Contradictions, disagreements, and missing evidence remain visible in the UI
- [ ] Synthesis/inference screens present computed output as evidence-backed, not absolute truth
- [ ] Source traceability is preserved from synthesis/disagreement/explanation screens
- [ ] Filters only affect display, not the underlying computation semantics shown to the user
- [ ] Empty/error/loading states do not overstate certainty or hide missing evidence
- [ ] All user-visible strings are in i18n resources, not hardcoded in components

**How to search**:
```bash
rg "disagreement|contradiction|uncertain|confidence|evidence|source" frontend/src/views frontend/src/components frontend/src/hooks
rg "\"[^\"]+[A-Za-z][^\"]*\"" frontend/src/views frontend/src/components | head
rg "t\\(" frontend/src/views frontend/src/components frontend/src/hooks
```

**Metrics**: count of UI paths that hide contradictions, count of hardcoded user-facing strings, count of views missing direct source-trace links.

---

## 6. Silent Error Handling & Logging

> VIBE: fail fast, fail loud.
> CODE_GUIDE: use logging, never print.

**Scope**: backend and frontend application code.

**Checks**:
- [ ] No bare `except` or swallowed exceptions that degrade correctness silently
- [ ] Error messages include enough context to diagnose the failing entity/source/relation/request
- [ ] No `print()` calls in production backend code
- [ ] Frontend error handling preserves actionable user feedback and useful logging context
- [ ] No broad fallback return values (`[]`, `{}`, `None`) that mask real failures in domain flows
- [ ] `# type: ignore` comments include justification when retained

**How to search**:
```bash
rg "except\\s*(Exception)?\\s*:" backend/app frontend/src
rg "print\\(" backend/app frontend/src
rg "# type: ignore" backend/app frontend/src
rg "return \\[\\]|return \\{\\}|return None" backend/app/services backend/app/api frontend/src
```

**Metrics**: count of swallowed exceptions, count of `print()` calls, count of vague error messages, count of unjustified `# type: ignore`.

---

## 7. Test Suite Health

> AI context core: TDD mandatory, never claim done if tests fail, target >= 80% coverage.

**Scope**: `backend/tests/`, `frontend/src/**/__tests__/`, `e2e/tests/`, changed modules in backend/frontend.

**Checks**:
- [ ] Backend tests cover success and error paths for changed service and API behavior
- [ ] Frontend tests cover loading, error, empty, and contradiction-visible states where relevant
- [ ] E2E tests cover critical user flows for auth, entities, relations, sources, inferences, and explanations
- [ ] No new flakiness from timing, order dependence, or network dependence
- [ ] Coverage remains at or above team expectations, with attention to modified modules
- [ ] Test fixtures and helper shims still reflect current public module boundaries

**How to search**:
```bash
pytest backend/tests -q
npm --prefix frontend test -- --runInBand
npm --prefix e2e test -- --runInBand
rg "pytest.raises" backend/tests
rg "render\\(|screen\\.|waitFor\\(" frontend/src -g '*test*'
```

**Metrics**: backend test pass/fail, frontend test pass/fail, e2e test pass/fail, coverage by changed module, count of error-path tests.

---

## 8. Pydantic / Typed Contract Discipline

> AI context core: Pydantic models are the single source of truth for I/O.

**Scope**: `backend/app/schemas/`, API request/response models, service boundaries, typed frontend contracts.

**Checks**:
- [ ] API request/response payloads are represented by Pydantic schemas, not ad-hoc dicts
- [ ] Route modules return schemas, not ORM models or partially shaped dicts
- [ ] Stable backend response shapes used by frontend have matching TypeScript types
- [ ] Manual dict assembly is minimized where `model_dump()` or schema mapping should be used
- [ ] New extraction/inference/explanation payload shapes are documented in schemas before use
- [ ] Backward-compatibility shims do not become the de facto source of truth for contracts

**How to search**:
```bash
rg "BaseModel" backend/app/schemas backend/app/api backend/app/services
rg "return \\{" backend/app/api backend/app/services
rg "model_dump\\(" backend/app
rg "type .*Read|interface .*Read" frontend/src/types frontend/src/api
```

**Metrics**: count of endpoints using raw dict contracts, count of manual payload builders, count of backend/frontend contract mismatches.

---

## 9. Type Coverage

> CODE_GUIDE: use type hints everywhere.

**Scope**: public Python functions in `backend/app/`, TypeScript surfaces in `frontend/src/`.

**Checks**:
- [ ] Public Python functions have parameter and return annotations
- [ ] Avoid `Any` where concrete domain types are known
- [ ] Prefer precise collections over bare `dict` / `list`
- [ ] TypeScript components/hooks/api clients do not fall back to `any`
- [ ] Frontend types reflect backend contracts, especially for revision, inference, and explanation payloads

**How to search**:
```bash
rg "def [a-zA-Z_]\\w*\\(.*\\):" backend/app | grep -v " -> "
rg ": Any\\b|-> Any\\b" backend/app
rg "\\bany\\b" frontend/src
rg "dict\\b|list\\b" backend/app | head
```

**Metrics**: percent of public Python functions fully typed, count of Python `Any`, count of TypeScript `any`, count of bare generic collection annotations.

---

## 10. Function Size & Modularity

> AGENTS.md: readability first, keep top-level code simple, hide complexity in subsystems.

**Scope**: backend services, API route modules, frontend views/components/hooks.

**Checks**:
- [ ] Functions remain short and focused, especially in service orchestration and page controllers
- [ ] Files trending above 500-800 lines are split into coherent modules
- [ ] Top-level workflow code reads like orchestration, not implementation detail
- [ ] Boolean flags are not switching unrelated behaviors inside one function
- [ ] Deep nesting is flattened with early returns or extracted helpers

**How to search**:
```bash
find backend/app frontend/src -type f \\( -name '*.py' -o -name '*.ts' -o -name '*.tsx' \\) -exec awk 'END{if(NR>500) print NR, FILENAME}' {} +
rg "def \\w+\\(.*bool|function .*\\(.*: boolean|const .* = \\(.*: boolean" backend/app frontend/src
```

**Metrics**: count of files >500 lines, count of oversized functions, count of functions with boolean mode flags, max nesting depth in modified areas.

---

## 11. Side Effects & Coupling

> CODE_GUIDE: side effects must be explicit. Prefer passing data over importing internal state.

**Scope**: backend services/repos/api, frontend hooks/components/utils.

**Checks**:
- [ ] Services do not instantiate hidden collaborators inside methods when constructor/provider wiring should be explicit
- [ ] No new circular imports across API, services, schemas, repositories, or frontend feature folders
- [ ] Functions avoid mutating caller-owned inputs unless that contract is explicit
- [ ] Hidden runtime imports (`require`, function-local imports) are only used for real cycle/optional-dependency reasons
- [ ] Frontend hooks/components do not depend on mutable module-level shared state

**How to search**:
```bash
rg "import .* inside function|from .* import .*" backend/app frontend/src
rg "require\\(" frontend/src backend/app
rg "TYPE_CHECKING" backend/app frontend/src
```

**Metrics**: count of hidden dependency edges, count of mutable module-level state sites, count of circular import risks.

---

## 12. Pattern Consistency

> VIBE: simple, explicit code. Consistent sibling modules reduce review and AI-edit risk.

**Scope**: `backend/app/api/`, `backend/app/services/`, `frontend/src/views/`, `frontend/src/components/`, `frontend/src/api/`.

**Checks**:
- [ ] Backend routes use the same provider/dependency pattern across modules
- [ ] Similar service families expose comparable constructor and method patterns
- [ ] Frontend views follow the current split between controller logic, hooks, and presentational sections
- [ ] API clients use shared request/query helpers rather than open-coded serialization
- [ ] Tests patch the direct owner module, not legacy facade shims, unless compatibility is intentional

**How to search**:
```bash
rg "Depends\\(" backend/app/api
rg "URLSearchParams|new URLSearchParams" frontend/src/api
rg "document_extraction\\.py|compat|shim|re-export" backend/app backend/tests frontend/src -i
```

**Metrics**: count of modules deviating from standard patterns, count of duplicated request-serialization helpers, count of tests coupled to compatibility facades.

---

## 13. Dead Code & Compatibility Shims

> AGENTS.md: remove duplication and keep modules focused.

**Scope**: entire repository, with extra attention to refactoring surfaces called out in `TODO.md`.

**Checks**:
- [ ] Unused imports, exports, and helper functions are removed
- [ ] Refactor-era compatibility shims still have active importers; delete dead ones
- [ ] Commented-out code and stale TODO/FIXME/HACK notes are either resolved or tracked in `TODO.md`
- [ ] Orphaned components/hooks/services created during refactors are deleted
- [ ] Legacy docs and reports do not misrepresent the current architecture

**How to search**:
```bash
ruff check backend/app backend/tests --select F401
rg "TODO|FIXME|HACK|XXX" backend/app frontend/src docs
rg "shim|re-export|backward compat|compatibility" backend/app backend/tests frontend/src -i
```

**Metrics**: count of unused imports, count of active shims with zero importers, count of stale inline TODOs, count of orphaned modules.

---

## 14. AI Edit Safety

> AGENTS.md: audit readability and architecture before completion.
> VIBE: no hidden side effects, no non-obvious shortcuts.

**Scope**: high-churn and high-risk modules across backend and frontend.

**Checks**:
- [ ] Large, central files expose clear helper seams before further AI edits
- [ ] Public module boundaries are explicit enough that tests and callers do not depend on incidental internals
- [ ] Hidden naming conventions or contract assumptions are documented near the code
- [ ] High-risk files have focused tests guarding behavior before refactors
- [ ] `TODO.md` records residual maintainability issues discovered during the audit

**How to search**:
```bash
find backend/app frontend/src -type f \\( -name '*.py' -o -name '*.ts' -o -name '*.tsx' \\) -exec awk 'END{if(NR>500) print NR, FILENAME}' {} +
rg "TODO.md|Refactor Needed|maintainability" .
```

**Metrics**: count of high-risk large files, count of undocumented hidden conventions, count of modified high-risk files lacking focused tests.

---

## 15. Documentation & i18n Completeness

> Routing rules: AI context files must stay synchronized with the codebase.

**Scope**: `AGENTS.md`, `TODO.md`, `docs/architecture/`, `docs/development/`, `frontend/src/i18n/`.

**Checks**:
- [ ] `TODO.md` reflects current active work and completed refactors accurately
- [ ] AI context docs still match actual architecture, route structure, and service boundaries
- [ ] New frontend user-visible text has translation keys and translations
- [ ] Cross-references remain valid after module moves or route splits
- [ ] Audit reports and status summaries do not contradict current code behavior

**How to search**:
```bash
rg "TODO.md|AI_CONTEXT|ARCHITECTURE|document_extraction|service_dependencies" docs AGENTS.md
rg "t\\(" frontend/src
rg "\"[^\"]+[A-Za-z][^\"]*\"" frontend/src/views frontend/src/components | head
```

**Metrics**: count of stale documentation references, count of missing translation keys, count of broken cross-references.

---

## Running an Audit

1. Pick an audit from the priority list, or run the full set before a release.
2. Search the codebase using the provided commands.
3. Classify each finding as Critical, Major, or Minor.
4. Save findings to `.temp/<audit_name>_report.md` using this format:

```markdown
# <Audit Name> Report — <date>

**Score**: XX/100 — N critical, N major, N minor
**Previous score**: YY/100 (<date>) — or "first run"
**Trend**: +X / -X / unchanged

## Critical

### [C1] <title>
- **File**: <path>:<line>
- **Problem**: <description>
- **Fix**: <concrete action>

## Major
...

## Minor
...

## Metrics
- <metric>: <value> (previous: <value>)

## Regressions Since Last Run
- <list of new findings that were not present in the previous report>
```

5. Fix Critical findings before merge, schedule Major for the current sprint, and fix Minor opportunistically.
6. Archive the previous report to `.temp/<audit_name>_report_<date>.md` before overwriting it.

---

## Cadence

| Trigger | Audits to Run |
|---------|---------------|
| **Before release** | All |
| **After backend refactor** | API / Service Boundary Discipline, Function Size & Modularity, Side Effects & Coupling, Dead Code & Compatibility Shims |
| **After inference or explanation changes** | Knowledge Integrity & Explainability, Pydantic / Typed Contract Discipline, Test Suite Health |
| **After schema or migration changes** | Revision Architecture & Provenance, Pydantic / Typed Contract Discipline |
| **After auth changes** | Security & Authentication, Test Suite Health |
| **After frontend synthesis/disagreement/explanation changes** | Frontend Uncertainty & Traceability, Documentation & i18n Completeness |
| **Before AI-assisted edits to core modules** | AI Edit Safety, Silent Error Handling & Logging, Pattern Consistency |
| **Weekly lightweight pass** | Silent Error Handling & Logging, Dead Code & Compatibility Shims, Documentation & i18n Completeness |
| **Monthly comprehensive pass** | Test Suite Health, Type Coverage, Function Size & Modularity, Knowledge Integrity & Explainability |
