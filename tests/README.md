# BeevyApp Test Suite

Comprehensive test suite for the BeevyApp Flask application, covering authentication, API endpoints, file uploads, database operations, and utility functions.

## Overview

This test suite provides extensive coverage of the BeevyApp project to ensure code quality and reliability during development and before deployment.

### Test Files

- **test_auth.py** - Authentication and user management tests
  - User registration
  - User login/logout
  - Password management
  - Session handling
  - Protected route access

- **test_api.py** - API endpoints and core functionality tests
  - Home page and routing
  - Shop functionality
  - Art detail pages
  - User profile pages
  - Drawing/collaboration routes
  - Static file serving
  - Database operations
  - Configuration validation

- **test_file_upload.py** - File upload and image processing tests
  - File extension validation
  - Image validation
  - Image metadata handling
  - Image watermarking
  - Secure filename handling
  - File size validation

- **test_database.py** - Database integration and model tests
  - Database connectivity
  - User table operations
  - Art table operations
  - Art ownership relationships
  - Database queries
  - Transaction handling

- **test_utils.py** - Utility function tests
  - Flash messages and translations
  - Deleted user placeholders
  - Backup utilities
  - Password hashing
  - DateTime handling
  - Configuration validation

- **conftest.py** - Shared pytest fixtures and configuration
  - Flask app instances
  - Test client setup
  - Database fixtures
  - User fixtures
  - File fixtures
  - Session fixtures
  - Assertion helpers

## Installation

### Prerequisites

Ensure you have pytest installed:

```bash
pip install pytest pytest-cov
```

All test dependencies should be in your `requirements.txt`:
```
pytest==9.0.2
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_auth.py
```

### Run Specific Test Class

```bash
pytest tests/test_auth.py::TestUserLogin
```

### Run Specific Test Function

```bash
pytest tests/test_auth.py::TestUserLogin::test_login_valid_credentials
```

### Run with Different Output Levels

```bash
# Verbose output
pytest -v

# Very verbose output with print statements
pytest -vv -s

# Short summary
pytest -q

# Show test names as they run
pytest -v --tb=short
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only auth tests
pytest -m auth

# Run everything except slow tests
pytest -m "not slow"

# Run database tests with verbose output
pytest -m database -v
```

### Run with Coverage Report

```bash
# Generate coverage report
pytest --cov=. --cov-report=html

# View coverage statistics in terminal
pytest --cov=. --cov-report=term-missing

# Coverage with specific directories
pytest --cov=app --cov=translations --cov=backup_utils
```

## Test Organization

Tests are organized by functionality:

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py             # Authentication tests
├── test_api.py              # API endpoint tests
├── test_file_upload.py      # File upload and image tests
├── test_database.py         # Database operation tests
├── test_utils.py            # Utility function tests
├── test_migration.py        # Database migration tests (existing)
├── test_backup.py           # Backup utility tests (existing)
├── checks/                  # Utility check modules
│   ├── check_art.py
│   ├── check_files.py
│   └── check_unused.py
└── pytest.log               # Test execution log
```

## Fixtures

Common fixtures available from `conftest.py`:

### App Fixtures
- `client` - Flask test client
- `app_instance` - Flask app instance
- `app_context` - Application context
- `request_context` - Request context

### Database Fixtures
- `db_connection` - Fresh in-memory database
- `main_db` - Main application database
- `clean_database` - Database with clean state

### User Fixtures
- `test_user_data` - Standard test user dictionary
- `test_user` - Created test user in database
- `authenticated_client` - Logged-in test client

### File Fixtures
- `sample_image` - Sample PNG image
- `sample_jpg` - Sample JPG image
- `sample_large_image` - Large test image
- `temp_upload_dir` - Temporary upload directory

### Utility Fixtures
- `assertions` - HTTP assertion helpers
- `timer` - Performance timer
- `sample_translations` - Translation samples

## Test Markers

Tests are marked with categories for selective execution:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Slower integration tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.database` - Database tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.file_upload` - File upload tests

## Best Practices

### Writing Tests

1. **Use descriptive names**: Test function names should describe what they test
   ```python
   def test_login_with_valid_credentials()  # Good
   def test_login()  # Not specific enough
   ```

2. **Follow Arrange-Act-Assert pattern**:
   ```python
   def test_user_creation(client, test_user_data):
       # Arrange
       username = test_user_data['username']
       
       # Act
       response = client.post('/register', data=test_user_data)
       
       # Assert
       assert response.status_code == 200
   ```

3. **Use fixtures to avoid repetition**:
   ```python
   def test_with_user(test_user):  # Uses fixture
       assert test_user['username'] == 'testuser'
   ```

4. **Clean up after yourself**:
   ```python
   def test_file_operations(tmp_path):
       # Fixture auto-cleans with tmp_path
       test_file = tmp_path / "test.txt"
   ```

### Running Tests Locally

Before committing:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific category
pytest -m auth -v
```

## Troubleshooting

### Tests Fail Due to Missing Database

```bash
# Ensure database exists or let app create it
python app.py

# Then run tests
pytest
```

### Tests Fail Due to Import Errors

```bash
# Ensure you're in the project root directory
cd /path/to/BeevyApp

# Run tests
pytest
```

### Tests Hang or Timeout

```bash
# Run with timeout (requires pytest-timeout)
pip install pytest-timeout
pytest --timeout=10
```

### Database Lock Errors

```bash
# Close any other connections to the database
# Or use in-memory database for tests (already configured in conftest.py)
```

## Coverage Goals

Aim for the following coverage:

- **Critical paths** (auth, payment): 100%
- **Main features** (uploads, art): 90%+
- **Utilities**: 85%+
- **Overall**: 80%+

```bash
# Check current coverage
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

## Continuous Integration

To use with CI/CD pipelines:

```bash
# Exit with failure if coverage drops below threshold
pytest --cov=. --cov-fail-under=80

# Generate XML report for CI tools
pytest --cov=. --cov-report=xml

# Generate JSON report
pytest --cov=. --cov-report=json
```

## Test Data

Test users and data are automatically created via fixtures. Key test accounts:

- **testuser** - Standard test user (password: TestPassword123!)
- **artist** - Artist test user
- **buyer** - Buyer/customer test user

These are created and cleaned up automatically during tests.

## Performance Testing

Monitor test execution time:

```bash
# Show slowest tests
pytest --durations=10

# Run with timing information
pytest -v -ra
```

## Adding New Tests

1. Create test file: `tests/test_feature_name.py`
2. Import fixtures from `conftest.py`
3. Write test classes grouping related tests
4. Add appropriate markers
5. Run: `pytest tests/test_feature_name.py -v`

Example:

```python
import pytest

class TestNewFeature:
    @pytest.mark.unit
    def test_feature_works(self, client, test_user):
        """Test that new feature works correctly"""
        # Your test code here
        assert True
```

## Maintenance

- Keep tests updated when code changes
- Remove obsolete tests
- Refactor duplicate test code into fixtures
- Review coverage reports regularly
- Update test documentation

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/testing/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)

## Contact & Support

For test-related questions or improvements, update this documentation and notify the team.

---

**Last Updated**: 2026-02-18  
**Test Suite Version**: 1.0  
**Python**: 3.9+  
**Pytest**: 9.0+
