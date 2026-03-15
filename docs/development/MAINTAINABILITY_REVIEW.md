# Maintainability Review Guide

Use this document as a lightweight review rubric, not as a permanent backlog or dated audit report.

## Purpose

Check whether a change keeps the codebase readable, local, typed, and easy to evolve.

This guide applies to both human and AI contributors.

## Review priorities

Review in this order:

1. Module ownership and boundary discipline
2. Function and component size
3. Duplication and drift
4. Type and schema clarity
5. Testability
6. Error handling and observability

## What to flag

### 1. Mixed responsibilities

Flag code when one module is doing more than one of these jobs:

- request handling
- domain logic
- persistence
- presentation state
- formatting or transport glue

Preferred direction:

- backend routers validate, authorize, call services, shape responses
- backend services own domain rules
- repositories own persistence
- frontend views compose hooks and components
- shared clients own network behavior

### 2. Oversized units

Flag code when a function or component becomes hard to understand in one read.

Common symptoms:

- many branches or flags
- many local state variables
- repeated query-building blocks
- UI rendering mixed with data orchestration
- long sections that could be named and extracted

Preferred direction:

- extract focused helpers only when they improve ownership and readability
- keep top-level orchestration easy to scan
- avoid abstraction for its own sake

### 3. Duplication

Flag repeated logic when behavior must stay identical across multiple sites.

Common examples:

- the same filtering logic in multiple services
- repeated error parsing or response shaping
- duplicated UI state transitions
- repeated domain-specific constants

Preferred direction:

- extract a shared helper only when there is one clear owner
- do not create generic utility buckets for unrelated logic

### 4. Weak contracts

Flag places where boundaries rely on ad-hoc dictionaries or unclear shapes.

Preferred direction:

- explicit backend schemas
- explicit frontend types
- stable API payload shapes
- named return values over positional ambiguity

### 5. Poor testability

Flag code that is hard to validate in isolation.

Common symptoms:

- hidden side effects
- logic embedded in controllers or views
- implicit global state
- data loading and transformation tightly coupled

Preferred direction:

- isolate domain logic in services or hooks
- keep I/O boundaries thin
- make state transitions explicit

### 6. Invisible failure modes

Flag code that hides degraded behavior.

Common symptoms:

- swallowed exceptions
- vague logging
- silent fallback values masking real errors
- UI states that hide contradiction or missing evidence

## Review output

For a substantial review, report:

- scope
- findings by severity
- concrete file references
- smallest safe follow-up
- validation gap if a risk was not tested

## Anti-patterns worth calling out

- god components or methods
- cross-layer shortcuts
- one-off patterns that diverge from nearby code
- behavior-preserving refactors mixed with feature changes
- stale docs that read like implementation tutorials

## Rule of thumb

If a new contributor cannot identify the owner module and the main data flow quickly, maintainability has already degraded.
