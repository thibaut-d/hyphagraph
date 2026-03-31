# HyphaGraph UX Audit Protocol

HyphaGraph should not run a single broad UX review and call it done. It needs a set of targeted audits with a shared execution contract so findings stay aligned with the current product model and convert cleanly into implementation work.

This document defines:

- the current-model assumptions an audit must honor
- how to decide whether an audit applies to implemented surfaces
- the standard output format for every audit
- the audit set worth running
- the recommended execution order for current project goals

## 1. Model Alignment Rules

Every audit must start by aligning to the current HyphaGraph model before making recommendations.

Canonical current model:

- `source`: a document that states something
- `entity`: a stable domain object
- `relation (claim)`: one document-grounded statement about entities in context
- `inference`: a computed result from multiple document-grounded claims
- `synthesis`: a human-readable computed summary over inferred or aggregated evidence

Current architectural invariants from the project docs:

- document-grounded claims are the only source of facts
- contradictions must be preserved, not hidden
- syntheses must remain computable and explainable
- AI must not become epistemically authoritative
- frontend must expose uncertainty, provenance, and evidence clearly

Audit rule:

- By default, audits evaluate the current model above.
- If an audit proposes a future model split, such as separating `claim` and `relation` into distinct first-class page families, it must label that recommendation as `future-model proposal`, not `current-model defect`.

## 2. Implemented-Surface Gate

Do not run an audit against imagined product surface area.

Before each audit, inventory relevant surfaces and classify each one as:

- `implemented`
- `partial`
- `planned`
- `not present`

Execution rule:

- `implemented`: produce full findings
- `partial`: produce findings plus missing-surface notes
- `planned`: produce only future-design risks and prerequisites
- `not present`: mark the audit or sub-scope as `N/A for current product`

This prevents low-signal findings on non-existent graph, compare, or onboarding surfaces.

## 3. Standard Output Contract

Every audit must produce the same minimum structure.

Required sections:

1. `Scope`
   - audit name
   - date
   - pages, components, and workflows reviewed
2. `Implemented Surfaces`
   - list of relevant surfaces and their status: implemented, partial, planned, not present
3. `Invariants Checked`
   - which architectural and product invariants were tested
4. `Findings`
   - each finding with severity, affected users, evidence, and recommendation
5. `Future-Model Proposals`
   - optional section for recommendations that intentionally exceed the current model
6. `TODO-Ready Actions`
   - concrete actions suitable for `TODO.md`
7. `N/A Items`
   - audit questions skipped because the surface is absent

Required evidence standard for each finding:

- cite the page, workflow, or component
- describe observed behavior, not only opinion
- state whether the issue is a `current-model defect`, `implementation gap`, or `future-model proposal`

Required action standard for `TODO.md` conversion:

- why the issue matters
- what should change
- where it likely lives in the codebase
- how success should be verified

## 4. Deliverable Format For TODO Conversion

Every audit should end with a compact list of implementation-ready actions. Each action should be convertible to a `TODO.md` item without rewriting.

Use this structure:

- `ID`: audit-specific identifier
- `Type`: current-model defect / implementation gap / future-model proposal
- `Priority`: critical / high / medium / low
- `Location`: page, workflow, component, or route family
- `Problem`: one-sentence statement of what fails
- `Change`: one-sentence fix direction
- `Verification`: how to confirm the fix works

Rule:

- Only `current-model defect` and `implementation gap` items should go into the near-term prioritized section of `TODO.md`.
- `future-model proposal` items can be captured separately or explicitly marked as structural redesign candidates.

## 5. Audit Set

The audits below are still the right set, but they must be run under the rules above.

### 1. Object Model Clarity Audit

Question:

- Do users understand the difference between `source`, `entity`, `relation (claim)`, `inference`, and `synthesis` in the current product?

Looks for:

- overlapping terms
- inconsistent naming
- unclear object boundaries
- mixed abstraction levels on the same page
- accidental drift between current model and proposed future model

Primary deliverables:

- confusion map
- naming problems by page family
- object identity rules for the current UI
- optional future-model proposals if the current model is no longer sufficient

### 2. Page Information Architecture Audit

Question:

- Does each page clearly communicate its object, purpose, hierarchy, and next actions?

Looks for:

- unclear page identity
- action-first layouts where verification should come first
- poor section ordering
- weak summary-to-detail flow
- page families missing for core objects

Primary deliverables:

- page-family findings
- recommended section order by page type
- page blueprint corrections

### 3. Evidence Traceability Audit

Question:

- Can users move naturally from synthesis or inference down to document-grounded evidence and back up again?

Looks for:

- hidden provenance
- too many clicks to verify
- traceability that stops at source pages instead of exact evidence items
- unclear support versus contradiction logic

Primary deliverables:

- traceability score by page family
- broken audit trails
- evidence-linking rules

### 4. Synthesis Explainability Audit

Question:

- Do computed conclusion surfaces show what is concluded, why, how strongly, and with what uncertainty?

Looks for:

- false certainty
- opaque synthesis blocks
- weak uncertainty signaling
- unclear computed-versus-sourced boundaries

Primary deliverables:

- ideal synthesis block blueprint
- explainability guidelines
- support / contradiction / uncertainty display rules

### 5. Navigation And Orientation Audit

Question:

- Can users tell where they are, what this page is related to, and how to move without losing context?

Looks for:

- weak breadcrumbs or page ancestry
- dead-end detail pages
- inconsistent local navigation
- poor transitions across list, detail, source, evidence, and synthesis surfaces

Primary deliverables:

- navigation map
- orientation failure list
- proposed global and local navigation rules

### 6. Expert Workflow Audit

Question:

- Can expert users complete high-value tasks quickly and confidently?

Example workflows:

- find an entity
- inspect linked claims or relations
- compare support and contradiction
- open exact source evidence
- validate relation meaning
- build trust in a synthesis

Looks for:

- too many clicks
- repeated context switching
- poor keyboard flow
- compare and inspect friction
- slow review or curation loops

Primary deliverables:

- workflow friction report
- step counts
- fast-path redesign suggestions

### 7. Dense Data Readability Audit

Question:

- Do dense expert views remain scannable, chunked, and readable over long sessions?

Looks for:

- metadata walls
- weak headings
- poor section ordering
- low table scanability
- undifferentiated long text

Primary deliverables:

- readability issues by component type
- dense-view hierarchy rules
- typography and spacing recommendations

### 8. Table, Filter, And Search Ergonomics Audit

Question:

- Can users search, refine, compare, and preserve context in large result sets?

Looks for:

- ambiguous filters
- hidden active constraints
- weak sorting
- poor column prioritization
- search destinations that do not land on canonical object pages

Primary deliverables:

- search and filter usability report
- filter taxonomy recommendations
- table blueprint improvements

### 9. Graph View Usefulness Audit

Question:

- If graph surfaces exist, do they help with navigation, explanation, analysis, or discovery?

Looks for:

- unclear node and edge meaning
- weak legend semantics
- graph overload
- poor transitions to canonical detail pages
- interaction that loses context

Primary deliverables:

- graph view scorecard
- recommended use cases
- rules for when graph view should or should not be used

Special gate:

- If no graph surface is implemented, mark this audit `N/A for current product` and limit output to future-design prerequisites.

### 10. Curation And Validation Workflow Audit

Question:

- Do review and editing flows support safe, evidence-visible knowledge curation?

Looks for:

- weak review states
- unclear validation actions
- insufficient evidence during curation
- poor change-review ergonomics
- missing audit trail for edits

Primary deliverables:

- curator workflow report
- review-state model recommendations
- safer validation patterns

### 11. Provenance Visibility Audit

Question:

- Is provenance visible enough on the page itself without forcing navigation away?

Looks for:

- source hidden in tabs
- no provenance in summaries
- unclear evidence counts
- no support level at a glance

Primary deliverables:

- provenance visibility rules
- at-a-glance evidence recommendations
- page-level provenance placement patterns

### 12. Learnability And Onboarding Audit

Question:

- Can a new or occasional user understand what the product is, what the objects are, and how to verify information?

Looks for:

- unexplained jargon
- missing empty-state guidance
- weak first-step suggestions
- confusing landing or entry flows

Primary deliverables:

- onboarding gap analysis
- glossary and help recommendations
- guided-entry patterns

### 13. Cross-Page Consistency Audit

Question:

- Do similar page families behave similarly enough to support transfer learning?

Looks for:

- inconsistent section ordering
- shifting action placement
- different names for the same semantic concept
- inconsistent evidence and uncertainty presentation

Primary deliverables:

- consistency matrix
- reusable page-family standards
- design-system-level recommendations

### 14. Trust Signaling Audit

Question:

- Does the interface feel rigorous, inspectable, and honest about uncertainty?

Looks for:

- unexplained generated output
- hidden computation logic
- overstated confidence
- evidence used decoratively instead of as proof

Primary deliverables:

- trust risk report
- trust-building recommendations
- wording and labeling guidelines

### 15. Scalability Of IA Audit

Question:

- Will current page and navigation structures still work when evidence, relations, and linked items grow much larger?

Looks for:

- unbounded lists
- weak summarization layers
- poor progressive disclosure
- page models that only work on demo-scale data

Primary deliverables:

- scale risk assessment
- structural redesign recommendations
- summary-layer and aggregation rules

## 6. Priority Model

Do not run the audits in a purely abstract sequence. Prioritize based on current implementation risk first, then broader research value.

### Implementation-Critical Now

Run these first because they directly affect the current app and current project goals:

1. Object model clarity audit
2. Page information architecture audit
3. Evidence traceability audit
4. Synthesis explainability audit
5. Navigation and orientation audit
6. Curation and validation workflow audit
7. Expert workflow audit

### Strategic Research Next

Run these after the highest-risk current defects are understood:

1. Provenance visibility audit
2. Cross-page consistency audit
3. Dense data readability audit
4. Table, filter, and search ergonomics audit
5. Trust signaling audit
6. Learnability and onboarding audit
7. Scalability of IA audit
8. Graph view usefulness audit

Rule:

- Any audit can move up if a new implementation introduces that surface and makes it high-risk.

## 7. Execution Sequence For A Real Audit Pass

For each audit:

1. inventory implemented surfaces
2. restate the current model and invariants being checked
3. review pages, components, and workflows
4. classify findings as current-model defect, implementation gap, or future-model proposal
5. convert near-term actions into `TODO.md`
6. note `N/A` areas explicitly

This keeps the audit program usable as an engineering input, not only as product research.

## 8. Success Criteria

The audit program is working if it produces:

- fewer contradictory recommendations across audits
- clearer separation between immediate fixes and structural redesign
- findings that map directly onto the current product architecture
- TODO items that are concrete enough for design and engineering execution
- recommendations that preserve HyphaGraph's core commitments: evidence-first reasoning, visible contradiction, and explainable computation
