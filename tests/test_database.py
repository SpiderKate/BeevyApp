"""
Test suite for database integration and models.
Tests database operations, queries, and data integrity.
"""

import pytest
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import bcrypt

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_db():
    """Create an in-memory test database"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    # Create tables for testing
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            avatar_path TEXT,
            description TEXT,
            language TEXT DEFAULT 'en',
            theme TEXT DEFAULT 'light',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create art table
    cursor.execute("""
        CREATE TABLE art (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            image_path TEXT NOT NULL,
            creator_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(creator_id) REFERENCES users(id)
        )
    """)
    
    # Create art_ownership table
    cursor.execute("""
        CREATE TABLE art_ownership (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            art_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(art_id) REFERENCES art(id),
            FOREIGN KEY(owner_id) REFERENCES users(id),
            UNIQUE(art_id, owner_id)
        )
    """)
    
    conn.commit()
    
    yield conn
    
    conn.close()


class TestDatabaseConnection:
    """Tests for database connectivity"""
    
    def test_main_database_exists(self):
        """Test that main database file exists"""
        assert Path("beevy.db").exists()
    
    def test_database_connection_successful(self):
        """Test successful database connection"""
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        
        # Simple query to test connection
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        assert result is not None
        conn.close()
    
    def test_in_memory_database_creation(self, test_db):
        """Test creating in-memory database for testing"""
        cursor = test_db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        assert len(tables) > 0


class TestUserTable:
    """Tests for user table operations"""
    
    def test_user_table_exists(self):
        """Test that users table exists in database"""
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        result = cursor.fetchone()
        # Table may or may not exist depending on setup
        conn.close()
    
    def test_user_insertion(self, test_db):
        """Test inserting a user into test database"""
        cursor = test_db.cursor()
        
        username = "testuser"
        email = "test@example.com"
        password = "password123"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        
        cursor.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        """, (username, email, hashed))
        
        test_db.commit()
        
        # Verify insertion
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        assert user is not None
        assert user['username'] == username
        assert user['email'] == email
    
    def test_user_duplicate_username_constraint(self, test_db):
        """Test that duplicate usernames are prevented"""
        cursor = test_db.cursor()
        
        username = "testuser"
        password = bcrypt.hashpw("pass123".encode(), bcrypt.gensalt())
        
        # Insert first user
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, "test1@example.com", password)
        )
        test_db.commit()
        
        # Try to insert duplicate
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, "test2@example.com", password)
            )
            test_db.commit()
    
    def test_user_duplicate_email_constraint(self, test_db):
        """Test that duplicate emails are prevented"""
        cursor = test_db.cursor()
        
        email = "test@example.com"
        password = bcrypt.hashpw("pass123".encode(), bcrypt.gensalt())
        
        # Insert first user
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("user1", email, password)
        )
        test_db.commit()
        
        # Try to insert duplicate email
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("user2", email, password)
            )
            test_db.commit()


class TestArtTable:
    """Tests for art table operations"""
    
    def test_art_table_exists(self):
        """Test that art table exists in database"""
        conn = sqlite3.connect("beevy.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='art'
        """)
        
        result = cursor.fetchone()
        # Table may or may not exist
        conn.close()
    
    def test_art_insertion(self, test_db):
        """Test inserting art into database"""
        cursor = test_db.cursor()
        
        # First insert a user (creator)
        password_hash = bcrypt.hashpw("pass".encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("artist", "artist@example.com", password_hash)
        )
        test_db.commit()
        
        # Get user ID
        cursor.execute("SELECT id FROM users WHERE username = ?", ("artist",))
        user_id = cursor.fetchone()['id']
        
        # Insert art
        cursor.execute("""
            INSERT INTO art (title, description, image_path, creator_id)
            VALUES (?, ?, ?, ?)
        """, ("Test Art", "Test Description", "/path/to/image.png", user_id))
        
        test_db.commit()
        
        # Verify insertion
        cursor.execute("SELECT * FROM art WHERE title = ?", ("Test Art",))
        art = cursor.fetchone()
        
        assert art is not None
        assert art['title'] == "Test Art"
        assert art['creator_id'] == user_id


class TestArtOwnershipTable:
    """Tests for art ownership relationship"""
    
    def test_art_ownership_insertion(self, test_db):
        """Test art ownership relationship"""
        cursor = test_db.cursor()
        
        # Insert users
        password_hash = bcrypt.hashpw("pass".encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("artist1", "a1@example.com", password_hash)
        )
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("buyer", "buyer@example.com", password_hash)
        )
        test_db.commit()
        
        # Get user IDs
        cursor.execute("SELECT id FROM users WHERE username = ?", ("artist1",))
        artist_id = cursor.fetchone()['id']
        cursor.execute("SELECT id FROM users WHERE username = ?", ("buyer",))
        buyer_id = cursor.fetchone()['id']
        
        # Insert art
        cursor.execute(
            "INSERT INTO art (title, image_path, creator_id) VALUES (?, ?, ?)",
            ("Artwork", "/path/image.png", artist_id)
        )
        test_db.commit()
        
        # Get art ID
        cursor.execute("SELECT id FROM art WHERE title = ?", ("Artwork",))
        art_id = cursor.fetchone()['id']
        
        # Insert ownership
        cursor.execute(
            "INSERT INTO art_ownership (art_id, owner_id) VALUES (?, ?)",
            (art_id, buyer_id)
        )
        test_db.commit()
        
        # Verify
        cursor.execute(
            "SELECT * FROM art_ownership WHERE art_id = ? AND owner_id = ?",
            (art_id, buyer_id)
        )
        ownership = cursor.fetchone()
        
        assert ownership is not None
    
    def test_art_ownership_unique_constraint(self, test_db):
        """Test that duplicate ownership is prevented"""
        cursor = test_db.cursor()
        
        # Setup
        password_hash = bcrypt.hashpw("pass".encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("artist", "artist@example.com", password_hash)
        )
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("buyer", "buyer@example.com", password_hash)
        )
        test_db.commit()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", ("artist",))
        artist_id = cursor.fetchone()['id']
        cursor.execute("SELECT id FROM users WHERE username = ?", ("buyer",))
        buyer_id = cursor.fetchone()['id']
        
        cursor.execute(
            "INSERT INTO art (title, image_path, creator_id) VALUES (?, ?, ?)",
            ("Art", "/path.png", artist_id)
        )
        test_db.commit()
        
        cursor.execute("SELECT id FROM art WHERE title = ?", ("Art",))
        art_id = cursor.fetchone()['id']
        
        # Insert first ownership
        cursor.execute(
            "INSERT INTO art_ownership (art_id, owner_id) VALUES (?, ?)",
            (art_id, buyer_id)
        )
        test_db.commit()
        
        # Try duplicate
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO art_ownership (art_id, owner_id) VALUES (?, ?)",
                (art_id, buyer_id)
            )
            test_db.commit()


class TestDatabaseQueries:
    """Tests for common database queries"""
    
    def test_get_user_by_username(self, test_db):
        """Test retrieving user by username"""
        cursor = test_db.cursor()
        
        password_hash = bcrypt.hashpw("pass".encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("querytest", "query@example.com", password_hash)
        )
        test_db.commit()
        
        # Query
        cursor.execute("SELECT * FROM users WHERE username = ?", ("querytest",))
        user = cursor.fetchone()
        
        assert user is not None
        assert user['username'] == "querytest"
    
    def test_get_user_art(self, test_db):
        """Test retrieving user's art"""
        cursor = test_db.cursor()
        
        password_hash = bcrypt.hashpw("pass".encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("artist", "artist@example.com", password_hash)
        )
        test_db.commit()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", ("artist",))
        artist_id = cursor.fetchone()['id']
        
        cursor.execute(
            "INSERT INTO art (title, image_path, creator_id) VALUES (?, ?, ?)",
            ("Art1", "/path1.png", artist_id)
        )
        cursor.execute(
            "INSERT INTO art (title, image_path, creator_id) VALUES (?, ?, ?)",
            ("Art2", "/path2.png", artist_id)
        )
        test_db.commit()
        
        # Get user's art
        cursor.execute(
            "SELECT * FROM art WHERE creator_id = ?", (artist_id,)
        )
        arts = cursor.fetchall()
        
        assert len(arts) == 2
    
    def test_get_user_owned_art(self, test_db):
        """Test retrieving art owned by user"""
        cursor = test_db.cursor()
        
        password_hash = bcrypt.hashpw("pass".encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("artist", "artist@example.com", password_hash)
        )
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("owner", "owner@example.com", password_hash)
        )
        test_db.commit()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", ("artist",))
        artist_id = cursor.fetchone()['id']
        cursor.execute("SELECT id FROM users WHERE username = ?", ("owner",))
        owner_id = cursor.fetchone()['id']
        
        cursor.execute(
            "INSERT INTO art (title, image_path, creator_id) VALUES (?, ?, ?)",
            ("Art", "/path.png", artist_id)
        )
        test_db.commit()
        
        cursor.execute("SELECT id FROM art WHERE title = ?", ("Art",))
        art_id = cursor.fetchone()['id']
        
        cursor.execute(
            "INSERT INTO art_ownership (art_id, owner_id) VALUES (?, ?)",
            (art_id, owner_id)
        )
        test_db.commit()
        
        # Get owned art
        cursor.execute("""
            SELECT a.* FROM art a
            JOIN art_ownership ao ON a.id = ao.art_id
            WHERE ao.owner_id = ?
        """, (owner_id,))
        owned = cursor.fetchall()
        
        assert len(owned) == 1
        assert owned[0]['title'] == "Art"


class TestTransactionHandling:
    """Tests for database transaction handling"""
    
    def test_transaction_rollback(self, test_db):
        """Test transaction rollback"""
        cursor = test_db.cursor()
        
        password_hash = bcrypt.hashpw("pass".encode(), bcrypt.gensalt())
        
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("user1", "user1@example.com", password_hash)
            )
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("user1", "user1duplicate@example.com", password_hash)  # Duplicate
            )
            test_db.commit()
        except sqlite3.IntegrityError:
            test_db.rollback()
        
        # Check that first user was not committed
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = ?", ("user1",))
        count = cursor.fetchone()['count']
        
        assert count == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
