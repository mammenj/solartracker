"""HTTP-level tests for the admin user-management area."""

from auth.db_quart import get_user, get_user_by_id


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
async def test_admin_can_open_user_management(client, login, admin):
    await login(admin)
    resp = await client.get("/admin/users")
    assert resp.status == 200
    assert "User Management" in resp.text


async def test_admin_is_redirected_away_from_user_pages(client, login, admin):
    await login(admin)
    for path in ("/", "/app/dashboard", "/app/entry"):
        resp = await client.get(path)
        assert resp.status == 303, path
        assert resp.location == "/admin/users", path


async def test_normal_user_is_redirected_home_from_admin(client, login, user):
    await login(user)
    for path in ("/admin/users", "/admin/users/new"):
        resp = await client.get(path)
        assert resp.status == 303, path
        assert resp.location == "/app/dashboard", path


async def test_normal_user_cannot_create_users(client, login, user):
    await login(user)
    resp = await client.post(
        "/admin/users",
        {"username": "sneaky", "password": "password123", "full_name": "S", "role": "user"},
    )
    assert resp.status == 303
    assert resp.location == "/app/dashboard"
    assert await get_user("sneaky") is None


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
async def test_new_user_form_shows_database_file_field(client, login, admin):
    await login(admin)
    resp = await client.get("/admin/users/new")
    assert resp.status == 200
    assert "Create User" in resp.text
    assert "Database File" in resp.text


async def test_create_normal_user_requires_db_file(client, login, admin):
    await login(admin)
    resp = await client.post(
        "/admin/users",
        {
            "username": "newbie",
            "password": "password123",
            "full_name": "New Bie",
            "role": "user",
            "status": "approved",
            "db_file": "",
        },
    )
    assert resp.status == 200
    assert "Database file required" in resp.text
    assert await get_user("newbie") is None


async def test_create_normal_user_succeeds_and_user_can_log_in(client, login, admin, new_client):
    await login(admin)
    resp = await client.post(
        "/admin/users",
        {
            "username": "newbie",
            "password": "password123",
            "full_name": "New Bie",
            "role": "user",
            "status": "approved",
            "db_file": "newbie.db",
        },
    )
    assert resp.status == 303
    assert resp.location == "/admin/users"
    assert (await get_user("newbie"))["db_file"] == "newbie.db"

    other = new_client()
    login_resp = await other.post("/login", {"username": "newbie", "password": "password123"})
    assert login_resp.status == 303
    assert login_resp.location == "/app/dashboard"


async def test_create_admin_user_does_not_require_db_file(client, login, admin, new_client):
    await login(admin)
    resp = await client.post(
        "/admin/users",
        {
            "username": "boss",
            "password": "password123",
            "full_name": "Boss",
            "role": "admin",
            "status": "approved",
        },
    )
    assert resp.status == 303

    boss = await get_user("boss")
    assert boss["role"] == "admin"
    assert boss["db_file"] == ""

    # Administrators have no readings database; the app must still work for them.
    other = new_client()
    assert (await other.post("/login", {"username": "boss", "password": "password123"})).status == 303
    assert (await other.get("/admin/users")).status == 200


async def test_create_user_rejects_duplicate_username(client, login, admin, user):
    await login(admin)
    resp = await client.post(
        "/admin/users",
        {
            "username": "user1",
            "password": "password123",
            "full_name": "Duplicate",
            "role": "user",
            "status": "approved",
            "db_file": "dup.db",
        },
    )
    assert resp.status == 200
    assert "Username already exists" in resp.text


async def test_create_user_rejects_short_password(client, login, admin):
    await login(admin)
    resp = await client.post(
        "/admin/users",
        {
            "username": "shorty",
            "password": "short",
            "full_name": "Shorty",
            "role": "user",
            "status": "approved",
            "db_file": "shorty.db",
        },
    )
    assert resp.status == 200
    assert "Password must be at least 8 characters" in resp.text
    assert await get_user("shorty") is None


# ---------------------------------------------------------------------------
# Edit / update
# ---------------------------------------------------------------------------
async def test_edit_form_prefills_existing_user(client, login, admin, user):
    await login(admin)
    resp = await client.get(f"/admin/users/{user['id']}/edit")
    assert resp.status == 200
    assert "Edit User" in resp.text
    assert "user1" in resp.text


async def test_edit_unknown_user_redirects(client, login, admin):
    await login(admin)
    resp = await client.get("/admin/users/9999/edit")
    assert resp.status == 303
    assert resp.location == "/admin/users"


async def test_update_user_details(client, login, admin, user):
    await login(admin)
    resp = await client.post(
        f"/admin/users/{user['id']}",
        {
            "full_name": "Renamed Person",
            "role": "user",
            "status": "disabled",
            "db_file": "user1.db",
        },
    )
    assert resp.status == 303

    updated = await get_user_by_id(user["id"])
    assert updated["full_name"] == "Renamed Person"
    assert updated["status"] == "disabled"


async def test_promoting_user_to_admin_keeps_db_file(client, login, admin, user):
    await login(admin)
    await client.post(
        f"/admin/users/{user['id']}",
        {"full_name": "User One", "role": "admin", "status": "approved"},
    )
    updated = await get_user_by_id(user["id"])
    assert updated["role"] == "admin"
    # db_file is only written for role=user, so the previous value survives
    assert updated["db_file"] == "user1.db"


async def test_admin_cannot_change_own_role(client, login, admin):
    await login(admin)
    resp = await client.post(
        f"/admin/users/{admin['id']}",
        {"full_name": "Administrator", "role": "user", "status": "approved"},
    )
    assert resp.status == 200
    assert "cannot change your own role" in resp.text
    assert (await get_user_by_id(admin["id"]))["role"] == "admin"


async def test_admin_cannot_disable_own_account(client, login, admin):
    await login(admin)
    resp = await client.post(
        f"/admin/users/{admin['id']}",
        {"full_name": "Administrator", "role": "admin", "status": "disabled"},
    )
    assert resp.status == 200
    assert "cannot disable your own account" in resp.text
    assert (await get_user_by_id(admin["id"]))["status"] == "approved"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
async def test_admin_cannot_delete_self(client, login, admin):
    await login(admin)
    resp = await client.post(f"/admin/users/{admin['id']}/delete")
    assert resp.status == 400
    assert await get_user_by_id(admin["id"]) is not None


async def test_admin_can_delete_another_user(client, login, admin, user):
    await login(admin)
    resp = await client.post(f"/admin/users/{user['id']}/delete")
    assert resp.status == 303
    assert await get_user_by_id(user["id"]) is None


# ---------------------------------------------------------------------------
# htmx driven user management
# ---------------------------------------------------------------------------
async def test_delete_user_via_htmx_returns_refreshed_panel(client, login, admin, user):
    await login(admin)
    resp = await client.post(
        f"/admin/users/{user['id']}/delete", headers={"HX-Request": "true"}
    )
    assert resp.status == 200
    assert "User Management" in resp.text
    assert user["username"] not in resp.text
    assert await get_user_by_id(user["id"]) is None


async def test_delete_user_form_is_htmx_driven(client, login, admin, user):
    await login(admin)
    resp = await client.get("/admin/users")
    assert f'hx-post="/admin/users/{user["id"]}/delete"' in resp.text
    assert 'hx-confirm="Delete user' in resp.text


async def test_current_user_row_has_no_delete_button(client, login, admin):
    await login(admin)
    resp = await client.get("/admin/users")
    assert f'hx-post="/admin/users/{admin["id"]}/delete"' not in resp.text


async def test_user_list_sorting_and_paging_refresh_the_panel(client, login, admin):
    await login(admin)
    resp = await client.get("/admin/users")
    # The sort headers / pagination swap the whole panel into the tab content.
    assert 'hx-target="#tab-content"' in resp.text
    assert 'hx-target="#admin-users-table"' not in resp.text
    assert 'hx-swap="outerHTML"' not in resp.text


async def test_create_user_via_htmx_returns_the_panel(client, login, admin):
    await login(admin)
    resp = await client.post(
        "/admin/users",
        {
            "username": "htmxuser",
            "password": "password123",
            "full_name": "Htmx User",
            "role": "user",
            "status": "approved",
            "db_file": "htmxuser.db",
        },
        headers={"HX-Request": "true"},
    )
    assert resp.status == 200
    assert "User Management" in resp.text
    assert "htmxuser" in resp.text
    assert await get_user("htmxuser") is not None


async def test_create_user_via_htmx_reports_validation_errors(client, login, admin):
    await login(admin)
    resp = await client.post(
        "/admin/users",
        {
            "username": "htmxuser",
            "password": "password123",
            "full_name": "Htmx User",
            "role": "user",
            "status": "approved",
            "db_file": "",
        },
        headers={"HX-Request": "true"},
    )
    assert resp.status == 200
    assert "Database file required" in resp.text
    assert "Create User" in resp.text
    assert await get_user("htmxuser") is None


async def test_update_user_via_htmx_returns_the_panel(client, login, admin, user):
    await login(admin)
    resp = await client.post(
        f"/admin/users/{user['id']}",
        {"full_name": "Renamed", "role": "user", "status": "approved", "db_file": "user1.db"},
        headers={"HX-Request": "true"},
    )
    assert resp.status == 200
    assert "User Management" in resp.text
    assert (await get_user_by_id(user["id"]))["full_name"] == "Renamed"


# ---------------------------------------------------------------------------
# Listing / partials
# ---------------------------------------------------------------------------
async def test_admin_users_paging_and_sorting(client, login, admin):
    await login(admin)
    resp = await client.get("/admin/users?page=2&sort=username&order=asc")
    assert resp.status == 200
    assert "User Management" in resp.text


async def test_admin_users_partial_for_htmx(client, login, admin):
    await login(admin)
    resp = await client.get("/admin/users/partial", headers={"HX-Request": "true"})
    assert resp.status == 200
    assert "User Management" in resp.text
    assert "<html" not in resp.text