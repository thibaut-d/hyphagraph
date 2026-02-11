# Backend Tests

Test suite using pytest + pytest-asyncio.

## Running Tests

```bash
cd backend

pytest                                           # All tests
pytest tests/test_auth_utils.py                  # Specific file
pytest tests/test_user_service.py::TestUserCreation  # Specific class
pytest -k "password"                             # Pattern match
pytest -m unit                                   # By marker
pytest -m integration                            # By marker

# With coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Verbose
pytest -v
```

## Configuration

Tests configured via `pytest.ini`:
- **Async mode**: `asyncio_mode = auto` (automatic async test detection)
- **Discovery**: finds all `test_*.py` files
- **Markers**: `unit`, `integration`, `auth`

## File Conventions

- Test files: `test_*.py` in `tests/` directory
- Classes: `TestFeatureName`
- Methods: `test_something_success`, `test_something_failure`
- Fixtures: use `@pytest.fixture` for shared setup

## Key Patterns

- Use `AsyncMock` for all DB operations
- Mark async tests with `@pytest.mark.asyncio`
- AAA pattern: Arrange / Act / Assert
- Test both success and error paths
- Use `app.dependency_overrides[get_db]` for DB mocking in endpoint tests

For detailed testing patterns and examples, see `docs/ai/AI_CONTEXT_BACKEND.md`.
