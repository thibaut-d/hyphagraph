# Debug Command

Use this command when investigating a bug, failing test, unexpected response, or broken UI or pipeline flow.

## Steps

1. State the symptom clearly.
2. Identify the failing boundary: API, service, repository, UI, test, or environment.
3. Reproduce the issue if possible.
4. Narrow the scope to the smallest responsible module.
5. Inspect inputs, outputs, assumptions, and state transitions.
6. Explain the likely root cause in plain language.
7. Apply the smallest safe fix.
8. Validate the fix and check for obvious regressions nearby.

## Debugging rules

- do not patch blindly
- do not confuse a symptom with the root cause
- keep temporary debug artifacts in `.temp/`
- preserve unrelated behavior
- pay extra attention to provenance, auth, and frontend/backend contract drift

## Output format

Provide:
- symptom
- likely root cause
- affected files or modules
- fix applied or proposed
- validation steps and outcome
