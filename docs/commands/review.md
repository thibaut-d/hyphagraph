# Review Command

Use this command when reviewing a diff, changed files, or a module for quality and project alignment.

## Review priorities

Focus on:
- architecture alignment
- readability
- typing quality
- provenance and explainability safety
- hidden side effects
- contradiction visibility in user-facing flows
- pattern consistency
- test adequacy

## Steps

1. Read the relevant repository guidance.
2. Define the review scope.
3. Identify strengths briefly.
4. List issues with severity.
5. Prefer concrete examples and actionable fixes.
6. Flag missing tests or validation gaps.

## Severity levels

- Critical: likely incorrect behavior, provenance loss, hidden contradiction handling, security issue, or broken contract
- Major: significant readability, maintainability, or boundary-discipline problem
- Minor: useful cleanup, but not urgent

## Output format

Provide:
- scope reviewed
- strengths
- critical issues
- major issues
- minor issues
- suggested next actions
