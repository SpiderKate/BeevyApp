import sqlite3
conn = sqlite3.connect('beevy.db')
cursor = conn.cursor()

#cursor.execute("PRAGMA foreign_keys = ON;")
#cursor.execute("PRAGMA foreign_keys;")
#print(cursor.fetchone())


#cursor.execute("CREATE table users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, surname TEXT, username CHECK (length(username) <= 30) NOT NULL, email TEXT NOT NULL, password CHECK (length(password) <= 100) NOT NULL, dob TEXT NOT NULL, bio CHECK (length(bio) <= 300), avatar_path TEXT, social_links TEXT, language TEXT NOT NULL DEFAULT en, theme TEXT NOT NULL DEFAULT bee, default_brush_size INTEGER DEFAULT 30, notifications BOOLEAN, last_login_at TEXT, bee_points INTEGER DEFAULT 5000, deleted INTEGER DEFAULT 0, deleted_at TEXT, recovery_username TEXT);")
#cursor.execute("CREATE table art (id INTEGER PRIMARY KEY AUTOINCREMENT, author_name TEXT NOT NULL, title CHECK (length(title) <= 100) NOT NULL, description CHECK (length(description) <= 300),tat INT NOT NULL, price INT NOT NULL, type TEXT NOT NULL, thumbnail_path TEXT NOT NULL, preview_path TEXT, original_path TEXT, examples_path TEXT, slots INT, author_id INT, is_active BOOLEAN NOT NULL DEFAULT 1, FOREIGN KEY(author_id) REFERENCES users(id));")
#cursor.execute("CREATE table rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, room_ID INT NOT NULL, name TEXT NOT NULL, password CHECK (length(password) <= 100), is_public BOOLEAN NOT NULL, user_id INT NOT NULL, is_active BOOLEAN DEFAULT 1, FOREIGN KEY(user_id) REFERENCES users(id));")
#cursor.execute("CREATE table art_ownership (id INTEGER PRIMARY KEY AUTOINCREMENT, art_id INTEGER NOT NULL, owner_id INTEGER NOT NULL, acquired_at TEXT NOT NULL, source TEXT, is_exclusive BOOLEAN, can_download BOOLEAN DEFAULT 1, license_type TEXT DEFAULT 'personal', FOREIGN KEY(art_id) REFERENCES art(id), FOREIGN KEY(owner_id) REFERENCES users(id));")

#cursor.execute("ALTER TABLE users ADD COLUMN recovery_username TEXT;")

#cursor.execute("DROP table users;")
#cursor.execute("DROP table art;")
#cursor.execute("DROP table rooms;")
#cursor.execute("DROP table art_ownership;")

#cursor.execute("DELETE FROM art;")
#cursor.execute("DELETE FROM users WHERE id=13;")
#cursor.execute("DELETE FROM rooms;")
#cursor.execute("DELETE FROM art_ownership;")

conn.commit()
conn.close()