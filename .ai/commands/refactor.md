# Refactor Command

Use this command when improving code structure without intentionally changing behavior, unless a fix is explicitly part of the task.

## Required behavior

1. Understand the current behavior before changing it.
2. Read the relevant module guidance and nearby patterns.
3. Propose a short refactor plan for non-trivial work.
4. Keep changes incremental and easy to review.
5. Avoid changing public contracts unless necessary.
6. Improve readability, typing, locality, and pattern consistency.
7. Validate that behavior is preserved, or explain any intended behavior change.

## Priorities

Prioritize:
- thinner route and view layers
- smaller focused functions
- stronger typing
- fewer raw dict contracts
- less hidden coupling
- clearer module ownership

## Output format

Provide:
- current structural issue
- refactor plan
- key edits made
- behavior preserved or intentionally changed
- validation performed
- remaining risks
