# Frontend Tests

Test suite for HyphaGraph frontend authentication API client.

## Test Structure

```
src/
├── api/
│   ├── auth.ts                # Auth API client
│   └── auth.test.ts           # Auth API tests
└── ...
```

## Test Coverage

### Authentication API Client (`auth.test.ts`)
- **Login**: Form-urlencoded credentials, token response
- **Register**: JSON registration, response validation
- **Get Current User**: User info retrieval
- **Refresh Token**: Access token refresh
- **Logout**: Token revocation
- **Password Reset**: Request reset, reset with token
- **Email Verification**: Verify email, resend verification
- **Error Handling**: API error propagation

## Prerequisites

Install test dependencies:

```bash
cd frontend
npm install -D vitest @vitest/ui @vitejs/plugin-react jsdom
```

Required packages:
- `vitest` - Fast unit test framework (Vite-native)
- `@vitest/ui` - Web-based test UI
- `jsdom` - DOM environment for React testing
- `@vitejs/plugin-react` - React support in Vitest

## Running Tests

### Run All Tests

```bash
cd frontend
npm test
```

### Run Tests in Watch Mode

```bash
npm test
# Tests will re-run automatically when files change
```

### Run Tests with UI

```bash
npm run test:ui
```

This opens a browser-based UI showing:
- Test results with detailed logs
- Code coverage
- Test file explorer
- Ability to run specific tests

### Run Tests with Coverage

```bash
npm run test:coverage
```

Coverage report will be in `coverage/` directory.

### Run Specific Tests

```bash
# Run specific test file
npx vitest auth.test.ts

# Run tests matching pattern
npx vitest --grep "login"

# Run in specific directory
npx vitest src/api
```

## Test Configuration

Tests are configured via `vitest.config.ts`:

- **Environment**: jsdom (for React/DOM testing)
- **Globals**: `describe`, `it`, `expect` available without imports
- **Coverage**: v8 provider with HTML/text reports
- **Mocking**: Auto-reset between tests

## Writing New Tests

### Test File Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { functionToTest } from './module';

// Mock dependencies
vi.mock('./dependency', () => ({
  dependency: vi.fn(),
}));

describe('Feature Name', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('functionToTest', () => {
    it('should do something successfully', async () => {
      // Arrange
      const expected = 'result';

      // Act
      const result = await functionToTest();

      // Assert
      expect(result).toBe(expected);
    });

    it('should handle errors', async () => {
      // Arrange
      const mockError = new Error('Test error');

      // Act & Assert
      await expect(functionToTest()).rejects.toThrow('Test error');
    });
  });
});
```

### Best Practices

1. **Mock External Dependencies**: Use `vi.mock()` for API clients
2. **Clear Mocks**: Reset mocks between tests with `beforeEach`
3. **Test Success and Failure**: Cover both happy paths and errors
4. **Descriptive Names**: Use clear test descriptions
5. **Async/Await**: Use async/await for promise-based code
6. **Type Safety**: Maintain TypeScript types in tests

### Common Patterns

#### Mocking Modules
```typescript
vi.mock('./client', () => ({
  apiFetch: vi.fn(),
}));
```

#### Testing Async Functions
```typescript
it('should fetch data', async () => {
  const mockData = { id: 1 };
  (apiFetch as any).mockResolvedValue(mockData);

  const result = await fetchData();

  expect(result).toEqual(mockData);
});
```

#### Testing Errors
```typescript
it('should throw on error', async () => {
  const error = new Error('API error');
  (apiFetch as any).mockRejectedValue(error);

  await expect(fetchData()).rejects.toThrow('API error');
});
```

#### Verifying Function Calls
```typescript
it('should call API with correct params', async () => {
  await login({ username: 'test', password: 'pass' });

  expect(apiFetch).toHaveBeenCalledWith('/auth/login', {
    method: 'POST',
    body: expect.any(URLSearchParams),
  });
});
```

## Test Organization

### File Naming
- Test files: `*.test.ts` or `*.spec.ts`
- Place test files next to source files
- Example: `auth.ts` → `auth.test.ts`

### Test Structure
```typescript
describe('Module/Component Name', () => {
  describe('Function/Method Name', () => {
    it('should behavior in specific scenario', () => {
      // Test implementation
    });
  });
});
```

## Continuous Integration

Example GitHub Actions workflow:

```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: cd frontend && npm ci
      - run: cd frontend && npm test
      - run: cd frontend && npm run test:coverage
```

## Debugging Tests

### VS Code Debugging
Add to `.vscode/launch.json`:
```json
{
  "type": "node",
  "request": "launch",
  "name": "Debug Vitest Tests",
  "runtimeExecutable": "npm",
  "runtimeArgs": ["test"],
  "console": "integratedTerminal"
}
```

### Console Logging
```typescript
it('should work', () => {
  console.log('Debug info:', value);
  expect(value).toBe(expected);
});
```

### Inspect Mode
```bash
node --inspect-brk ./node_modules/.bin/vitest
```

## Coverage Goals

Target coverage levels:
- **Overall**: > 80%
- **API Clients**: > 90%
- **Critical Paths**: 100%

View coverage:
```bash
npm run test:coverage
open coverage/index.html
```

## Common Issues

### Module Not Found
- Ensure dependencies are installed: `npm install`
- Check import paths are correct

### Mock Not Working
- Verify `vi.mock()` is called before imports
- Use `vi.clearAllMocks()` in `beforeEach`

### Type Errors in Tests
- Cast mocks: `(mockFn as any).mockResolvedValue()`
- Or use proper typing: `vi.mocked(mockFn)`

### Tests Not Running
- Check file matches pattern: `*.test.ts`
- Ensure file is in `src/` directory
- Verify vitest.config.ts include patterns

## Additional Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/) - For React component tests
- [Mock Service Worker](https://mswjs.io/) - For API mocking
