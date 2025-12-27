# Backend Tests

Comprehensive test suite for HyphaGraph backend authentication system.

## Test Structure

```
tests/
├── __init__.py                    # Test package initialization
├── test_auth_utils.py             # Unit tests for auth utilities
├── test_user_service.py           # Unit tests for UserService
├── test_auth_endpoints.py         # Integration tests for auth endpoints
└── README.md                      # This file
```

## Test Coverage

### 1. Authentication Utilities (`test_auth_utils.py`)
- **Password Hashing**: bcrypt hashing, verification, unicode support
- **JWT Tokens**: Token creation, decoding, expiration, validation
- **Refresh Tokens**: Token generation, hashing, verification, URL-safety

### 2. User Service (`test_user_service.py`)
- **User Creation**: Registration, duplicate email handling
- **Authentication**: Login, password verification, inactive users
- **Password Management**: Change password, reset requests, token expiration
- **Email Verification**: Token creation, verification, expired tokens
- **Refresh Tokens**: Token pair creation

### 3. Auth Endpoints (`test_auth_endpoints.py`)
- **Registration**: User creation, validation, email verification
- **Login**: Authentication, token generation, error handling
- **Token Management**: Refresh, logout, revocation
- **Password Operations**: Change password, reset flow
- **Email Verification**: Verification, resend verification
- **Account Management**: Profile updates, account deletion

## Running Tests

### Prerequisites

Install test dependencies:
```bash
# Using uv (recommended)
cd backend
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

Required test packages:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `httpx` - Async HTTP client for endpoint testing

### Run All Tests

```bash
cd backend
pytest
```

### Run Specific Test Files

```bash
# Auth utilities only
pytest tests/test_auth_utils.py

# User service only
pytest tests/test_user_service.py

# Auth endpoints only
pytest tests/test_auth_endpoints.py
```

### Run Tests by Category

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only auth-related tests
pytest -m auth
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term-missing

# Open coverage report
# Windows:
start htmlcov/index.html
# Linux/Mac:
open htmlcov/index.html
```

### Run in Verbose Mode

```bash
# Show detailed test output
pytest -v

# Show even more details (locals in tracebacks)
pytest -vv -l
```

### Run Specific Tests

```bash
# Run a specific test class
pytest tests/test_user_service.py::TestUserCreation

# Run a specific test method
pytest tests/test_user_service.py::TestUserCreation::test_create_user_success

# Run tests matching a pattern
pytest -k "password"
```

### Watch Mode (Auto-rerun on changes)

```bash
# Requires pytest-watch
pip install pytest-watch
ptw
```

## Test Configuration

Tests are configured via `pytest.ini`:

- **Async Mode**: `asyncio_mode = auto` - Automatic async test detection
- **Test Discovery**: Finds all `test_*.py` files
- **Markers**: Custom markers for categorizing tests
- **Logging**: Configurable logging levels
- **Coverage**: Integration with pytest-cov

## Writing New Tests

### Test File Template

```python
"""
Description of what this test file covers.
"""
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_dependency():
    """Fixture description."""
    return AsyncMock()

class TestFeatureName:
    """Test suite for FeatureName."""

    @pytest.mark.asyncio
    async def test_something_success(self, mock_dependency):
        """Test description."""
        # Arrange
        expected = "result"

        # Act
        result = await function_under_test()

        # Assert
        assert result == expected
```

### Best Practices

1. **Use Fixtures**: Share common setup code via fixtures
2. **Mock External Dependencies**: Use `AsyncMock` for async code
3. **Test Both Success and Failure**: Cover happy paths and error cases
4. **Descriptive Names**: Use clear, descriptive test names
5. **Arrange-Act-Assert**: Structure tests clearly
6. **Async Tests**: Mark async tests with `@pytest.mark.asyncio`
7. **Markers**: Use markers to categorize tests

### Common Patterns

#### Mocking AsyncSession (Database)
```python
@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db
```

#### Testing Exceptions
```python
with pytest.raises(HTTPException) as exc_info:
    await function_that_raises()

assert exc_info.value.status_code == 400
assert "error message" in exc_info.value.detail
```

#### Patching Dependencies
```python
with patch("app.services.user_service.hash_password") as mock_hash:
    mock_hash.return_value = "hashed"
    result = await service.create_user(data)
```

## Continuous Integration

Tests should be run automatically in CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    cd backend
    pytest --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Import Errors
- Ensure backend package is installed: `pip install -e .`
- Check PYTHONPATH includes project root

### Async Test Warnings
- Ensure `pytest-asyncio` is installed
- Check `asyncio_mode = auto` in pytest.ini

### Slow Tests
- Run only unit tests: `pytest -m unit`
- Use `-x` flag to stop on first failure
- Run specific test files instead of all tests

### Database Connection Errors
- Tests use mocked database - no real DB needed
- If seeing DB errors, check that dependencies are properly mocked

## Code Coverage Goals

Target coverage levels:
- **Overall**: > 80%
- **Authentication**: > 90%
- **Critical Paths**: 100%

Check current coverage:
```bash
pytest --cov=app --cov-report=term-missing
```
