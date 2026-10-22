"""Authentication and user management module."""

import bcrypt
import hmac
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from config import load_config

config = load_config()
AUTH_DB = Path(config.auth_db_file)
DATA_DIR = Path(config.data_dir)
SECRET = config.auth_secret.encode()

#: Paths whose meter_records schema has already been provisioned this process.
_provisioned_dbs: set[Path] = set()


@asynccontextmanager
async def _connect(path: Optional[Path] = None):
    """Yield a connection with ``Row`` rows enabled.

    Defaults to the auth database; pass ``path`` for a user database.
    Centralises the connect + ``row_factory`` setup so every query opens its
    database the same way.  The auth path is resolved at call time so tests can
    redirect it, and the connection is always closed on exit.
    """
    async with aiosqlite.connect(path if path is not None else AUTH_DB) as db:
        db.row_factory = aiosqlite.Row
        yield db

# ---------------------------------------------------------------------------
# Password hashing (sync - bcrypt is CPU-bound, keep sync)
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
# Session management (signed cookie) - sync, no DB access
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

STATUSES = ("pending", "approved", "disabled")

USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'disabled')) DEFAULT 'pending',
    db_file TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA = USERS_TABLE_SQL + """
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
"""

#: Marker present in the legacy schema that limited roles to admin/user.
_LEGACY_ROLE_CHECK = "CHECK (role IN"


async def _migrate_role_constraint(db: aiosqlite.Connection) -> None:
    """Drop the legacy ``role IN ('admin', 'user')`` CHECK constraint.

    Roles are now defined by ``auth/policy.csv``, so the database must accept
    any role name. The table is rebuilt in place; existing rows are preserved.
    """
    row = await db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
    )
    row = await row.fetchone()
    if not row or _LEGACY_ROLE_CHECK not in (row[0] or ""):
        return

    await db.execute("DROP TABLE IF EXISTS users_role_migration")
    await db.execute("ALTER TABLE users RENAME TO users_role_migration")
    # Indexes follow the renamed table, so drop them before recreating.
    await db.execute("DROP INDEX IF EXISTS idx_users_username")
    await db.execute("DROP INDEX IF EXISTS idx_users_status")
    await db.execute(USERS_TABLE_SQL)
    await db.execute(
        "INSERT INTO users "
        "(id, username, password_hash, full_name, role, status, db_file, created_at, updated_at) "
        "SELECT id, username, password_hash, full_name, role, status, db_file, created_at, updated_at "
        "FROM users_role_migration"
    )
    await db.execute("DROP TABLE users_role_migration")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")


async def init_auth_db() -> None:
    """Create auth database and schema if not exists."""
    AUTH_DB.parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with _connect() as db:
        await db.executescript(SCHEMA)
        try:
            await _migrate_role_constraint(db)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


def _row_to_user(row: aiosqlite.Row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "password_hash": row["password_hash"],
        "full_name": row["full_name"],
        "role": row["role"],
        "status": row["status"],
        "db_file": row["db_file"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------------------------
# User CRUD (async)
# ---------------------------------------------------------------------------

async def _allowed_roles() -> set[str]:
    """Roles currently defined in the authorization policy file."""
    from auth.policy import roles

    return set(roles())


async def create_user(username: str, password: str, full_name: str, role: str, db_file: str, status: str = "pending") -> int:
    """Create a new user, return user_id."""
    allowed = await _allowed_roles()
    if role not in allowed:
        raise ValueError(f"role must be one of: {', '.join(sorted(allowed))}")
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    pw_hash = hash_password(password)
    now = datetime.now().isoformat()
    async with _connect() as db:
        cursor = await db.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, status, db_file, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (username, pw_hash, full_name, role, status, db_file, now, now),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user(username: str) -> Optional[dict]:
    """Get user by username."""
    async with _connect() as db:
        row = await db.execute(
            "SELECT id, username, password_hash, full_name, role, status, db_file, created_at, updated_at "
            "FROM users WHERE username = ?",
            (username,),
        )
        row = await row.fetchone()
    return _row_to_user(row) if row else None


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    async with _connect() as db:
        row = await db.execute(
            "SELECT id, username, password_hash, full_name, role, status, db_file, created_at, updated_at "
            "FROM users WHERE id = ?",
            (user_id,),
        )
        row = await row.fetchone()
    return _row_to_user(row) if row else None


async def list_users(page: int = 1, page_size: int = 10, sort: str = "username", order: str = "asc") -> tuple[list[dict], int]:
    """List users with paging and sorting."""
    allowed_sorts = {"username", "full_name", "role", "status", "created_at"}
    sort = sort if sort in allowed_sorts else "username"
    order = order.upper() if order in ("asc", "desc") else "ASC"
    page = max(1, page)
    page_size = max(1, page_size)
    offset = (page - 1) * page_size

    async with _connect() as db:
        total_row = await db.execute("SELECT COUNT(*) FROM users")
        total = (await total_row.fetchone())[0]
        rows = await db.execute(
            f"SELECT id, username, password_hash, full_name, role, status, db_file, created_at, updated_at "
            f"FROM users ORDER BY {sort} {order} LIMIT ? OFFSET ?",
            (page_size, offset),
        )
        rows = await rows.fetchall()

    return [_row_to_user(r) for r in rows], total


async def update_user(user_id: int, **fields) -> bool:
    """Update user fields (full_name, role, status, db_file)."""
    allowed = {"full_name", "role", "status", "db_file"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    if "role" in updates and updates["role"] not in await _allowed_roles():
        raise ValueError(f"role must be one of: {', '.join(sorted(await _allowed_roles()))}")
    if "status" in updates and updates["status"] not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    async with _connect() as db:
        cursor = await db.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        await db.commit()
        return cursor.rowcount > 0


async def delete_user(user_id: int) -> bool:
    """Delete a user (admin only, use with caution)."""
    async with _connect() as db:
        cursor = await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount > 0


async def count_users() -> int:
    async with _connect() as db:
        row = await db.execute("SELECT COUNT(*) FROM users")
        row = await row.fetchone()
        return row[0]


async def count_users_by_role() -> dict[str, int]:
    """Return ``{role: user_count}`` for every role currently in use."""
    async with _connect() as db:
        rows = await db.execute(
            "SELECT role, COUNT(*) FROM users GROUP BY role"
        )
        rows = await rows.fetchall()
    return {role: count for role, count in rows}


async def count_users_with_role(role: str) -> int:
    """Number of users assigned to ``role``."""
    async with _connect() as db:
        row = await db.execute(
            "SELECT COUNT(*) FROM users WHERE role = ?", (role,)
        )
        row = await row.fetchone()
        return row[0]


# ---------------------------------------------------------------------------
# User database provisioning
# ---------------------------------------------------------------------------

async def provision_user_db(db_path: Path) -> None:
    """Create the meter_records schema in a user's database.

    Delegates to :class:`MeterReadingStore`, which owns the readings schema and
    its process-wide "already provisioned" cache - so the DDL runs at most once
    per database regardless of whether provisioning was triggered here or by a
    store on first use.
    """
    from libsolar_sqlite import MeterReadingStore

    store = MeterReadingStore(db_path)
    try:
        await store._ensure_schema()
    finally:
        await store.aclose()



async def ensure_user_db(db_file: str) -> Path:
    """Return resolved Path for a user's DB, creating if needed.

    Users without an explicit database file (administrators do not log
    readings) fall back to the application's default database, which lives
    in the data directory - never in the project root.

    Provisioning is idempotent (``CREATE ... IF NOT EXISTS``) but not free, so
    each resolved path is only provisioned once per process.
    """
    db_file = (db_file or "").strip()
    if db_file:
        p = Path(db_file)
        if not p.is_absolute():
            p = DATA_DIR / p
    else:
        p = DATA_DIR / Path(config.db_file).name
    if p not in _provisioned_dbs:
        await provision_user_db(p)
        _provisioned_dbs.add(p)
    return p