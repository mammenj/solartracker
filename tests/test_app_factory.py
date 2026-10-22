"""Tests for the application factory and route wiring (core/app.py)."""

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
    ("GET", "/admin/users/<int:user_id>/edit"),
    ("POST", "/admin/users/<int:user_id>"),
    ("POST", "/admin/users/<int:user_id>/delete"),
    ("GET", "/admin/roles"),
    ("GET", "/admin/roles/partial"),
    ("GET", "/admin/roles/new"),
    ("POST", "/admin/roles"),
    ("GET", "/admin/roles/<string:role>/edit"),
    ("POST", "/admin/roles/<string:role>"),
    ("POST", "/admin/roles/<string:role>/delete"),
    ("GET", "/static/<path:filename>"),
}


def test_create_app_returns_application(app):
    assert app is not None


def test_all_expected_routes_are_registered(app):
    registered = {
        (method, rule.rule)
        for rule in app.url_map.iter_rules()
        for method in rule.methods
        if method in ("GET", "POST")
    }

    missing = EXPECTED_ROUTES - registered
    assert not missing, f"missing routes: {sorted(missing)}"


async def test_protected_routes_require_authentication(client):
    protected = [
        ("GET", "/"),
        ("GET", "/app/dashboard"),
        ("GET", "/app/dashboard/partial"),
        ("GET", "/app/dashboard/chart"),
        ("GET", "/app/entry"),
        ("GET", "/app/entry/readings-table"),
        ("GET", "/admin/users"),
        ("GET", "/admin/users/new"),
        ("GET", "/admin/roles"),
        ("GET", "/admin/roles/new"),
    ]
    for method, path in protected:
        resp = await client.request(method, path)
        assert resp.status in (302, 303), path
        assert resp.location == "/login", path
