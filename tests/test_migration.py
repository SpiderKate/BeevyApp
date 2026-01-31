import sqlite3


def test_preferences_for_all_users():
    conn = sqlite3.connect('beevy.db')
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM users')
    users = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM preferences')
    prefs = cur.fetchone()[0]

    conn.close()

    assert prefs == users, f"Expected preferences count == users count ({prefs} != {users})"


def test_foreign_key_integrity():
    conn = sqlite3.connect('beevy.db')
    cur = conn.cursor()

    # preferences.user_id must reference a user
    cur.execute("SELECT p.user_id FROM preferences p LEFT JOIN users u ON p.user_id = u.id WHERE u.id IS NULL")
    bad = cur.fetchall()
    assert bad == [], f"Found preferences with missing user references: {bad}"

    # art.author_id if not null must reference users
    cur.execute("SELECT DISTINCT author_id FROM art WHERE author_id IS NOT NULL AND author_id NOT IN (SELECT id FROM users)")
    bad2 = cur.fetchall()
    assert bad2 == [], f"Found art rows with missing author references: {bad2}"

    conn.close()
