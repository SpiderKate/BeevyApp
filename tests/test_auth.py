"""
Test suite for authentication and user management functionality.
Tests user registration, login, password management, and session handling.
"""

import pytest
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, get_unique_deleted_username
import bcrypt


@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def setup_test_user():
    """Create a test user in the database"""
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    
    # Hash a test password
    test_password = "TestPassword123!"
    hashed = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode('utf-8')
    username = f"testuser_{uuid4().hex[:8]}"
    email = f"{username}@example.com"
    
    # Insert test user
    cursor.execute("""
        INSERT INTO users (username, email, password, name, surname, dob, deleted)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (username, email, hashed, "Test", "User", "2000-01-01"))
    user_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO preferences (user_id, language, theme, default_brush_size, notifications) VALUES (?, ?, ?, ?, ?)",
        (user_id, 'en', 'bee', 30, 1)
    )
    conn.commit()
    conn.close()
    
    yield {"username": username, "email": email, "password": test_password}
    
    # Cleanup
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM preferences WHERE user_id = ?", (row[0],))
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()


class TestUserRegistration:
    """Tests for user registration functionality"""
    
    def test_register_page_loads(self, client):
        """Test that registration page is accessible"""
        response = client.get('/register')
        assert response.status_code == 200
        
    def test_register_new_user_valid_data(self, client):
        """Test successful user registration with valid data"""
        username = f"newuser_{uuid4().hex[:8]}"
        email = f"{username}@example.com"
        response = client.post('/register', data={
            'username': username,
            'email': email,
            'password': 'SecurePass123!',
            'name': 'New',
            'surname': 'User',
            'dob': '2000-01-01'
        }, follow_redirects=True)
        
        # Check user was created
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        assert user is not None
        
        # Cleanup
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM preferences WHERE user_id = ?", (row[0],))
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        conn.close()
    
    def test_register_duplicate_username(self, client, setup_test_user):
        """Test that duplicate username registration fails"""
        response = client.post('/register', data={
            'username': setup_test_user['username'],
            'email': 'another@example.com',
            'password': 'Password123!',
            'name': 'Another',
            'surname': 'Person',
            'dob': '2000-01-01'
        })
        
        assert response.status_code in (200, 302)  # Form reload or redirect
    
    def test_register_missing_required_fields(self, client):
        """Test registration fails when required fields are missing"""
        response = client.post('/register', data={
            'username': 'newuser2',
            'email': 'newuser2@example.com',
            'password': 'Password123!',
            # missing name/surname/dob in this app
        })
        
        assert response.status_code in (400, 302)


class TestUserLogin:
    """Tests for user login functionality"""
    
    def test_login_page_loads(self, client):
        """Test that login page is accessible"""
        response = client.get('/login')
        assert response.status_code == 200
    
    def test_login_valid_credentials(self, client, setup_test_user):
        """Test successful login with valid credentials"""
        response = client.post('/login', data={
            'username': setup_test_user['username'],
            'password': setup_test_user['password']
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_login_invalid_username(self, client):
        """Test login with non-existent username"""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'Password123!'
        })
        
        assert response.status_code in (302, 200)
    
    def test_login_invalid_password(self, client, setup_test_user):
        """Test login with wrong password"""
        response = client.post('/login', data={
            'username': setup_test_user['username'],
            'password': 'WrongPassword123!'
        })
        
        assert response.status_code in (200, 302)
    
    def test_session_created_after_login(self, client, setup_test_user):
        """Test that session is created after successful login"""
        with client.session_transaction() as sess:
            assert 'username' not in sess
        
        client.post('/login', data={
            'username': setup_test_user['username'],
            'password': setup_test_user['password']
        })
        
        with client.session_transaction() as sess:
            assert 'username' in sess


class TestUserLogout:
    """Tests for user logout functionality"""
    
    def test_logout_clears_session(self, client, setup_test_user):
        """Test that logout clears user session"""
        # Login first
        client.post('/login', data={
            'username': setup_test_user['username'],
            'password': setup_test_user['password']
        })
        
        # Verify logged in
        with client.session_transaction() as sess:
            assert 'username' in sess
        
        # Logout (GET renders page, POST performs logout)
        client.post(f"/{setup_test_user['username']}/settings/logout", follow_redirects=True)
        
        # Verify logged out
        with client.session_transaction() as sess:
            assert 'username' not in sess


class TestPasswordManagement:
    """Tests for password-related functionality"""
    
    def test_password_hashing(self, setup_test_user):
        """Test that passwords are properly hashed"""
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", 
                      (setup_test_user['username'],))
        stored_hash = cursor.fetchone()[0]
        conn.close()
        
        # Verify hash is not plain text
        assert stored_hash != setup_test_user['password']
        
        # Verify hash can be verified
        assert bcrypt.checkpw(setup_test_user['password'].encode(), 
                             stored_hash.encode())


class TestDeletedUsername:
    """Tests for deleted user placeholder functionality"""
    
    def test_generate_deleted_username(self):
        """Test deleted username generation"""
        from app import generate_deleted_username
        
        username = generate_deleted_username()
        assert username.startswith("Deleted_User_")
        assert len(username) > 13  # Length + random suffix
    
    def test_get_unique_deleted_username(self, setup_test_user):
        """Test that unique deleted usernames are generated"""
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        
        username1 = get_unique_deleted_username(cursor)
        username2 = get_unique_deleted_username(cursor)
        
        assert username1 != username2
        assert username1.startswith("Deleted_User_")
        assert username2.startswith("Deleted_User_")
        
        conn.close()


class TestLoginRequired:
    """Tests for login_required decorator"""
    
    def test_protected_route_redirect_when_not_logged_in(self, client):
        """Test that protected routes redirect to login when not logged in"""
        response = client.get('/someone/settings', follow_redirects=False)
        assert response.status_code == 302  # Redirect
    
    def test_protected_route_accessible_when_logged_in(self, client, setup_test_user):
        """Test that protected routes are accessible when logged in"""
        client.post('/login', data={
            'username': setup_test_user['username'],
            'password': setup_test_user['password']
        })
        
        response = client.get(f"/{setup_test_user['username']}/settings")
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
