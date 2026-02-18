"""
High-impact integration tests to improve coverage of main Flask route blocks.
These tests seed minimal valid DB data and exercise authenticated routes.
"""

import sqlite3
import uuid
from datetime import datetime

import bcrypt
import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def seeded_data():
    conn = sqlite3.connect("beevy.db")
    cursor = conn.cursor()

    author_username = f"cov_author_{uuid.uuid4().hex[:8]}"
    buyer_username = f"cov_buyer_{uuid.uuid4().hex[:8]}"
    author_email = f"{author_username}@example.com"
    buyer_email = f"{buyer_username}@example.com"

    author_password = "AuthorPass123!"
    buyer_password = "BuyerPass123!"

    author_hash = bcrypt.hashpw(author_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    buyer_hash = bcrypt.hashpw(buyer_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    cursor.execute(
        """
        INSERT INTO users (name, surname, username, email, password, dob, deleted)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        ("Cov", "Author", author_username, author_email, author_hash, "2000-01-01"),
    )
    author_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO users (name, surname, username, email, password, dob, deleted)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        ("Cov", "Buyer", buyer_username, buyer_email, buyer_hash, "2000-01-01"),
    )
    buyer_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO preferences (user_id, language, theme, default_brush_size, notifications)
        VALUES (?, ?, ?, ?, ?)
        """,
        (author_id, "en", "bee", 30, 1),
    )
    cursor.execute(
        """
        INSERT INTO preferences (user_id, language, theme, default_brush_size, notifications)
        VALUES (?, ?, ?, ?, ?)
        """,
        (buyer_id, "en", "bee", 30, 1),
    )

    public_room_id = str(uuid.uuid4())
    private_room_id = str(uuid.uuid4())
    private_room_password = "RoomPass123!"
    private_room_hash = bcrypt.hashpw(private_room_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    cursor.execute(
        """
        INSERT INTO rooms (room_ID, name, password, is_public, user_id, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (public_room_id, "Public Coverage Room", None, 1, author_id),
    )
    cursor.execute(
        """
        INSERT INTO rooms (room_ID, name, password, is_public, user_id, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (private_room_id, "Private Coverage Room", private_room_hash, 0, author_id),
    )

    cursor.execute(
        """
        INSERT INTO art (
            author_name, title, description, tat, price, type,
            thumbnail_path, preview_path, original_path, examples_path,
            slots, author_id, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            author_username,
            "Coverage Active Art",
            "desc",
            "2 days",
            15,
            "digital",
            "uploads/shop/thumbs/coverage_active.png",
            "uploads/shop/examples/coverage_active_preview.png",
            "uploads/shop/original/coverage_active_original.png",
            "",
            1,
            author_id,
            1,
        ),
    )
    active_art_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO art (
            author_name, title, description, tat, price, type,
            thumbnail_path, preview_path, original_path, examples_path,
            slots, author_id, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            author_username,
            "Coverage Inactive Art",
            "desc",
            "2 days",
            20,
            "digital",
            "uploads/shop/thumbs/coverage_inactive.png",
            "uploads/shop/examples/coverage_inactive_preview.png",
            "uploads/shop/original/coverage_inactive_original.png",
            "",
            1,
            author_id,
            0,
        ),
    )
    inactive_art_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO art_ownership (art_id, owner_id, acquired_at, source, is_exclusive, can_download, license_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            active_art_id,
            buyer_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "",
            0,
            1,
            "personal",
        ),
    )

    conn.commit()

    yield {
        "author_username": author_username,
        "buyer_username": buyer_username,
        "author_password": author_password,
        "buyer_password": buyer_password,
        "public_room_id": public_room_id,
        "private_room_id": private_room_id,
        "private_room_password": private_room_password,
        "active_art_id": active_art_id,
        "inactive_art_id": inactive_art_id,
    }

    cursor.execute("DELETE FROM art_ownership WHERE art_id IN (?, ?)", (active_art_id, inactive_art_id))
    cursor.execute("DELETE FROM art WHERE id IN (?, ?)", (active_art_id, inactive_art_id))
    cursor.execute("DELETE FROM rooms WHERE room_ID IN (?, ?)", (public_room_id, private_room_id))
    cursor.execute("DELETE FROM preferences WHERE user_id IN (?, ?)", (author_id, buyer_id))
    cursor.execute("DELETE FROM users WHERE id IN (?, ?)", (author_id, buyer_id))
    conn.commit()
    conn.close()


def set_session_user(client, username):
    with client.session_transaction() as session:
        session["username"] = username
        session["user_language"] = "en"


class TestCoverageSettingsRoutes:
    def test_settings_pages_get(self, client, seeded_data):
        username = seeded_data["buyer_username"]
        set_session_user(client, username)

        urls = [
            f"/{username}/settings",
            f"/{username}/settings/profile",
            f"/{username}/settings/preferences",
            f"/{username}/settings/account",
            f"/{username}/settings/security",
            f"/{username}/settings/logout",
            f"/{username}/settings/delete",
        ]

        for url in urls:
            response = client.get(url)
            assert response.status_code == 200

    def test_settings_pages_post(self, client, seeded_data):
        username = seeded_data["buyer_username"]
        set_session_user(client, username)

        profile_resp = client.post(
            f"/{username}/settings/profile",
            data={"username": username, "bio": "Coverage bio"},
            follow_redirects=False,
        )
        assert profile_resp.status_code == 302

        pref_resp = client.post(
            f"/{username}/settings/preferences",
            data={"language": "en", "theme": "bee", "brush": "25", "not": "on"},
            follow_redirects=False,
        )
        assert pref_resp.status_code == 302

        account_resp = client.post(
            f"/{username}/settings/account",
            data={"email": f"updated_{username}@example.com"},
            follow_redirects=False,
        )
        assert account_resp.status_code == 302

        security_fail_resp = client.post(
            f"/{username}/settings/security",
            data={
                "curPassword": "WrongPass123!",
                "newPassword": "NewStrongPass123!",
                "newPassword2": "NewStrongPass123!",
            },
            follow_redirects=False,
        )
        assert security_fail_resp.status_code == 200

        security_ok_resp = client.post(
            f"/{username}/settings/security",
            data={
                "curPassword": seeded_data["buyer_password"],
                "newPassword": "NewStrongPass123!",
                "newPassword2": "NewStrongPass123!",
            },
            follow_redirects=False,
        )
        assert security_ok_resp.status_code == 200

        delete_guard_resp = client.post(
            f"/{username}/settings/delete",
            data={"confirm": "NOPE", "password": "anything"},
            follow_redirects=False,
        )
        assert delete_guard_resp.status_code == 200


class TestCoverageDrawAndJoinRoutes:
    def test_draw_and_join_paths(self, client, seeded_data):
        username = seeded_data["buyer_username"]
        set_session_user(client, username)

        for path in ["/join", "/join/public", "/join/private", "/option", "/create"]:
            response = client.get(path)
            assert response.status_code == 200

        public_join = client.get(f"/join/{seeded_data['public_room_id']}")
        assert public_join.status_code == 302

        private_join_get = client.get(f"/join/{seeded_data['private_room_id']}")
        assert private_join_get.status_code == 200

        private_join_bad = client.post(
            f"/join/{seeded_data['private_room_id']}",
            data={"password": "bad-pass"},
        )
        assert private_join_bad.status_code == 200

        private_join_ok = client.post(
            f"/join/{seeded_data['private_room_id']}",
            data={"password": seeded_data["private_room_password"]},
            follow_redirects=False,
        )
        assert private_join_ok.status_code == 302

        draw_public = client.get(f"/draw/{seeded_data['public_room_id']}")
        assert draw_public.status_code == 200


class TestCoverageShopAndOwnedRoutes:
    def test_shop_and_owned_paths(self, client, seeded_data):
        username = seeded_data["buyer_username"]
        set_session_user(client, username)

        shop_resp = client.get("/shop")
        assert shop_resp.status_code == 200

        active_detail_resp = client.get(f"/shop/{seeded_data['active_art_id']}")
        assert active_detail_resp.status_code == 302

        owned_resp = client.get(f"/owned/{seeded_data['active_art_id']}")
        assert owned_resp.status_code == 200

        inactive_resp = client.get(f"/shop/{seeded_data['inactive_art_id']}")
        assert inactive_resp.status_code == 404

    def test_remove_ownership_path(self, client, seeded_data):
        username = seeded_data["buyer_username"]
        set_session_user(client, username)

        remove_resp = client.post(
            f"/owned/{seeded_data['active_art_id']}/remove",
            follow_redirects=False,
        )
        assert remove_resp.status_code == 302


class TestCoverageRecoverRoute:
    def test_recover_route_branches(self, client, seeded_data):
        missing_resp = client.post("/recover", data={"email": "", "password": ""})
        assert missing_resp.status_code == 200

        wrong_password_resp = client.post(
            "/recover",
            data={
                "email": f"{seeded_data['buyer_username']}@example.com",
                "password": "not-the-right-password",
                "username": seeded_data["buyer_username"],
            },
        )
        assert wrong_password_resp.status_code == 200
