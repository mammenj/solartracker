"""Authentication and user management module."""

import bcrypt
import hmac
import json
import sqlite3
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import load_config

config = load_config()
AUTH_DB = Path(config.auth_db_file)
DATA_DIR = Path(config.data_dir)
SECRET = config.auth_secret.encode()

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return bcrypt hash of password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Session management (signed cookie)
# ---------------------------------------------------------------------------

def _sign(data: str) -> str:
    return hmac.new(SECRET, data.encode(), "sha256").hexdigest()


def create_session(user_id: int) -> str:
    """Create a signed session token."""
    payload = f"{user_id}:{int(time.time())}"
    sig = _sign(payload)
    return f"{payload}:{sig}"


def verify_session(token: str) -> Optional[int]:
    """Verify session token, return user_id if valid and not expired (24h)."""
    try:
        user_id_str, ts_str, sig = token.rsplit(":", 2)
        payload = f"{user_id_str}:{ts_str}"
        if not hmac.compare_digest(_sign(payload), sig):
            return None
        if time.time() - int(ts_str) > 24 * 3600:
            return None
        return int(user_id_str)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Auth database schema & initialization
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
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


def init_auth_db() -> None:
    """Create auth database and schema if not exists."""
    AUTH_DB.parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(AUTH_DB)) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def _row_to_user(row: tuple) -> dict:
    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
        "full_name": row[3],
        "role": row[4],
        "status": row[5],
        "db_file": row[6],
        "created_at": row[7],
        "updated_at": row[8],
    }


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

def create_user(username: str, password: str, full_name: str, role: str, db_file: str, status: str = "pending") -> int:
    """Create a new user, return user_id."""
    if role not in ("admin", "user"):
        raise ValueError("role must be 'admin' or 'user'")
    if status not in ("pending", "approved", "disabled"):
        raise ValueError("status must be 'pending', 'approved', or 'disabled'")
    pw_hash = hash_password(password)
    now = datetime.now().isoformat()
    with closing(sqlite3.connect(AUTH_DB)) as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, status, db_file, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (username, pw_hash, full_name, role, status, db_file, now, now),
        )
        conn.commit()
        return cursor.lastrowid


def get_user(username: str) -> Optional[dict]:
    """Get user by username."""
    with closing(sqlite3.connect(AUTH_DB)) as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, full_name, role, status, db_file, created_at, updated_at "
            "FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    with closing(sqlite3.connect(AUTH_DB)) as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, full_name, role, status, db_file, created_at, updated_at "
            "FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return _row_to_user(row) if row else None


def list_users(page: int = 1, page_size: int = 10, sort: str = "username", order: str = "asc") -> tuple[list[dict], int]:
    """List users with paging and sorting."""
    allowed_sorts = {"username", "full_name", "role", "status", "created_at"}
    sort = sort if sort in allowed_sorts else "username"
    order = order.upper() if order in ("asc", "desc") else "ASC"
    page = max(1, page)
    page_size = max(1, page_size)
    offset = (page - 1) * page_size

    with closing(sqlite3.connect(AUTH_DB)) as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        rows = conn.execute(
            f"SELECT id, username, password_hash, full_name, role, status, db_file, created_at, updated_at "
            f"FROM users ORDER BY {sort} {order} LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()

    return [_row_to_user(r) for r in rows], total


def update_user(user_id: int, **fields) -> bool:
    """Update user fields (full_name, role, status, db_file)."""
    allowed = {"full_name", "role", "status", "db_file"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    with closing(sqlite3.connect(AUTH_DB)) as conn:
        cursor = conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return cursor.rowcount > 0


def delete_user(user_id: int) -> bool:
    """Delete a user (admin only, use with caution)."""
    with closing(sqlite3.connect(AUTH_DB)) as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def count_users() -> int:
    with closing(sqlite3.connect(AUTH_DB)) as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


# ---------------------------------------------------------------------------
# User database provisioning
# ---------------------------------------------------------------------------

def provision_user_db(db_path: Path) -> None:
    """Create the meter_records schema in a user's database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meter_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                import REAL NOT NULL,
                export REAL NOT NULL,
                solar_gen REAL NOT NULL,
                addedon TEXT NOT NULL
            )
        """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON meter_records(date)")
        conn.commit()


def ensure_user_db(db_file: str) -> Path:
    """Return resolved Path for a user's DB, creating if needed."""
    p = Path(db_file)
    if not p.is_absolute():
        p = DATA_DIR / p
    provision_user_db(p)
    return p