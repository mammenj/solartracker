"""Tests for the application factory and route wiring (core/app.py)."""

# Bottle stores a route's methods as a string of single-letter flags
# (e.g. "GET" -> 'G', "POST" -> 'P').
METHOD_LETTER = {"GET": "G", "POST": "P"}

EXPECTED_ROUTES = {
    ("GET", "/setup"),
    ("POST", "/setup"),
    ("GET", "/login"),
    ("POST", "/login"),
    ("POST", "/logout"),
    ("GET", "/"),
    ("GET", "/app/dashboard"),
    ("GET", "/app/dashboard/partial"),
    ("GET", "/app/dashboard/periods-table"),
    ("GET", "/app/dashboard/chart"),
    ("GET", "/app/entry"),
    ("GET", "/app/entry/partial"),
    ("GET", "/app/entry/readings-table"),
    ("POST", "/readings"),
    ("GET", "/admin/users"),
    ("GET", "/admin/users/partial"),
    ("GET", "/admin/users/new"),
    ("POST", "/admin/users"),
    ("GET", "/admin/users/<user_id:int>/edit"),
    ("POST", "/admin/users/<user_id:int>"),
    ("POST", "/admin/users/<user_id:int>/delete"),
    ("GET", "/static/<filename:path>"),
}


def test_create_app_returns_application(app):
    assert app is not None


def test_all_expected_routes_are_registered(app):
    registered = {
        (method, rule.rule)
        for rule in app.routes
        for method, letter in METHOD_LETTER.items()
        if letter in rule.method
    }

    missing = EXPECTED_ROUTES - registered
    assert not missing, f"missing routes: {sorted(missing)}"


def test_protected_routes_require_authentication(client):
    protected = [
        ("GET", "/"),
        ("GET", "/app/dashboard"),
        ("GET", "/app/dashboard/partial"),
        ("GET", "/app/dashboard/chart"),
        ("GET", "/app/entry"),
        ("GET", "/app/entry/readings-table"),
        ("GET", "/admin/users"),
        ("GET", "/admin/users/new"),
    ]
    for method, path in protected:
        resp = client.request(method, path)
        assert resp.status == 303, path
        assert resp.location == "/login", path
