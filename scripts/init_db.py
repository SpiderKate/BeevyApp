import sqlite3
from pathlib import Path
import shutil

DB_PRIMARY_PATH = Path("/var/data/beevy.db")
DB_FALLBACK_PATH = Path("beevy.db")


def ensure_db_link(target: Path) -> None:
    local_db = Path("beevy.db")

    if local_db.exists() and local_db.is_symlink():
        return

    if not target.parent.exists():
        return

    if local_db.exists() and not local_db.is_symlink():
        if not target.exists():
            shutil.copy2(local_db, target)
        local_db.unlink()

    if not local_db.exists():
        local_db.symlink_to(target)


def create_schema(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
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

        CREATE TABLE IF NOT EXISTS art (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_name TEXT NOT NULL,
            title TEXT NOT NULL,
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

        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_ID INT NOT NULL,
            name TEXT NOT NULL,
            password TEXT,
            is_public BOOLEAN NOT NULL,
            user_id INT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS art_ownership (
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

        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            language TEXT NOT NULL DEFAULT 'en',
            theme TEXT NOT NULL DEFAULT 'bee',
            default_brush_size INTEGER DEFAULT 30,
            notifications BOOLEAN DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )

    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    for user_id in user_ids:
        cursor.execute("SELECT 1 FROM preferences WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO preferences (user_id, language, theme, default_brush_size, notifications)
                VALUES (?, 'en', 'bee', 30, 1)
                """,
                (user_id,),
            )

    conn.commit()
    conn.close()


def main() -> None:
    db_path = DB_PRIMARY_PATH if DB_PRIMARY_PATH.parent.exists() else DB_FALLBACK_PATH
    ensure_db_link(DB_PRIMARY_PATH)
    create_schema(db_path)
    print(f"Database ready at: {db_path}")


if __name__ == "__main__":
    main()
