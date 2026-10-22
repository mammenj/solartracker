"""Shared pytest fixtures for the Solar Tracker test suite.

The application reads its configuration, auth database and per-user data
directory through module-level globals that are bound at import time.  The
`isolate` fixture redirects all of those at a temporary directory so the test
suite never touches the real ``auth.db`` or ``data/`` files.
"""

import sys

# config.load_config() parses sys.argv with argparse, which chokes on pytest's
# own command line arguments.  Neutralise it before any app module is imported.
sys.argv = ["st"]

import importlib
import shutil
from http.cookies import SimpleCookie
from urllib.parse import urlsplit

import pytest

from config import AppConfig


# Modules that keep a module-level ``config`` object bound at import time.
CONFIG_MODULES = [
    "auth.db",
    "auth.deps",
    "auth.routes",
    "core.app",
    "dashboard.routes",
    "entry.routes",
    "entry.services",
    "admin.routes",
    "admin.services",
]


# ---------------------------------------------------------------------------
# Minimal async test client for Quart
# ---------------------------------------------------------------------------
class Response:
    """A lightweight HTTP response wrapper."""

    def __init__(self, status: int, headers: list[tuple[str, str]], body: bytes):
        self.status = status
        self.status_line = f"{status} OK"
        self.headers = headers
        self.text = body.decode("utf-8", "replace")

    @property
    def location(self) -> str | None:
        """Location header reduced to a path (+query), as browsers use it."""
        raw = self.header("Location")
        if raw is None:
            return None
        parts = urlsplit(raw)
        return parts.path + (f"?{parts.query}" if parts.query else "")

    def header(self, name: str, default=None):
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value
        return default


class Client:
    """A tiny cookie-aware test client for Quart."""

    def __init__(self, app):
        self.app = app
        self.cookies: dict[str, str] = {}
        self._client = app.test_client()

    async def get(self, path: str, headers: dict | None = None) -> Response:
        return await self.request("GET", path, headers=headers)

    async def post(self, path: str, data: dict | None = None, headers: dict | None = None) -> Response:
        return await self.request("POST", path, data=data or {}, headers=headers)

    async def request(self, method: str, path: str, data: dict | None = None, headers: dict | None = None) -> Response:
        # Build headers with cookies
        request_headers = dict(headers or {})
        if self.cookies:
            cookie_header = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
            request_headers["Cookie"] = cookie_header

        if method == "GET":
            resp = await self._client.get(path, headers=request_headers)
        elif method == "POST":
            if data is not None:
                from urllib.parse import urlencode
                body = urlencode(data).encode()
                request_headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                body = b""
            resp = await self._client.post(path, data=body, headers=request_headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        self._store_cookies(resp.headers)
        body = await resp.get_data()
        return Response(resp.status_code, list(resp.headers), body)

    def _store_cookies(self, headers):
        for key, value in headers:
            if key.lower() != "set-cookie":
                continue
            parsed = SimpleCookie()
            parsed.load(value)
            for name, morsel in parsed.items():
                if not morsel.value or morsel["max-age"] == "0":
                    self.cookies.pop(name, None)
                else:
                    self.cookies[name] = morsel.value


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def test_config(tmp_path) -> AppConfig:
    """An AppConfig pointing entirely at a throwaway directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return AppConfig(
        db_file=tmp_path / "meter_logs.db",
        host="127.0.0.1",
        port=0,
        server="wsgiref",
        app_version="test",
        auth_db_file=tmp_path / "auth.db",
        data_dir=data_dir,
        auth_secret="test-secret",
    )


@pytest.fixture(autouse=True)
async def isolate(test_config, tmp_path, monkeypatch):
    """Redirect every hard-coded path/global at the temporary directory."""
    import config as config_module

    import core.app as core_app
    import dashboard.routes as dashboard_routes
    import entry.routes as entry_routes
    import entry.services as entry_services
    import admin.routes as admin_routes
    import admin.services as admin_services
    import auth.db as auth_db
    import auth.routes as auth_routes
    import auth.deps as auth_deps
    import auth.policy as auth_policy
    import main

    monkeypatch.setattr(auth_db, "AUTH_DB", test_config.auth_db_file)
    monkeypatch.setattr(auth_db, "DATA_DIR", test_config.data_dir)
    monkeypatch.setattr(auth_db, "SECRET", test_config.auth_secret.encode())
    monkeypatch.setattr(auth_db, "config", test_config)
    # Provisioning / schema caches are process-wide; reset so each test
    # provisions afresh against its own temporary directory.
    monkeypatch.setattr(auth_db, "_provisioned_dbs", set())
    import libsolar_sqlite
    monkeypatch.setattr(libsolar_sqlite, "_schema_ready", set())
    await auth_db.init_auth_db()

    # Patch config in all modules that capture load_config() at import time
    modules_with_config = [
        auth_db, auth_routes, auth_deps, auth_policy,
        core_app,
        dashboard_routes, entry_routes, entry_services,
        admin_routes, admin_services,
        main,
    ]
    for mod in modules_with_config:
        if hasattr(mod, "config"):
            monkeypatch.setattr(mod, "config", test_config)

    # In-function `from config import load_config` calls.
    monkeypatch.setattr(config_module, "load_config", lambda: test_config)

    # Module-level `config = load_config()` captures.
    for module_name in CONFIG_MODULES:
        module = importlib.import_module(module_name)
        if hasattr(module, "config"):
            monkeypatch.setattr(module, "config", test_config)

    # Authorization policy: work on a throwaway copy of auth/policy.csv and
    # reset the process-wide enforcer so tests never touch the real policy.
    import auth.policy as policy_module

    tmp_policy = tmp_path / "policy.csv"
    shutil.copy(policy_module.POLICY_PATH, tmp_policy)
    monkeypatch.setattr(policy_module, "POLICY_PATH", tmp_policy)
    monkeypatch.setattr(policy_module, "_policy", None)

    yield test_config


@pytest.fixture
def app(isolate, test_config):
    """A freshly built Quart application using the isolated config."""
    from core.app import create_app

    return create_app(test_config)


@pytest.fixture
def client(app) -> Client:
    return Client(app)


@pytest.fixture
def new_client(app):
    """Factory for additional independent clients (separate cookie jars)."""

    def _new() -> Client:
        return Client(app)

    return _new


@pytest.fixture
def make_user():
    """Create a user directly in the isolated auth database."""
    from auth.db import create_user

    async def _make(
        username="user1",
        password="password123",
        full_name="User One",
        role="user",
        db_file=None,
        status="approved",
    ) -> int:
        if db_file is None:
            db_file = f"{username}.db"
        return await create_user(username, password, full_name, role, db_file, status)

    return _make


@pytest.fixture
async def admin(make_user):
    uid = await make_user("admin", "admin12345", "Administrator", "admin", "./meter_logs.db")
    return {"id": uid, "username": "admin", "password": "admin12345"}


@pytest.fixture
async def user(make_user):
    uid = await make_user("user1", "password123", "User One", "user", "user1.db")
    return {"id": uid, "username": "user1", "password": "password123"}


@pytest.fixture
def login(client):
    """Log the given credential dict in through the login form."""

    async def _login(creds: dict):
        resp = await client.post(
            "/login", {"username": creds["username"], "password": creds["password"]}
        )
        assert resp.status in (302, 303), f"login failed: {resp.status} {resp.text[:200]}"
        return resp

    return _login