# Testing for merge-mcp

This directory contains tests for the merge-mcp project.

## Test Structure

- `unit/`: Unit tests for individual components

## Running Tests

To run all tests:

```bash
python -m pytest
```

To run a specific test file:

```bash
python -m pytest tests/unit/test_server.py
```

To run tests with verbose output:

```bash
python -m pytest -v
```

## Test Coverage

To run tests with coverage reporting:

```bash
python -m pytest --cov=merge_mcp
```

Note: You'll need to install pytest-cov for coverage reporting:

```bash
pip install pytest-cov
```

## Writing Tests

When writing new tests:

1. Unit tests should be placed in the `unit/` directory
2. Integration tests should be placed in the `integration/` directory
3. Use the fixtures defined in `conftest.py` where appropriate
4. For async tests, use the `@pytest.mark.asyncio` decorator
