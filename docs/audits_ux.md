# HyphaGraph UX Audit Program

For HyphaGraph, the most useful UX evaluation approach is not a single broad audit. It is a set of targeted audits, each with a narrow question and a concrete deliverable.

This document defines those audits, what each one is meant to answer, and the recommended execution order.

## Recommended Audit Set

### 1. Object Model Clarity Audit

Checks whether users really understand the difference between:

- `entity`
- `relation`
- `claim`
- `source`
- `synthesis`
- `inference`

This is critical because if the conceptual model is fuzzy, the whole product feels confusing even with a good UI.

Looks for:

- overlapping terms
- inconsistent naming
- unclear boundaries between object types
- pages that mix different abstraction levels

Deliverable:

- confusion map
- renaming suggestions
- object identity rules for the UI

### 2. Navigation And Orientation Audit

Checks whether users know:

- where they are
- how they got there
- what is related
- how to go back up
- how to continue deeper without getting lost

This is especially important in graph-like knowledge products.

Looks for:

- weak breadcrumbs
- dead-end detail pages
- poor local navigation
- loss of context when moving between list, detail, graph, and source

Deliverable:

- navigation map
- orientation failures
- proposed global and local navigation model

### 3. Evidence Traceability Audit

This is one of the highest-value audits for HyphaGraph.

Checks whether a user can move naturally from:

- synthesis
- to supporting claims
- to source excerpts
- to original documents

And also back upward.

Looks for:

- hidden provenance
- too many clicks to verify
- poor distinction between support and contradiction
- unclear "why is this shown" logic

Deliverable:

- traceability score by page type
- broken audit trails
- rules for provenance placement and evidence linking

### 4. Synthesis Explainability Audit

Focused specifically on pages or blocks that present compiled conclusions.

Checks whether the UI makes clear:

- what the synthesis says
- what supports it
- what contradicts it
- what remains uncertain
- what is computed vs directly evidenced

Looks for:

- false certainty
- opaque synthesis blocks
- missing uncertainty indicators
- missing explanation of derivation logic

Deliverable:

- ideal synthesis block blueprint
- explainability guidelines
- display rules for support, contradiction, and uncertainty

### 5. Contradiction Handling Audit

HyphaGraph should not just store contradictions; it should make them intelligible.

This audit checks whether disagreement is surfaced in a way that helps reasoning instead of causing chaos.

Looks for:

- contradictory claims being flattened away
- no distinction between majority support and minority contradiction
- no visual model for conflict
- pages that imply consensus when none exists

Deliverable:

- contradiction display patterns
- conflict comparison layouts
- severity ranking of misleading certainty issues

### 6. Expert Workflow Audit

This is a task-based audit for heavy users.

Example workflows:

- find an entity
- inspect linked claims
- compare support
- open source evidence
- validate relation meaning
- build trust in a synthesis

Looks for:

- too many clicks
- poor keyboard efficiency
- repeated context switching
- friction in compare and inspect flows
- layouts that slow expert work

Deliverable:

- workflow friction report
- step counts
- fast-path redesign suggestions

### 7. Dense Data Readability Audit

A specialized readability audit for expert tools, not marketing pages.

Checks whether dense content remains:

- scannable
- chunked
- prioritized
- readable over long sessions

Looks for:

- metadata walls
- poor section ordering
- weak headings
- low scanability
- bad table readability
- too much undifferentiated text

Deliverable:

- readability problems by component type
- content hierarchy rules
- typography and spacing recommendations for dense views

### 8. Table, Filter, And Search Ergonomics Audit

If the product has large datasets, this becomes extremely important.

Checks whether users can:

- find things quickly
- refine large result sets
- understand filter state
- compare rows
- preserve search context

Looks for:

- ambiguous filters
- hidden active constraints
- poor column prioritization
- weak sorting
- hard-to-scan tables
- filters disconnected from user reasoning

Deliverable:

- search and filter usability report
- recommended filter taxonomy
- table blueprint improvements

### 9. Graph View Usefulness Audit

Graph views are often impressive but not actually usable.

This audit asks whether the graph helps with:

- navigation
- explanation
- analysis
- discovery

or whether it mostly creates visual noise.

Looks for:

- unclear node and edge meaning
- poor legend and semantics
- graph overload
- weak link to detail pages
- loss of context after interaction

Deliverable:

- graph view scorecard
- recommended graph use cases
- rules for when graph view should or should not be used

### 10. Curation And Validation Workflow Audit

If users edit, review, validate, or curate claims and relations, this deserves its own audit.

Checks whether the product supports safe knowledge curation.

Looks for:

- weak review states
- unclear validation actions
- insufficient evidence visibility during curation
- bad change-review ergonomics
- missing audit trail for edits

Deliverable:

- curator workflow report
- review-state model recommendations
- safer validation UI patterns

### 11. Provenance Visibility Audit

Close to traceability, but more page-local.

This audit checks whether provenance is visible enough without navigating away.

Looks for:

- source hidden in secondary tabs
- no provenance in summaries
- unclear evidence counts
- no support level at glance

Deliverable:

- provenance visibility rules
- at-a-glance evidence design recommendations
- page-level provenance placement patterns

### 12. Learnability And Onboarding Audit

Useful if you want outsiders or occasional users to understand the system.

Checks whether a new user can grasp:

- what the product is
- what the major object types are
- how to start
- how to verify information

Looks for:

- unexplained jargon
- missing empty-state guidance
- no first-step suggestions
- confusing landing pages

Deliverable:

- onboarding gap analysis
- glossary and help recommendations
- guided-entry patterns

### 13. Cross-Page Consistency Audit

Checks whether similar page families behave similarly.

For example:

- all detail pages
- all list pages
- all compare views
- all evidence panels

Looks for:

- inconsistent section ordering
- different naming for same concepts
- shifting action placement
- different visual language for the same semantic status

Deliverable:

- consistency matrix
- reusable page-family standards
- design-system-level recommendations

### 14. Trust Signaling Audit

A more product-strategic audit.

Checks whether the interface feels:

- rigorous
- inspectable
- honest about uncertainty
- resistant to "magic AI answer" vibes

This is especially important for HyphaGraph because credibility is part of the product value.

Looks for:

- unexplained generated outputs
- hidden computation logic
- lack of uncertainty language
- UI that overstates confidence
- evidence presented as decoration rather than proof

Deliverable:

- trust risk report
- trust-building UI recommendations
- wording and labeling guidelines

### 15. Scalability Of IA Audit

Checks whether the current page and navigation architecture will still work when the dataset becomes much larger.

Looks for:

- pages that collapse under many linked items
- unbounded relation lists
- weak summarization layers
- poor progressive disclosure
- navigation models that only work on small demos

Deliverable:

- scale risk assessment
- structural redesign recommendations
- rules for summary layers, aggregation, and lazy disclosure

## Recommended Priority Order

If I had to prioritize, I would start with this sequence:

1. Object model clarity audit
2. Page information architecture audit
3. Evidence traceability audit
4. Synthesis explainability audit
5. Navigation and orientation audit
6. Expert workflow audit
7. Graph view usefulness audit

That order matches the core product risk: first make the system understandable, then make it traceable, then make it efficient.

## Suggested Program Output

This audit program can be expanded into a full execution plan for HyphaGraph with:

- audit names
- goal of each audit
- concrete questions
- expected deliverables
- recommended execution order

