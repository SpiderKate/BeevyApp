# Quick Test Reference

Fast reference guide for running tests in BeevyApp.

## Installation

```bash
pip install pytest pytest-cov
```

## Quick Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py

# Run auth tests only
pytest -m auth

# Run with coverage report
pytest --cov=. --cov-report=html

# Run and stop at first failure
pytest -x

# Run tests matching a pattern
pytest -k "login"

# Run showing print statements
pytest -vv -s
```

## Filter by Category

```bash
# Unit tests only (no integration tests)
pytest -m unit

# Integration tests only
pytest -m "not unit"

# Authentication tests
pytest -m auth

# Database tests
pytest -m database

# Skip slow tests
pytest -m "not slow"
```

## Test Files Summary

| File                | Purpose                 | Command                            |
|---------------------|-------------------------|------------------------------------|
| test_auth.py        | User login/registration | `pytest tests/test_auth.py`        |
| test_api.py         | API endpoints           | `pytest tests/test_api.py`         |
| test_file_upload.py | Image upload/validation | `pytest tests/test_file_upload.py` |
| test_database.py    | Database operations     | `pytest tests/test_database.py`    |
| test_utils.py       | Utility functions       | `pytest tests/test_utils.py`       |
| test_backup.py      | Backup system           | `pytest tests/test_backup.py`      |
| test_migration.py   | Database migrations     | `pytest tests/test_migration.py`   |

## Before Committing Code

```bash
# Full test suite with coverage
pytest --cov=. --cov-report=term-missing
```

## Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# View: htmlcov/index.html in your browser

# Show coverage in terminal
pytest --cov=. --cov-report=term-missing
```

## Troubleshooting

```bash
# Run single test to debug
pytest tests/test_auth.py::TestUserLogin::test_login_valid_credentials -vv

# Show all output including prints
pytest -vv -s tests/test_auth.py

# See why tests are being skipped
pytest -rs

# Run with detailed traceback
pytest --tb=long
```

## Common Patterns

```bash
# Run tests and show slowest 10
pytest --durations=10

# Fail if any test is slow
pytest --durations=0 --durations-min=1.0

# Run in random order (good for finding dependencies)
pytest --random-order

# Re-run only failed tests
pytest --lf

# Run tests that failed last
pytest --ff
```

---

For detailed information, see [tests/README.md](README.md)
