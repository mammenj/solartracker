"""Unit tests for the auth database layer (auth/db.py)."""

import sqlite3
import time

import pytest

from auth import db as authdb


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def test_hash_password_is_not_plaintext_and_verifies():
    hashed = authdb.hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert authdb.verify_password("s3cret-password", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = authdb.hash_password("s3cret-password")
    assert authdb.verify_password("wrong-password", hashed) is False


def test_verify_password_handles_invalid_hash():
    assert authdb.verify_password("anything", "not-a-bcrypt-hash") is False


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def test_session_roundtrip():
    token = authdb.create_session(42)
    assert authdb.verify_session(token) == 42


@pytest.mark.parametrize("bad", ["", "garbage", "1:2", "abc:def:ghi", "1:2:3:4"])
def test_verify_session_rejects_malformed_tokens(bad):
    assert authdb.verify_session(bad) is None


def test_verify_session_rejects_tampered_signature():
    token = authdb.create_session(7)
    user_id, timestamp, signature = token.rsplit(":", 2)
    tampered = f"{user_id}:{timestamp}:{'0' * len(signature)}"
    assert authdb.verify_session(tampered) is None


def test_verify_session_rejects_expired_token():
    payload = f"7:{int(time.time()) - 25 * 3600}"
    token = f"{payload}:{authdb._sign(payload)}"
    assert authdb.verify_session(token) is None


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------
def test_create_and_fetch_user():
    uid = authdb.create_user("alice", "password123", "Alice", "user", "alice.db", "approved")

    user = authdb.get_user("alice")
    assert user["id"] == uid
    assert user["username"] == "alice"
    assert user["full_name"] == "Alice"
    assert user["role"] == "user"
    assert user["status"] == "approved"
    assert user["db_file"] == "alice.db"
    assert authdb.get_user_by_id(uid)["username"] == "alice"


def test_get_missing_user_returns_none():
    assert authdb.get_user("nobody") is None
    assert authdb.get_user_by_id(9999) is None


def test_created_password_is_hashed():
    authdb.create_user("carol", "password123", "Carol", "user", "carol.db")
    assert authdb.get_user("carol")["password_hash"] != "password123"


def test_default_status_is_pending():
    authdb.create_user("dave", "password123", "Dave", "user", "dave.db")
    assert authdb.get_user("dave")["status"] == "pending"


@pytest.mark.parametrize("role", ["superuser", "", "ADMIN"])
def test_create_user_rejects_invalid_role(role):
    with pytest.raises(ValueError):
        authdb.create_user("bob", "password123", "Bob", role, "bob.db")


def test_create_user_rejects_invalid_status():
    with pytest.raises(ValueError):
        authdb.create_user("bob", "password123", "Bob", "user", "bob.db", "nope")


def test_duplicate_username_is_rejected():
    authdb.create_user("dup", "password123", "Dup", "user", "dup.db")
    with pytest.raises(sqlite3.IntegrityError):
        authdb.create_user("dup", "password123", "Dup Again", "user", "dup2.db")


def test_update_user_fields():
    uid = authdb.create_user("erin", "password123", "Erin", "user", "erin.db", "approved")
    assert authdb.update_user(uid, full_name="Erin Updated", status="disabled") is True

    user = authdb.get_user_by_id(uid)
    assert user["full_name"] == "Erin Updated"
    assert user["status"] == "disabled"


def test_update_user_ignores_unknown_fields():
    uid = authdb.create_user("frank", "password123", "Frank", "user", "frank.db")
    assert authdb.update_user(uid, username="hacked") is False
    assert authdb.get_user_by_id(uid)["username"] == "frank"


def test_update_missing_user_returns_false():
    assert authdb.update_user(4242, full_name="Ghost") is False


def test_delete_user():
    uid = authdb.create_user("gina", "password123", "Gina", "user", "gina.db")
    assert authdb.delete_user(uid) is True
    assert authdb.get_user_by_id(uid) is None
    assert authdb.delete_user(uid) is False


def test_count_users():
    assert authdb.count_users() == 0
    authdb.create_user("a", "password123", "A", "user", "a.db")
    authdb.create_user("b", "password123", "B", "admin", "", "approved")
    assert authdb.count_users() == 2


# ---------------------------------------------------------------------------
# Listing / paging / sorting
# ---------------------------------------------------------------------------
def _seed(n: int) -> None:
    for i in range(n):
        authdb.create_user(f"user{i:02d}", "password123", f"User {i}", "user", f"u{i}.db", "approved")


def test_list_users_pages_and_reports_total():
    _seed(12)
    page1, total = authdb.list_users(page=1, page_size=10, sort="username", order="asc")
    assert total == 12
    assert len(page1) == 10
    assert page1[0]["username"] == "user00"

    page2, _ = authdb.list_users(page=2, page_size=10, sort="username", order="asc")
    assert [u["username"] for u in page2] == ["user10", "user11"]


def test_list_users_descending():
    _seed(3)
    users, _ = authdb.list_users(sort="username", order="desc")
    assert [u["username"] for u in users] == ["user02", "user01", "user00"]


def test_list_users_ignores_injection_in_sort_and_order():
    _seed(2)
    users, total = authdb.list_users(sort="username; DROP TABLE users--", order="weird")
    assert total == 2
    assert len(users) == 2
    assert authdb.count_users() == 2  # table still intact


# ---------------------------------------------------------------------------
# Per-user database provisioning
# ---------------------------------------------------------------------------
def test_ensure_user_db_creates_schema():
    path = authdb.ensure_user_db("newuser.db")
    assert path.exists()
    with sqlite3.connect(path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "meter_records" in tables


def test_ensure_user_db_is_idempotent():
    first = authdb.ensure_user_db("twice.db")
    second = authdb.ensure_user_db("twice.db")
    assert first == second


def test_ensure_user_db_resolves_relative_to_data_dir(test_config):
    path = authdb.ensure_user_db("relative.db")
    assert path.parent == test_config.data_dir


def test_ensure_user_db_with_empty_db_file_falls_back_to_default(test_config):
    """A user without a DB file gets the default DB - inside the data dir."""
    path = authdb.ensure_user_db("")
    assert path == test_config.data_dir / test_config.db_file.name
    assert path.exists()


def test_ensure_user_db_with_blank_db_file_falls_back_to_default(test_config):
    assert authdb.ensure_user_db("   ") == test_config.data_dir / test_config.db_file.name


def test_ensure_user_db_never_creates_a_db_outside_the_data_dir(test_config):
    """Regression: the default DB used to land in the project root."""
    for db_file in ("", "   ", "someone.db", "./someone.db"):
        path = authdb.ensure_user_db(db_file)
        assert path.parent == test_config.data_dir, db_file


# ---------------------------------------------------------------------------
# Legacy schema migration
# ---------------------------------------------------------------------------
LEGACY_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'disabled')) DEFAULT 'pending',
    db_file TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
"""


def test_init_auth_db_drops_legacy_role_check_and_preserves_rows(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy_auth.db"
    with sqlite3.connect(legacy) as conn:
        conn.executescript(LEGACY_SCHEMA)
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, status, db_file) "
            "VALUES ('legacy', 'hash', 'Legacy Admin', 'admin', 'approved', 'legacy.db')"
        )

    monkeypatch.setattr(authdb, "AUTH_DB", legacy)
    authdb.init_auth_db()

    with sqlite3.connect(legacy) as conn:
        table_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()[0]
        assert "CHECK (role IN" not in table_sql

        # Existing row survived the rebuild.
        assert conn.execute(
            "SELECT username, role, status FROM users WHERE username = 'legacy'"
        ).fetchone() == ("legacy", "admin", "approved")

        # The rebuilt table accepts roles that are not admin/user.
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, status, db_file) "
            "VALUES ('custom', 'hash', 'Custom Role', 'viewer', 'approved', 'custom.db')"
        )
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2

        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'users'"
            )
        }
    assert {"idx_users_username", "idx_users_status"} <= indexes


def test_init_auth_db_is_idempotent_after_migration(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy_auth.db"
    with sqlite3.connect(legacy) as conn:
        conn.executescript(LEGACY_SCHEMA)

    monkeypatch.setattr(authdb, "AUTH_DB", legacy)
    authdb.init_auth_db()
    authdb.init_auth_db()  # second run must be a no-op

    with sqlite3.connect(legacy) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
