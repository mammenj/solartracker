#!/usr/bin/env python
"""Performance profiler for the Solar Tracker.

Runs the app in-process against a throwaway database, seeds a little data, then
reports where request time actually goes:

* per-route latency over a warm loop,
* the exact SQLite statements each route issues (steady state),
* the cost of ``Policy.can`` with the cache warm vs. cold,
* a ``cProfile`` breakdown of the dashboard render.

It never touches the real ``auth.db``, ``data/`` or ``auth/policy.csv``: every
path is redirected into a temporary directory first, exactly like the test
suite does.

Usage::

    uv run python scripts/perf_profile.py
    uv run python scripts/perf_profile.py --iterations 50 --profile-route /app/entry
"""

from __future__ import annotations

import argparse
import asyncio
import cProfile
import io
import pstats
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode

# ``config.load_config`` parses sys.argv with argparse, which would choke on
# this script's own arguments. Neutralise it before any app module imports.
sys.argv = ["st"]

import aiosqlite

from config import AppConfig

# ---------------------------------------------------------------------------
# SQLite statement counting
# ---------------------------------------------------------------------------
# Patch the aiosqlite connection methods so every statement issued anywhere in
# the app is counted - this is API-level, so it is exact (unlike wrapping
# sqlite3.connect, which aiosqlite runs on its own worker thread).
_STATEMENTS: list[str] = []
_real_execute = aiosqlite.Connection.execute
_real_executescript = getattr(aiosqlite.Connection, "executescript", None)


async def _counted_execute(self, sql, *args, **kwargs):
    _STATEMENTS.append(" ".join(str(sql).split())[:70])
    return await _real_execute(self, sql, *args, **kwargs)


async def _counted_executescript(self, sql, *args, **kwargs):
    _STATEMENTS.append("<executescript>")
    return await _real_executescript(self, sql, *args, **kwargs)


def install_statement_counter() -> None:
    aiosqlite.Connection.execute = _counted_execute
    if _real_executescript is not None:
        aiosqlite.Connection.executescript = _counted_executescript


def take_statements() -> list[str]:
    """Return the statements recorded since the last call and reset the list."""
    recorded = list(_STATEMENTS)
    _STATEMENTS.clear()
    return recorded


# ---------------------------------------------------------------------------
# Minimal cookie-aware client over Quart's test client
# ---------------------------------------------------------------------------
class Session:
    def __init__(self, app):
        self._client = app.test_client()
        self.cookies: dict[str, str] = {}

    async def _post_form(self, path: str, data: dict):
        body = urlencode(data).encode()
        resp = await self._client.post(
            path,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        await resp.get_data()
        self._store_cookies(resp)
        return resp

    async def get(self, path: str):
        headers = {}
        if self.cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        resp = await self._client.get(path, headers=headers)
        await resp.get_data()
        self._store_cookies(resp)
        return resp

    def _store_cookies(self, resp):
        for key, value in resp.headers:
            if key.lower() != "set-cookie":
                continue
            name, _, rest = value.partition("=")
            self.cookies[name] = rest.split(";", 1)[0]

    async def login(self, username: str, password: str):
        # Login responds with a redirect, which httpx would follow; the test
        # client returns it directly, so the Set-Cookie is captured above.
        return await self._post_form(
            "/login", {"username": username, "password": password}
        )


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
def make_config(root: Path) -> AppConfig:
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return AppConfig(
        db_file=root / "meter_logs.db",
        host="127.0.0.1",
        port=0,
        server="quart",
        app_version="profile",
        auth_db_file=root / "auth.db",
        data_dir=data_dir,
        auth_secret="profile-secret",
    )


async def build_app(root: Path):
    """Create the app with all globals redirected at ``root``."""
    import auth.db as auth_db
    import auth.policy as policy_module

    cfg = make_config(root)
    auth_db.AUTH_DB = cfg.auth_db_file
    auth_db.DATA_DIR = cfg.data_dir
    auth_db.SECRET = cfg.auth_secret.encode()
    auth_db.config = cfg

    # Work on a throwaway policy copy so the real policy.csv is never written.
    tmp_policy = root / "policy.csv"
    shutil.copy(policy_module.POLICY_PATH, tmp_policy)
    policy_module.POLICY_PATH = tmp_policy
    policy_module._policy = None

    from core.app import create_app

    app = create_app(cfg)
    await auth_db.init_auth_db()
    return app, auth_db


async def seed_data(auth_db, readings: int = 60) -> None:
    """Create one admin and one normal user, plus some meter readings."""
    from datetime import datetime, timedelta

    from libsolar_sqlite import MeterReadingStore

    await auth_db.create_user("prof", "prof12345", "Prof", "admin", "./prof.db", "approved")
    await auth_db.create_user("norm", "norm12345", "Norm", "user", "./prof.db", "approved")

    store = MeterReadingStore(await auth_db.ensure_user_db("./prof.db"))
    base = datetime(2026, 1, 1)
    for i in range(1, readings + 1):
        await store.save_or_update(
            type(
                "R",
                (),
                {
                    "date": base + timedelta(days=i),
                    "import_units": 100 + i,
                    "export_units": 50 + i,
                    "solar_units": 30 + i,
                },
            )()
        )
    await store.aclose()


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------
async def report_latency(session: Session, routes: dict[str, str], iterations: int) -> None:
    print(f"\n=== Per-route latency ({iterations} iterations, in-process) ===")
    for label, path in routes.items():
        for _ in range(3):  # warmup
            await session.get(path)
        start = time.perf_counter()
        for _ in range(iterations):
            await session.get(path)
        avg_ms = (time.perf_counter() - start) / iterations * 1000
        print(f"  {label:34s} {avg_ms:8.2f} ms")


async def report_statements(routes: dict[str, str], sessions: dict[str, Session]) -> None:
    print("\n=== SQLite statements per request (steady state) ===")
    for label, path in routes.items():
        session = sessions[label]
        # Warm once: the first request may include one-time schema DDL.
        await session.get(path)
        take_statements()
        resp = await session.get(path)
        statements = take_statements()
        print(f"\n  {label}  ->  {resp.status_code}  {len(statements)} statements")
        for sql in statements:
            print(f"      - {sql}")


def report_can_benchmark(policy, n: int = 20000) -> None:
    print("\n=== Policy.can() microbenchmark ===")
    user = {"role": "admin"}

    start = time.perf_counter()
    for _ in range(n):
        policy.can(user, "dashboard", "view")
    cached_us = (time.perf_counter() - start) / n * 1e6
    print(f"  can() warm (cache hit)          : {cached_us:8.2f} us/call")

    start = time.perf_counter()
    for _ in range(n):
        policy._can_cache.clear()  # force the uncached path
        policy.can(user, "dashboard", "view")
    uncached_us = (time.perf_counter() - start) / n * 1e6
    print(f"  can() cold (real enforce)       : {uncached_us:8.2f} us/call")

    start = time.perf_counter()
    for _ in range(n):
        policy.home_for(user)
    home_us = (time.perf_counter() - start) / n * 1e6
    print(f"  home_for()                      : {home_us:8.2f} us/call")

    if cached_us > 0:
        print(f"  speedup from cache              : {uncached_us / cached_us:8.0f}x")


async def report_profile(app, session: Session, path: str, iterations: int) -> None:
    print(f"\n=== cProfile: {iterations}x GET {path} ===")
    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(iterations):
        await session.get(path)
    profiler.disable()

    buf = io.StringIO()
    pstats.Stats(profiler, stream=buf).sort_stats("cumulative").print_stats(20)
    # Drop the pstats header line noise, keep the table.
    lines = buf.getvalue().splitlines()
    print("\n".join(lines[:40]))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20,
                        help="iterations per route for the latency loop")
    parser.add_argument("--profile-iterations", type=int, default=50,
                        help="iterations for the cProfile section")
    parser.add_argument("--profile-route", default="/app/dashboard",
                        help="route to profile with cProfile")
    args = parser.parse_args()

    root = Path(tempfile.mkdtemp(prefix="st-profile-", dir="/tmp/opencode"))
    print(f"Profiling against throwaway dir: {root}")

    install_statement_counter()
    app, auth_db = await build_app(root)
    await seed_data(auth_db)

    from auth.policy import get_policy

    normal = Session(app)
    await normal.login("norm", "norm12345")
    admin = Session(app)
    await admin.login("prof", "prof12345")

    # A normal user lands on the dashboard; the admin lands on /admin/users.
    normal_routes = {
        "GET /app/dashboard": "/app/dashboard",
        "GET /app/entry": "/app/entry",
    }
    admin_routes = {
        "GET /admin/users": "/admin/users",
        "GET /admin/roles": "/admin/roles",
    }

    all_routes = {**normal_routes, **admin_routes}
    sessions = {label: (admin if label.startswith("GET /admin") else normal)
                for label in all_routes}

    await report_latency(normal, {**normal_routes, **admin_routes}, args.iterations)
    await report_statements(all_routes, sessions)
    report_can_benchmark(get_policy())

    profile_session = sessions.get(args.profile_route, normal)
    await report_profile(app, profile_session, args.profile_route, args.profile_iterations)


if __name__ == "__main__":
    asyncio.run(main())
