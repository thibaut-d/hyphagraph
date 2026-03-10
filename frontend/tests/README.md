# Frontend Tests

Unit and component tests using Vitest + React Testing Library.

## Running Tests

```bash
cd frontend

npm test                # All tests (watch mode)
npm run test:coverage   # With coverage report
npm run test:ui         # Browser-based test UI

# Specific file or pattern
npx vitest auth.test.ts
npx vitest --grep "login"
```

## Configuration

Tests configured via `vitest.config.ts`:
- **Environment**: jsdom
- **Globals**: `describe`, `it`, `expect` available without imports
- **Coverage**: v8 provider, HTML + text reports in `coverage/`
- **Mocking**: Auto-reset between tests

## File Conventions

- Test files: `*.test.ts` or `*.spec.ts`, placed next to source files
- Example: `auth.ts` → `auth.test.ts`
- Nested structure: `describe('Module') > describe('Function') > it('should...')`

## Key Patterns

- Mock API calls with `vi.mock('../api/client')`
- Use `vi.clearAllMocks()` in `beforeEach`
- AAA pattern: Arrange / Act / Assert
- Cover both success and error paths

For detailed testing patterns and examples, see `docs/ai/AI_CONTEXT_FRONTEND.md`.
