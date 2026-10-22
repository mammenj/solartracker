"""HTTP tests for admin-managed roles and permissions."""

from auth.db import get_user
from auth.policy import get_policy


def _role_form(role, home, permissions=()):
    return [("role", role), ("home", home)] + [
        ("permissions", permission) for permission in permissions
    ]


# ---------------------------------------------------------------------------
# Access to the roles admin
# ---------------------------------------------------------------------------
async def test_admin_can_view_roles(client, login, admin):
    await login(admin)
    resp = await client.get("/admin/roles")
    assert resp.status == 200
    assert "Roles & Permissions" in resp.text
    assert "admin" in resp.text
    assert "user" in resp.text
    assert "auth/policy.csv" in resp.text


async def test_normal_user_is_redirected_from_roles(client, login, user):
    await login(user)
    resp = await client.get("/admin/roles")
    assert resp.status in (302, 303)
    assert resp.location == "/app/dashboard"


async def test_htmx_request_gets_a_redirect_header_instead_of_a_body(client, login, user):
    """htmx must navigate, not paste a full page into the tab area."""
    await login(user)
    resp = await client.get("/admin/roles", headers={"HX-Request": "true"})
    assert resp.status == 200
    assert resp.header("HX-Redirect") == "/app/dashboard"
    assert resp.text == ""


async def test_roles_nav_visibility(client, login, admin, user, new_client):
    await login(admin)
    assert "/admin/roles" in (await client.get("/admin/users")).text

    other = new_client()
    await other.post("/login", {"username": user["username"], "password": user["password"]})
    assert "/admin/roles" not in (await other.get("/app/dashboard")).text


# ---------------------------------------------------------------------------
# Create / update / delete roles
# ---------------------------------------------------------------------------
async def test_admin_can_create_a_role(client, login, admin):
    await login(admin)
    resp = await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view", "entry:view"]),
    )
    assert resp.status in (302, 303)
    assert resp.location == "/admin/roles"

    policy = get_policy()
    assert "viewer" in policy.roles()
    assert policy.can({"role": "viewer"}, "dashboard", "view") is True
    assert policy.can({"role": "viewer"}, "entry", "view") is True
    assert policy.home_for({"role": "viewer"}) == "/app/dashboard"


async def test_admin_can_update_role_permissions(client, login, admin):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view"]),
    )

    resp = await client.post(
        "/admin/roles/viewer",
        [("home", "/app/entry"), ("permissions", "entry:view")],
    )
    assert resp.status in (302, 303)

    policy = get_policy()
    assert policy.can({"role": "viewer"}, "dashboard", "view") is False
    assert policy.can({"role": "viewer"}, "entry", "view") is True
    assert policy.home_for({"role": "viewer"}) == "/app/entry"


async def test_admin_can_delete_an_unused_role(client, login, admin):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("temp", "/app/dashboard", ["dashboard:view"]),
    )

    resp = await client.post("/admin/roles/temp/delete")
    assert resp.status in (302, 303)
    assert "temp" not in get_policy().roles()


async def test_delete_role_via_htmx_returns_refreshed_panel(client, login, admin):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("temp", "/app/dashboard", ["dashboard:view"]),
    )

    resp = await client.post("/admin/roles/temp/delete", headers={"HX-Request": "true"})
    assert resp.status == 200
    assert "Roles & Permissions" in resp.text
    assert "temp" not in get_policy().roles()


async def test_role_delete_form_is_htmx_driven(client, login, admin):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("temp", "/app/dashboard", ["dashboard:view"]),
    )

    resp = await client.get("/admin/roles")
    assert 'hx-post="/admin/roles/temp/delete"' in resp.text
    assert 'hx-confirm="Delete role' in resp.text


async def test_create_role_via_htmx_returns_the_panel(client, login, admin):
    await login(admin)
    resp = await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view"]),
        headers={"HX-Request": "true"},
    )
    assert resp.status == 200
    assert "Roles & Permissions" in resp.text
    assert "viewer" in resp.text
    assert "viewer" in get_policy().roles()


async def test_update_role_via_htmx_returns_the_panel(client, login, admin):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view"]),
    )

    resp = await client.post(
        "/admin/roles/viewer",
        [("home", "/app/entry"), ("permissions", "entry:view")],
        headers={"HX-Request": "true"},
    )
    assert resp.status == 200
    assert "Roles & Permissions" in resp.text
    assert get_policy().can({"role": "viewer"}, "entry", "view") is True


async def test_create_role_via_htmx_reports_validation_errors(client, login, admin):
    await login(admin)
    resp = await client.post(
        "/admin/roles",
        _role_form("viewer", "/admin/users", ["dashboard:view"]),
        headers={"HX-Request": "true"},
    )
    assert resp.status == 200
    assert "requires the" in resp.text
    assert "Create Role" in resp.text
    assert "viewer" not in get_policy().roles()


async def test_admin_cannot_delete_a_role_with_users(client, login, admin, make_user):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view"]),
    )
    await make_user("viewer1", "password123", "Viewer One", "viewer", "viewer1.db")

    resp = await client.post("/admin/roles/viewer/delete")
    assert resp.status == 400
    assert "viewer" in get_policy().roles()


async def test_admin_cannot_delete_their_own_role(client, login, admin):
    await login(admin)

    resp = await client.post("/admin/roles/admin/delete")
    assert resp.status == 400
    assert "admin" in get_policy().roles()


async def test_admin_cannot_remove_own_policy_permission(client, login, admin):
    await login(admin)

    resp = await client.post(
        "/admin/roles/admin",
        [
            ("home", "/admin/users"),
            ("permissions", "admin_users:view"),
            ("permissions", "admin_users:update"),
        ],
    )
    assert resp.status == 200
    assert "cannot remove your own ability" in resp.text
    assert get_policy().can({"role": "admin"}, "admin_policy", "update") is True

    # Keeping update but dropping view is also a lockout (no way back in).
    resp = await client.post(
        "/admin/roles/admin",
        [
            ("home", "/admin/users"),
            ("permissions", "admin_users:view"),
            ("permissions", "admin_policy:update"),
        ],
    )
    assert resp.status == 200
    assert "cannot remove your own ability" in resp.text
    assert get_policy().can({"role": "admin"}, "admin_policy", "view") is True


async def test_role_form_rejects_unknown_permission(client, login, admin):
    await login(admin)

    resp = await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["nope:view"]),
    )
    assert resp.status == 200
    assert "Unknown permission" in resp.text
    assert "viewer" not in get_policy().roles()


async def test_role_form_rejects_a_home_it_cannot_open(client, login, admin):
    await login(admin)

    resp = await client.post(
        "/admin/roles",
        _role_form("viewer", "/admin/users", ["dashboard:view"]),
    )
    assert resp.status == 200
    assert "requires the" in resp.text
    assert "viewer" not in get_policy().roles()


# ---------------------------------------------------------------------------
# Policy drives actual access
# ---------------------------------------------------------------------------
async def test_created_role_controls_access(client, login, admin, make_user, new_client):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view"]),
    )
    await make_user("viewer1", "password123", "Viewer One", "viewer", "viewer1.db")

    other = new_client()
    login_resp = await other.post(
        "/login", {"username": "viewer1", "password": "password123"}
    )
    assert login_resp.status in (302, 303)
    assert login_resp.location == "/app/dashboard"

    assert (await other.get("/")).status == 200
    # No entry permission -> redirected home.
    assert (await other.get("/app/entry")).status in (302, 303)
    assert (await other.get("/app/entry")).location == "/app/dashboard"
    # No admin permission -> redirected home.
    assert (await other.get("/admin/users")).status in (302, 303)
    assert (await other.get("/admin/users")).location == "/app/dashboard"


async def test_removing_a_permission_takes_effect_immediately(
    client, login, admin, make_user, new_client
):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view"]),
    )
    await make_user("viewer1", "password123", "Viewer One", "viewer", "viewer1.db")

    other = new_client()
    await other.post("/login", {"username": "viewer1", "password": "password123"})
    assert (await other.get("/")).status == 200

    # Replace the permission and move the home page through the admin UI.
    await client.post(
        "/admin/roles/viewer",
        [("home", "/app/entry"), ("permissions", "entry:view")],
    )

    resp = await other.get("/")
    assert resp.status in (302, 303)
    assert resp.location == "/app/entry"


async def test_forbidden_home_page_does_not_redirect_loop(
    client, login, admin, make_user, new_client
):
    await login(admin)
    # Simulate a hand-edited policy: a role with no permissions whose home is
    # a protected page (the admin UI rejects this combination).
    get_policy().upsert_role("viewer", [], "/app/dashboard")
    await make_user("viewer1", "password123", "Viewer One", "viewer", "")

    other = new_client()
    assert (
        (await other.post("/login", {"username": "viewer1", "password": "password123"})).location
        == "/app/dashboard"
    )

    resp = await other.get("/app/dashboard")
    assert resp.status in (302, 303)
    assert resp.location == "/login?error=no_access"
    assert "session" not in other.cookies


async def test_user_whose_role_was_removed_is_logged_out(client, login, user):
    await login(user)
    get_policy().delete_role("user")

    resp = await client.get("/app/dashboard")
    assert resp.status in (302, 303)
    assert resp.location == "/login?error=no_access"
    assert "session" not in client.cookies

    page = await client.get("/login?error=no_access")
    assert page.status == 200
    assert "landing page" in page.text


async def test_admin_cannot_post_readings(client, login, admin):
    await login(admin)
    resp = await client.post(
        "/readings",
        {
            "date": "2026-01-01",
            "import_units": "10",
            "export_units": "5",
            "solar_units": "3",
        },
    )
    assert resp.status in (302, 303)
    assert resp.location == "/admin/users"


async def test_entry_view_without_write_cannot_add_readings(
    client, login, admin, make_user, new_client
):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("reader", "/app/entry", ["entry:view"]),
    )
    await make_user("reader1", "password123", "Reader One", "reader", "reader1.db")

    other = new_client()
    await other.post("/login", {"username": "reader1", "password": "password123"})
    assert (await other.get("/app/entry")).status == 200

    resp = await other.post(
        "/readings",
        {
            "date": "2026-01-01",
            "import_units": "10",
            "export_units": "5",
            "solar_units": "3",
        },
    )
    assert resp.status in (302, 303)
    assert resp.location == "/app/entry"

    from auth.db import ensure_user_db
    from libsolar_sqlite import MeterReadingStore

    assert (await MeterReadingStore(await ensure_user_db("reader1.db")).count()) == 0


# ---------------------------------------------------------------------------
# User form integration
# ---------------------------------------------------------------------------
async def test_user_form_lists_policy_roles(client, login, admin):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view"]),
    )

    resp = await client.get("/admin/users/new")
    assert resp.status == 200
    assert 'value="viewer"' in resp.text


async def test_admin_can_create_user_with_custom_role(client, login, admin):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view"]),
    )

    resp = await client.post(
        "/admin/users",
        {
            "username": "viewer1",
            "password": "password123",
            "full_name": "Viewer One",
            "role": "viewer",
            "status": "approved",
            "db_file": "viewer1.db",
        },
    )
    assert resp.status in (302, 303)
    assert (await get_user("viewer1"))["role"] == "viewer"


async def test_role_without_readings_does_not_require_db_file(client, login, admin):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("ops", "/admin/users", ["admin_users:view"]),
    )

    resp = await client.post(
        "/admin/users",
        {
            "username": "ops1",
            "password": "password123",
            "full_name": "Ops One",
            "role": "ops",
            "status": "approved",
            "db_file": "",
        },
    )
    assert resp.status in (302, 303)
    assert (await get_user("ops1"))["role"] == "ops"


async def test_role_with_readings_requires_db_file(client, login, admin):
    await login(admin)
    await client.post(
        "/admin/roles",
        _role_form("viewer", "/app/dashboard", ["dashboard:view"]),
    )

    resp = await client.post(
        "/admin/users",
        {
            "username": "viewer1",
            "password": "password123",
            "full_name": "Viewer One",
            "role": "viewer",
            "status": "approved",
            "db_file": "",
        },
    )
    assert resp.status == 200
    assert "Database file required" in resp.text