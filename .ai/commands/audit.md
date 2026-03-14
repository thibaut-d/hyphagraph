# Audit Command

Use this command to evaluate a repository area against HyphaGraph's architecture and AI-readability rules.

## Steps

1. Read `.ai/AUDITS.md`.
2. Read `audit.md` if you need the detailed repository-specific checklist.
3. Define the audit scope explicitly.
4. Run only the most relevant audit categories for that scope.
5. Classify findings as Critical, Major, or Minor.
6. Prefer concrete file-level findings over general commentary.
7. Write a report in `.temp/` when the audit is substantial.
8. Record durable follow-up items in `TODO.md`.

## Minimum focus areas

At minimum consider:
- naming clarity
- boundary discipline
- typed contracts
- provenance and explainability where relevant
- contradiction visibility where relevant
- tests and validation gaps

## Output format

Provide:
- scope
- findings ordered by severity
- concrete file examples
- recommended fixes in priority order
- report path if one was written
