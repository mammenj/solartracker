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
from http.cookies import SimpleCookie
from io import BytesIO
from urllib.parse import urlencode, urlsplit

import pytest
from wsgiref.util import setup_testing_defaults

from config import AppConfig

# Modules that keep a module-level ``config`` object bound at import time.
CONFIG_MODULES = [
    "auth.db",
    "auth.deps",
    "auth.routes",
    "core.app",
    "core.deps",
    "dashboard.routes",
    "entry.routes",
    "entry.services",
    "admin.routes",
    "admin.services",
]


# ---------------------------------------------------------------------------
# Minimal WSGI test client (no third-party dependency)
# ---------------------------------------------------------------------------
class Response:
    """A lightweight HTTP response wrapper."""

    def __init__(self, status_line: str, headers: list[tuple[str, str]], body: bytes):
        self.status = int(status_line.split(" ", 1)[0])
        self.status_line = status_line
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
    """A tiny cookie-aware WSGI client for exercising the Bottle app."""

    def __init__(self, app):
        self.app = app
        self.cookies: dict[str, str] = {}

    # -- request helpers ---------------------------------------------------
    def get(self, path: str, headers: dict | None = None) -> Response:
        return self.request("GET", path, headers=headers)

    def post(self, path: str, data: dict | None = None, headers: dict | None = None) -> Response:
        return self.request("POST", path, data=data or {}, headers=headers)

    def request(self, method: str, path: str, data: dict | None = None, headers: dict | None = None) -> Response:
        environ = self._build_environ(method, path, data, headers)
        captured: dict = {}

        def start_response(status, response_headers, exc_info=None):
            captured["status"] = status
            captured["headers"] = response_headers

        body = b"".join(self.app(environ, start_response))
        response = Response(captured["status"], captured["headers"], body)
        self._store_cookies(response.headers)
        return response

    # -- internals ---------------------------------------------------------
    def _build_environ(self, method: str, path: str, data: dict | None, headers: dict | None) -> dict:
        parts = urlsplit(path)
        body = urlencode(data).encode() if data is not None else b""

        environ: dict = {}
        setup_testing_defaults(environ)
        # Bottle emits 303 redirects for HTTP/1.1 and 302 for HTTP/1.0; browsers
        # and curl speak 1.1, so the tests should too.
        environ["SERVER_PROTOCOL"] = "HTTP/1.1"
        environ["REQUEST_METHOD"] = method.upper()
        environ["PATH_INFO"] = parts.path or "/"
        environ["QUERY_STRING"] = parts.query
        environ["wsgi.input"] = BytesIO(body)
        environ["CONTENT_LENGTH"] = str(len(body))
        if data is not None:
            environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        if self.cookies:
            environ["HTTP_COOKIE"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        for key, value in (headers or {}).items():
            environ["HTTP_" + key.upper().replace("-", "_")] = value
        return environ

    def _store_cookies(self, headers: list[tuple[str, str]]) -> None:
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
def isolate(test_config, monkeypatch):
    """Redirect every hard-coded path/global at the temporary directory."""
    import config as config_module

    import auth.db as auth_db

    monkeypatch.setattr(auth_db, "AUTH_DB", test_config.auth_db_file)
    monkeypatch.setattr(auth_db, "DATA_DIR", test_config.data_dir)
    monkeypatch.setattr(auth_db, "SECRET", test_config.auth_secret.encode())
    auth_db.init_auth_db()

    # In-function `from config import load_config` calls.
    monkeypatch.setattr(config_module, "load_config", lambda: test_config)

    # Module-level `config = load_config()` captures.
    for module_name in CONFIG_MODULES:
        module = importlib.import_module(module_name)
        if hasattr(module, "config"):
            monkeypatch.setattr(module, "config", test_config)

    yield test_config


@pytest.fixture
def app(isolate, test_config):
    """A freshly built Bottle application using the isolated config."""
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

    def _make(
        username="user1",
        password="password123",
        full_name="User One",
        role="user",
        db_file=None,
        status="approved",
    ) -> int:
        if db_file is None:
            db_file = f"{username}.db"
        return create_user(username, password, full_name, role, db_file, status)

    return _make


@pytest.fixture
def admin(make_user):
    uid = make_user("admin", "admin12345", "Administrator", "admin", "./meter_logs.db")
    return {"id": uid, "username": "admin", "password": "admin12345"}


@pytest.fixture
def user(make_user):
    uid = make_user("user1", "password123", "User One", "user", "user1.db")
    return {"id": uid, "username": "user1", "password": "password123"}


@pytest.fixture
def login(client):
    """Log the given credential dict in through the login form."""

    def _login(creds: dict):
        resp = client.post(
            "/login", {"username": creds["username"], "password": creds["password"]}
        )
        assert resp.status == 303, f"login failed: {resp.status} {resp.text[:200]}"
        return resp

    return _login
