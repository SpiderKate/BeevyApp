"""
Pytest configuration and shared fixtures for all test modules.
Provides common fixtures, setup/teardown, and test configuration.
"""

import pytest
import sys
import os
import sqlite3
import bcrypt
from pathlib import Path
from io import BytesIO

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


# ===== Pytest Configuration =====

def pytest_configure(config):
    """Configure pytest before test collection"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests as authentication tests"
    )
    config.addinivalue_line(
        "markers", "database: marks tests as database tests"
    )


# ===== Session Scope Fixtures =====

@pytest.fixture(scope="session")
def app_instance():
    """Create Flask app instance for entire test session"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    yield app


@pytest.fixture(scope="session")
def database():
    """Ensure database exists and is accessible for session"""
    db_path = Path("beevy.db")
    if not db_path.exists():
        # Create a basic database if it doesn't exist
        conn = sqlite3.connect(str(db_path))
        conn.close()
    
    yield str(db_path)


# ===== Function Scope Fixtures =====

@pytest.fixture
def client(app_instance):
    """Create a test client for Flask application"""
    return app_instance.test_client()


@pytest.fixture
def runner(app_instance):
    """Create a CLI test runner"""
    return app_instance.test_cli_runner()


@pytest.fixture
def app_context(app_instance):
    """Provide application context for tests"""
    with app_instance.app_context():
        yield app_instance


@pytest.fixture
def request_context(app_instance):
    """Provide request context for tests"""
    with app_instance.test_request_context():
        yield app_instance


# ===== Database Fixtures =====

@pytest.fixture
def db_connection():
    """Create a fresh database connection for each test"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None  # Autocommit mode
    
    yield conn
    
    conn.close()


@pytest.fixture
def main_db():
    """Access main application database"""
    conn = sqlite3.connect("beevy.db")
    conn.row_factory = sqlite3.Row
    
    yield conn
    
    conn.close()


# ===== User Fixtures =====

@pytest.fixture
def test_user_data():
    """Standard test user data"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "avatar": "https://example.com/avatar.png",
        "description": "Test user description"
    }


@pytest.fixture
def test_user(main_db, test_user_data):
    """Create a test user in the main database"""
    cursor = main_db.cursor()
    hashed = bcrypt.hashpw(test_user_data['password'].encode(), bcrypt.gensalt())
    
    try:
        cursor.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        """, (test_user_data['username'], test_user_data['email'], hashed))
        main_db.commit()
    except sqlite3.OperationalError:
        # Table might not exist, that's ok
        pass
    except sqlite3.IntegrityError:
        # User might already exist, clean it up first
        cursor.execute("DELETE FROM users WHERE username = ?", (test_user_data['username'],))
        main_db.commit()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        """, (test_user_data['username'], test_user_data['email'], hashed))
        main_db.commit()
    
    yield test_user_data
    
    # Cleanup
    try:
        cursor.execute("DELETE FROM users WHERE username = ?", (test_user_data['username'],))
        main_db.commit()
    except:
        pass


@pytest.fixture
def authenticated_client(client, test_user):
    """Create a client logged in with test user"""
    client.post('/login', data={
        'username': test_user['username'],
        'password': test_user['password']
    })
    
    return client


# ===== File Fixtures =====

@pytest.fixture
def sample_image():
    """Create a sample PNG image for testing"""
    from PIL import Image
    
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return img_io


@pytest.fixture
def sample_jpg():
    """Create a sample JPG image for testing"""
    from PIL import Image
    
    img = Image.new('RGB', (100, 100), color='blue')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    
    return img_io


@pytest.fixture
def sample_large_image():
    """Create a large sample image for testing"""
    from PIL import Image
    
    img = Image.new('RGB', (2048, 2048), color='green')
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return img_io


# ===== Session Fixtures =====

@pytest.fixture
def session_data():
    """Standard session data for testing"""
    return {
        'username': 'testuser',
        'user_language': 'en',
        'theme': 'light'
    }


# ===== Art/Content Fixtures =====

@pytest.fixture
def sample_art_data():
    """Standard art/content data for testing"""
    return {
        "title": "Test Artwork",
        "description": "A test artwork for unit tests",
        "image_path": "/static/uploads/test.png",
        "tags": ["test", "sample"]
    }


# ===== Translation Fixtures =====

@pytest.fixture
def supported_languages():
    """List of supported languages"""
    return ["en", "cs"]


@pytest.fixture
def sample_translations():
    """Sample translation strings"""
    return {
        "en": {
            "nav.home": "Home",
            "nav.shop": "Shop",
            "flash.login_first": "Please log in first"
        },
        "cs": {
            "nav.home": "Domů",
            "nav.shop": "Obchod",
            "flash.login_first": "Prosím přihlaste se nejdříve"
        }
    }


# ===== Utility Fixtures =====

@pytest.fixture
def temp_upload_dir(tmp_path):
    """Create a temporary upload directory"""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    
    (upload_dir / "avatar").mkdir()
    (upload_dir / "shop").mkdir()
    
    return upload_dir


@pytest.fixture
def clean_database():
    """Provide a clean database state before and after test"""
    # Setup
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='table'
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    # Store data (backup)
    backup = {}
    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        backup[table] = cursor.fetchall()
    
    yield conn
    
    # Cleanup - restore original state or delete test data
    # This depends on your needs
    conn.close()


# ===== Pytest Hooks =====

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        # Add markers based on file name
        if "auth" in item.nodeid:
            item.add_marker(pytest.mark.auth)
        if "database" in item.nodeid:
            item.add_marker(pytest.mark.database)
        if "api" in item.nodeid:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(autouse=True)
def reset_app_context(app_instance):
    """Reset app context between tests"""
    yield
    
    # Cleanup after each test
    if app_instance.config['TESTING']:
        pass  # App is in testing mode, no special cleanup needed


# ===== Assertion Helpers =====

class HTTPAssertions:
    """Helper class for HTTP response assertions"""
    
    @staticmethod
    def assert_status_ok(response):
        """Assert response status is 200"""
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    @staticmethod
    def assert_status_redirect(response):
        """Assert response status is 3xx"""
        assert 300 <= response.status_code < 400, f"Expected 3xx, got {response.status_code}"
    
    @staticmethod
    def assert_status_not_found(response):
        """Assert response status is 404"""
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    @staticmethod
    def assert_content_type_html(response):
        """Assert response content type is HTML"""
        assert 'text/html' in response.content_type, \
            f"Expected HTML content type, got {response.content_type}"
    
    @staticmethod
    def assert_content_type_json(response):
        """Assert response content type is JSON"""
        assert 'application/json' in response.content_type, \
            f"Expected JSON content type, got {response.content_type}"


@pytest.fixture
def assertions():
    """Provide assertion helpers to tests"""
    return HTTPAssertions()


# ===== Logging Configuration =====

@pytest.fixture(scope="session")
def logging_config():
    """Configure logging for tests"""
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return logging


# ===== Performance Fixtures =====

@pytest.fixture
def timer():
    """Simple timer for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start = None
            self.end = None
        
        def __enter__(self):
            self.start = time.time()
            return self
        
        def __exit__(self, *args):
            self.end = time.time()
        
        @property
        def elapsed(self):
            return self.end - self.start if self.end and self.start else 0
    
    return Timer()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
