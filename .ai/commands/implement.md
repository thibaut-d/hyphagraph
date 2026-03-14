# Implement Command

Use this command when adding a feature or materially extending existing behavior.

## Required behavior

1. Read the bootstrap context if it has not already been loaded.
2. Inspect the relevant owner module before editing.
3. Identify the backend, frontend, and test boundaries affected.
4. Write a short plan for non-trivial work.
5. Reuse existing repository patterns before introducing new abstractions.
6. Keep changes local, readable, and typed.
7. Preserve provenance, explainability, and contradiction visibility where relevant.
8. Run the most relevant tests or checks and report any blocker clearly.

## HyphaGraph checklist

- objective understood
- owning module identified
- architectural invariants checked
- backend/frontend contract impact identified
- provenance or revision impact identified when relevant
- contradiction and evidence visibility preserved when relevant
- temporary artifacts confined to `.temp/`

## Output format

Provide:
- short plan
- implementation summary
- files changed
- validation performed
- remaining risks or follow-up items
