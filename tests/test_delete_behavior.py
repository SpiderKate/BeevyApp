import sqlite3
import os
import shutil
import bcrypt
from app import app, process_uploaded_image
from io import BytesIO
from PIL import Image


def make_filelike(tmp_path, name='test.png'):
    p = tmp_path / 'src.png'
    img = Image.new('RGBA', (60, 40), (200, 100, 50, 255))
    img.save(p, format='PNG')
    b = p.read_bytes()
    bio = BytesIO(b)
    bio.seek(0)
    bio.filename = name
    return bio


def test_author_delete_creates_owner_copies(tmp_path, monkeypatch):
    # Setup: ensure fresh DB (this test modifies the real beevy.db in the workspace)
    conn = sqlite3.connect('beevy.db')
    cursor = conn.cursor()

    # Create users
    pw = bcrypt.hashpw(b'pass123', bcrypt.gensalt()).decode('utf-8')
    cursor.execute("INSERT INTO users (username, password) VALUES (?,?)", ('author_del', pw))
    author_id = cursor.lastrowid
    cursor.execute("INSERT INTO users (username, password) VALUES (?,?)", ('buyer_del', pw))
    buyer_id = cursor.lastrowid

    # Create a test image via process_uploaded_image
    fileobj = make_filelike(tmp_path)
    wm_rel, orig_rel = process_uploaded_image(fileobj, 'author_del', prefix='delete_test', save_original=True, author_name='Author Del - author_del')

    # Insert art referencing test files
    cursor.execute("INSERT INTO art (author_name, title, description, tat, price, type, thumbnail_path, preview_path, original_path, examples_path, slots, author_id, is_active) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   ('Author Del', 'Del Test', 'desc', 1, 10, 'png', wm_rel, wm_rel, orig_rel, '', 0, author_id, 1))
    art_id = cursor.lastrowid

    # Give buyer ownership
    cursor.execute("INSERT INTO art_ownership (art_id, owner_id, acquired_at) VALUES (?,?,datetime('now'))", (art_id, buyer_id))
    conn.commit()
    conn.close()

    # Login as author and post delete
    with app.test_client() as client:
        rv = client.post('/login', data={'username': 'author_del', 'password': 'pass123'}, follow_redirects=True)
        assert b"Succesfully logged in" in rv.data

        rv2 = client.post(f'/author_del/{art_id}/edit', data={'confirmDelete': 'DELETE', 'password': 'pass123'}, follow_redirects=True)
        assert b"owner copies preserved" in rv2.data.lower() or b"deleted from shop" in rv2.data.lower()

    # Check DB: ownership should have source set and file exists
    conn = sqlite3.connect('beevy.db')
    cursor = conn.cursor()
    cursor.execute("SELECT source FROM art_ownership WHERE art_id = ?", (art_id,))
    rows = cursor.fetchall()
    assert rows and rows[0][0], "Owner source should be set"
    rel = rows[0][0]
    full = os.path.join(os.getcwd(), 'static', rel.replace('/', os.sep))
    assert os.path.exists(full), "Owner copy should exist on disk"

    # Buyer should be able to view minimal owner page and see 'By ####' and download link
    with app.test_client() as client:
        rv = client.post('/login', data={'username': 'buyer_del', 'password': 'pass123'}, follow_redirects=True)
        assert b"Succesfully logged in" in rv.data
        rv2 = client.get(f'/shop/{art_id}')
        assert b"By ####" in rv2.data or b"by ####" in rv2.data.lower()
        assert f"/download/{art_id}".encode() in rv2.data
        assert b"Buy for" not in rv2.data, "Buy button should not appear on owner-only page"

    # Cleanup created files and DB rows
    try:
        # remove the created owner copy
        os.remove(full)
        # remove original files if still present
        wm_full = os.path.join(os.getcwd(), 'static', wm_rel.replace('/', os.sep))
        orig_full = os.path.join(os.getcwd(), 'static', orig_rel.replace('/', os.sep))
        for p in (wm_full, orig_full):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
    except Exception:
        pass

    conn.execute("DELETE FROM art_ownership WHERE art_id = ?", (art_id,))
    conn.execute("DELETE FROM art WHERE id = ?", (art_id,))
    conn.execute("DELETE FROM users WHERE id IN (?,?)", (author_id, buyer_id))
    conn.commit()
    conn.close()