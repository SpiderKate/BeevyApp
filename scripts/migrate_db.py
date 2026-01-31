"""Migration helper: export data from current beevy.db, create a new DB with schema
from setup_db.py, migrate rows while moving inlined preference columns from users
into a new `preferences` table, verify row counts and swap DBs with a backup.

Run with: .venv\Scripts\python.exe scripts/migrate_db.py
"""
import sqlite3
import os
import shutil
from datetime import datetime

OLD_DB = 'beevy.db'
NEW_DB = 'beevy_new.db'
BACKUP_FMT = 'beevy.db.bak.{ts}'

# SQL schema derived from setup_db.py (keeps same constraint semantics)
CREATE_USERS = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    surname TEXT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    dob TEXT NOT NULL,
    bio TEXT,
    avatar_path TEXT,
    social_links TEXT,
    last_login_at TEXT,
    bee_points INTEGER DEFAULT 5000,
    deleted INTEGER DEFAULT 0,
    deleted_at TEXT,
    recovery_username TEXT
);
"""

CREATE_ART = """
CREATE TABLE art (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_name TEXT NOT NULL,
    title NOT NULL,
    description TEXT,
    tat INT NOT NULL,
    price INT NOT NULL,
    type TEXT NOT NULL,
    thumbnail_path TEXT NOT NULL,
    preview_path TEXT,
    original_path TEXT,
    examples_path TEXT,
    slots INT,
    author_id INT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY(author_id) REFERENCES users(id)
);
"""

CREATE_ROOMS = """
CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_ID INT NOT NULL,
    name TEXT NOT NULL,
    password TEXT,
    is_public BOOLEAN NOT NULL,
    user_id INT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""

CREATE_OWNERSHIP = """
CREATE TABLE art_ownership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    art_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    acquired_at TEXT NOT NULL,
    source TEXT,
    is_exclusive BOOLEAN,
    can_download BOOLEAN DEFAULT 1,
    license_type TEXT DEFAULT 'personal',
    FOREIGN KEY(art_id) REFERENCES art(id),
    FOREIGN KEY(owner_id) REFERENCES users(id)
);
"""

CREATE_PREFERENCES = """
CREATE TABLE preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    theme TEXT NOT NULL DEFAULT 'bee',
    default_brush_size INTEGER DEFAULT 30,
    notifications BOOLEAN DEFAULT 1,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""

def fetch_all_rows(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [c[1] for c in cur.fetchall()]
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    return cols, rows


def migrate():
    if not os.path.exists(OLD_DB):
        print(f"{OLD_DB} not found in repo root. Aborting.")
        return 1

    # Connect old DB
    old = sqlite3.connect(OLD_DB)

    # Read old data
    print("Exporting data from old DB...")
    users_cols, users_rows = fetch_all_rows(old, 'users')
    art_cols, art_rows = fetch_all_rows(old, 'art')
    rooms_cols, rooms_rows = fetch_all_rows(old, 'rooms')
    own_cols, own_rows = fetch_all_rows(old, 'art_ownership')

    # Map of column positions for users preference columns (if present)
    ucol_index = {c: i for i, c in enumerate(users_cols)}
    has_pref_cols = all(k in ucol_index for k in ('language', 'theme', 'default_brush_size', 'notifications'))

    # Create new DB
    if os.path.exists(NEW_DB):
        os.remove(NEW_DB)
    new = sqlite3.connect(NEW_DB)
    cur = new.cursor()

    print("Creating schema in new DB...")
    cur.executescript('\n'.join([CREATE_USERS, CREATE_PREFERENCES, CREATE_ART, CREATE_ROOMS, CREATE_OWNERSHIP]))
    new.commit()

    # Insert users -> preferences
    print(f"Migrating {len(users_rows)} users and preferences (if present)...")
    for row in users_rows:
        # build user tuple matching new users table order
        # users table fields: id, name, surname, username, email, password, dob, bio, avatar_path, social_links, last_login_at, bee_points, deleted, deleted_at, recovery_username
        id_ = row[ucol_index['id']]
        name = row[ucol_index.get('name')]
        surname = row[ucol_index.get('surname')]
        username = row[ucol_index.get('username')]
        email = row[ucol_index.get('email')]
        password = row[ucol_index.get('password')]
        dob = row[ucol_index.get('dob')]
        bio = row[ucol_index.get('bio')]
        avatar_path = row[ucol_index.get('avatar_path')]
        social_links = row[ucol_index.get('social_links')]
        last_login_at = row[ucol_index.get('last_login_at')]
        bee_points = row[ucol_index.get('bee_points')]
        deleted = row[ucol_index.get('deleted')]
        deleted_at = row[ucol_index.get('deleted_at')]
        recovery_username = row[ucol_index.get('recovery_username')]

        cur.execute(
            "INSERT INTO users (id, name, surname, username, email, password, dob, bio, avatar_path, social_links, last_login_at, bee_points, deleted, deleted_at, recovery_username) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (id_, name, surname, username, email, password, dob, bio, avatar_path, social_links, last_login_at, bee_points, deleted, deleted_at, recovery_username)
        )

        # preferences
        if has_pref_cols:
            language = row[ucol_index.get('language')] or 'en'
            theme = row[ucol_index.get('theme')] or 'bee'
            default_brush_size = row[ucol_index.get('default_brush_size')] or 30
            notifications = row[ucol_index.get('notifications')]
            # null -> default
            cur.execute(
                "INSERT INTO preferences (user_id, language, theme, default_brush_size, notifications) VALUES (?,?,?,?,?)",
                (id_, language, theme, default_brush_size, notifications)
            )

    new.commit()

    # Insert other tables preserving ids
    print(f"Migrating {len(art_rows)} art rows...")
    if art_rows:
        art_cols_names = art_cols
        for row in art_rows:
            # construct insert with explicit columns to preserve ids
            placeholders = ','.join('?' for _ in art_cols_names)
            cols_sql = ','.join(art_cols_names)
            cur.execute(f"INSERT INTO art ({cols_sql}) VALUES ({placeholders})", row)
    new.commit()

    print(f"Migrating {len(rooms_rows)} rooms rows...")
    if rooms_rows:
        cols_sql = ','.join(rooms_cols)
        placeholders = ','.join('?' for _ in rooms_cols)
        for row in rooms_rows:
            cur.execute(f"INSERT INTO rooms ({cols_sql}) VALUES ({placeholders})", row)
    new.commit()

    print(f"Migrating {len(own_rows)} ownership rows...")
    if own_rows:
        cols_sql = ','.join(own_cols)
        placeholders = ','.join('?' for _ in own_cols)
        for row in own_rows:
            cur.execute(f"INSERT INTO art_ownership ({cols_sql}) VALUES ({placeholders})", row)
    new.commit()

    # Update sqlite_sequence for AUTOINCREMENT behavior
    print("Updating sqlite_sequence to match max ids...")
    for t in ('users', 'art', 'rooms', 'art_ownership', 'preferences'):
        cur.execute(f"SELECT MAX(id) FROM {t}")
        max_id = cur.fetchone()[0] or 0
        # delete existing row and insert desired seq
        cur.execute("DELETE FROM sqlite_sequence WHERE name = ?", (t,))
        if max_id:
            cur.execute("INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (t, max_id))
    new.commit()

    # Sanity checks
    print("Running sanity checks...")
    cur.execute("SELECT COUNT(*) FROM users")
    users_new = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users",)
    art_new = cur.execute("SELECT COUNT(*) FROM art").fetchone()[0]

    print(f"Users: old={len(users_rows)} new={users_new}")
    print(f"Art: old={len(art_rows)} new={art_new}")

    # Backup old DB
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_name = BACKUP_FMT.format(ts=ts)
    print(f"Backing up {OLD_DB} -> {backup_name}")
    shutil.copy2(OLD_DB, backup_name)

    # Replace DB
    print(f"Swapping in new DB ({NEW_DB} -> {OLD_DB})")
    old.close()
    new.close()
    os.replace(NEW_DB, OLD_DB)

    # Write migration log
    migrations_dir = os.path.join(os.path.dirname(__file__), '..', 'migrations')
    os.makedirs(migrations_dir, exist_ok=True)
    log_path = os.path.join(migrations_dir, 'migration_log.txt')
    entry = (f"{datetime.now().isoformat()} - Migration completed. Backup: {backup_name}. "
             f"Users: old={len(users_rows)} new={users_new}; Art: old={len(art_rows)} new={art_new}\n")
    try:
        with open(log_path, 'a', encoding='utf-8') as fh:
            fh.write(entry)
        print(f"Wrote migration log to {log_path}")
    except Exception as e:
        print(f"Failed to write migration log: {e}")

    print("Migration complete. Please run your tests and verify app behavior. Original DB backed up.")
    return 0

if __name__ == '__main__':
    exit(migrate())
