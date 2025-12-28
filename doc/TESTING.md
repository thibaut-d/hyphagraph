# Testing Guide

Comprehensive testing documentation for HyphaGraph authentication system.

## Overview

The HyphaGraph project includes extensive test coverage for both backend and frontend authentication functionality:

- **Backend**: pytest-based unit and integration tests
- **Frontend**: Vitest-based unit tests for API clients

## Quick Start

### Backend Tests

```bash
cd backend
uv pip install -e ".[dev]"  # Install with dev dependencies
pytest                       # Run all tests
pytest -v                    # Verbose output
pytest --cov=app            # With coverage
```

### Frontend Tests

```bash
cd frontend
npm install -D vitest @vitest/ui @vitejs/plugin-react jsdom
npm test                     # Run all tests
npm run test:ui             # Run with web UI
npm run test:coverage       # With coverage
```

## Backend Test Suite

### Test Files

Located in `backend/tests/`:

1. **`test_auth_utils.py`** - Authentication utility functions
   - Password hashing (bcrypt)
   - JWT token creation and validation
   - Refresh token generation and verification
   - **18 test cases**

2. **`test_user_service.py`** - UserService business logic
   - User registration and creation
   - Authentication and login
   - Password management (change, reset)
   - Email verification
   - Refresh token management
   - **15+ test cases**

3. **`test_auth_endpoints.py`** - API endpoint integration tests
   - Registration endpoint
   - Login endpoint
   - Token refresh and logout
   - Password change and reset
   - Email verification flow
   - Account management
   - **30+ test cases**

### Configuration

**`backend/pytest.ini`**
- Test discovery patterns
- Async test support (asyncio_mode = auto)
- Custom markers (unit, integration, auth, slow, db)
- Logging configuration
- Coverage integration

### Running Backend Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_auth_utils.py

# Specific test class
pytest tests/test_user_service.py::TestUserCreation

# Specific test method
pytest tests/test_user_service.py::TestUserCreation::test_create_user_success

# Tests by marker
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m auth             # Auth-related tests

# With coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Verbose with locals
pytest -vv -l

# Stop on first failure
pytest -x

# Match pattern
pytest -k "password"
```

### Backend Test Coverage

- **Authentication Utilities**: 100% (all functions tested)
- **UserService**: >90% (comprehensive business logic tests)
- **Auth Endpoints**: >85% (all endpoints with success and error cases)

## Frontend Test Suite

### Test Files

Located in `frontend/src/api/`:

1. **`auth.test.ts`** - Authentication API client functions
   - Login (form-urlencoded)
   - Register (JSON)
   - Get current user
   - Refresh access token
   - Logout
   - Password reset flow
   - Email verification flow
   - Error handling
   - **40+ test cases**

### Configuration

**`frontend/vitest.config.ts`**
- jsdom environment for React testing
- Global test utilities (describe, it, expect)
- Coverage configuration (v8 provider)
- Mock auto-reset between tests

### Running Frontend Tests

```bash
# All tests
npm test

# Watch mode (auto-rerun on changes)
npm test
# (vitest runs in watch mode by default)

# With UI
npm run test:ui

# With coverage
npm run test:coverage

# Specific file
npx vitest auth.test.ts

# Match pattern
npx vitest --grep "login"
```

### Frontend Test Coverage

- **Auth API Client**: >95% (all functions with success and error paths)

## Test Architecture

### Backend Testing Patterns

#### Fixtures
```python
@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db
```

#### Async Tests
```python
@pytest.mark.asyncio
async def test_async_function(mock_db):
    result = await async_function(mock_db)
    assert result.success
```

#### Exception Testing
```python
with pytest.raises(HTTPException) as exc_info:
    await function_that_raises()

assert exc_info.value.status_code == 400
```

#### Mocking
```python
with patch("app.services.user_service.hash_password") as mock_hash:
    mock_hash.return_value = "hashed"
    result = await service.create_user(data)
```

### Frontend Testing Patterns

#### Mocking Modules
```typescript
vi.mock('./client', () => ({
  apiFetch: vi.fn(),
}));
```

#### Async Testing
```typescript
it('should fetch data', async () => {
  (apiFetch as any).mockResolvedValue({ id: 1 });
  const result = await fetchData();
  expect(result).toEqual({ id: 1 });
});
```

#### Error Testing
```typescript
it('should handle errors', async () => {
  (apiFetch as any).mockRejectedValue(new Error('Failed'));
  await expect(fetchData()).rejects.toThrow('Failed');
});
```

## Test Coverage Goals

### Overall Targets
- **Backend Overall**: >80%
- **Frontend Overall**: >80%
- **Authentication Code**: >90%
- **Critical Security Paths**: 100%

### Critical Paths (100% Coverage Required)
- Password hashing and verification
- JWT token generation and validation
- Refresh token management
- Password reset flow
- Email verification flow
- Authentication checks

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: |
          cd backend
          pip install uv
          uv pip install -e ".[dev]"
          pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v3

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: |
          cd frontend
          npm ci
          npm test
          npm run test:coverage
```

## Writing New Tests

### Backend Test Template

```python
"""
Description of what this test module covers.
"""
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def setup():
    """Fixture description."""
    return AsyncMock()

class TestFeature:
    """Tests for Feature."""

    @pytest.mark.asyncio
    async def test_success_case(self, setup):
        """Should successfully do X when Y."""
        # Arrange
        expected = "result"

        # Act
        result = await function_under_test(setup)

        # Assert
        assert result == expected

    @pytest.mark.asyncio
    async def test_error_case(self, setup):
        """Should raise error when invalid input."""
        with pytest.raises(HTTPException) as exc_info:
            await function_under_test(invalid_input)

        assert exc_info.value.status_code == 400
```

### Frontend Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('./dependency', () => ({
  dependency: vi.fn(),
}));

describe('Feature', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should do X successfully', async () => {
    // Arrange
    const expected = { data: 'value' };

    // Act
    const result = await functionUnderTest();

    // Assert
    expect(result).toEqual(expected);
  });

  it('should handle errors', async () => {
    // Arrange
    const error = new Error('Test error');

    // Act & Assert
    await expect(functionUnderTest()).rejects.toThrow('Test error');
  });
});
```

## Best Practices

### General
1. **Test Behavior, Not Implementation**: Focus on what code does, not how
2. **Arrange-Act-Assert**: Structure tests clearly
3. **One Assertion Per Test**: Keep tests focused
4. **Descriptive Names**: Use "should X when Y" format
5. **Test Edge Cases**: Empty inputs, null values, boundaries
6. **Mock External Dependencies**: Database, APIs, email services

### Backend Specific
1. **Use AsyncMock**: For async database operations
2. **Mark Async Tests**: Always use `@pytest.mark.asyncio`
3. **Test Security**: Verify authentication and authorization
4. **Test Validation**: Check input validation and error messages
5. **Test Database Operations**: Verify commits, rollbacks, refreshes

### Frontend Specific
1. **Mock API Calls**: Don't make real HTTP requests
2. **Clear Mocks**: Reset between tests with `beforeEach`
3. **Test Type Safety**: Ensure correct TypeScript types
4. **Test Error Handling**: Verify error propagation
5. **Test Request Formatting**: Check headers, body, method

## Troubleshooting

### Backend Issues

**Import Errors**
```bash
pip install -e .  # Install package in editable mode
```

**Async Warnings**
- Check `pytest-asyncio` is installed
- Verify `asyncio_mode = auto` in pytest.ini

**Database Errors**
- Tests use mocked database
- Ensure proper mocking in fixtures

### Frontend Issues

**Module Not Found**
```bash
npm install  # Install dependencies
```

**Mocks Not Working**
- Place `vi.mock()` at top of file
- Use `vi.clearAllMocks()` in `beforeEach`

**Type Errors**
- Cast mocks: `(mockFn as any)`
- Or use: `vi.mocked(mockFn)`

## Documentation

- **Backend Tests**: See `backend/tests/README.md`
- **Frontend Tests**: See `frontend/tests/README.md`
- **pytest Docs**: https://docs.pytest.org/
- **Vitest Docs**: https://vitest.dev/

## Coverage Reports

### Generate Reports

```bash
# Backend
cd backend
pytest --cov=app --cov-report=html
# Open backend/htmlcov/index.html

# Frontend
cd frontend
npm run test:coverage
# Open frontend/coverage/index.html
```

### Interpreting Coverage

- **Green**: >80% coverage
- **Yellow**: 60-80% coverage
- **Red**: <60% coverage

Focus on:
1. Authentication and security code (should be 100%)
2. Business logic (should be >90%)
3. API endpoints (should be >85%)

## Next Steps

1. **Add More Tests**: Continue expanding coverage
2. **Component Tests**: Add React component tests with Testing Library
3. **E2E Tests**: Consider Playwright or Cypress for full flow testing
4. **Performance Tests**: Add load testing for API endpoints
5. **Security Tests**: Penetration testing for authentication
