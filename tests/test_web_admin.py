"""HTTP-level tests for the admin user-management area."""

from auth.db import get_user, get_user_by_id


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
def test_admin_can_open_user_management(client, login, admin):
    login(admin)
    resp = client.get("/admin/users")
    assert resp.status == 200
    assert "User Management" in resp.text


def test_admin_is_redirected_away_from_user_pages(client, login, admin):
    login(admin)
    for path in ("/", "/app/dashboard", "/app/entry"):
        resp = client.get(path)
        assert resp.status == 303, path
        assert resp.location == "/admin/users", path


def test_normal_user_is_forbidden_from_admin(client, login, user):
    login(user)
    for path in ("/admin/users", "/admin/users/new"):
        assert client.get(path).status == 403, path


def test_normal_user_cannot_create_users(client, login, user):
    login(user)
    resp = client.post(
        "/admin/users",
        {"username": "sneaky", "password": "password123", "full_name": "S", "role": "user"},
    )
    assert resp.status == 403
    assert get_user("sneaky") is None


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def test_new_user_form_shows_database_file_field(client, login, admin):
    login(admin)
    resp = client.get("/admin/users/new")
    assert resp.status == 200
    assert "Create User" in resp.text
    assert "Database File" in resp.text


def test_create_normal_user_requires_db_file(client, login, admin):
    login(admin)
    resp = client.post(
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
    assert get_user("newbie") is None


def test_create_normal_user_succeeds_and_user_can_log_in(client, login, admin, new_client):
    login(admin)
    resp = client.post(
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
    assert get_user("newbie")["db_file"] == "newbie.db"

    other = new_client()
    login_resp = other.post("/login", {"username": "newbie", "password": "password123"})
    assert login_resp.status == 303
    assert login_resp.location == "/app/dashboard"


def test_create_admin_user_does_not_require_db_file(client, login, admin, new_client):
    login(admin)
    resp = client.post(
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

    boss = get_user("boss")
    assert boss["role"] == "admin"
    assert boss["db_file"] == ""

    # Administrators have no readings database; the app must still work for them.
    other = new_client()
    assert other.post("/login", {"username": "boss", "password": "password123"}).status == 303
    assert other.get("/admin/users").status == 200


def test_create_user_rejects_duplicate_username(client, login, admin, user):
    login(admin)
    resp = client.post(
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


def test_create_user_rejects_short_password(client, login, admin):
    login(admin)
    resp = client.post(
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
    assert get_user("shorty") is None


# ---------------------------------------------------------------------------
# Edit / update
# ---------------------------------------------------------------------------
def test_edit_form_prefills_existing_user(client, login, admin, user):
    login(admin)
    resp = client.get(f"/admin/users/{user['id']}/edit")
    assert resp.status == 200
    assert "Edit User" in resp.text
    assert "user1" in resp.text


def test_edit_unknown_user_redirects(client, login, admin):
    login(admin)
    resp = client.get("/admin/users/9999/edit")
    assert resp.status == 303
    assert resp.location == "/admin/users"


def test_update_user_details(client, login, admin, user):
    login(admin)
    resp = client.post(
        f"/admin/users/{user['id']}",
        {
            "full_name": "Renamed Person",
            "role": "user",
            "status": "disabled",
            "db_file": "user1.db",
        },
    )
    assert resp.status == 303

    updated = get_user_by_id(user["id"])
    assert updated["full_name"] == "Renamed Person"
    assert updated["status"] == "disabled"


def test_promoting_user_to_admin_keeps_db_file(client, login, admin, user):
    login(admin)
    client.post(
        f"/admin/users/{user['id']}",
        {"full_name": "User One", "role": "admin", "status": "approved"},
    )
    updated = get_user_by_id(user["id"])
    assert updated["role"] == "admin"
    # db_file is only written for role=user, so the previous value survives
    assert updated["db_file"] == "user1.db"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
def test_admin_cannot_delete_self(client, login, admin):
    login(admin)
    resp = client.post(f"/admin/users/{admin['id']}/delete")
    assert resp.status == 400
    assert get_user_by_id(admin["id"]) is not None


def test_admin_can_delete_another_user(client, login, admin, user):
    login(admin)
    resp = client.post(f"/admin/users/{user['id']}/delete")
    assert resp.status == 303
    assert get_user_by_id(user["id"]) is None


# ---------------------------------------------------------------------------
# Listing / partials
# ---------------------------------------------------------------------------
def test_admin_users_paging_and_sorting(client, login, admin):
    login(admin)
    resp = client.get("/admin/users?page=2&sort=username&order=asc")
    assert resp.status == 200
    assert "User Management" in resp.text


def test_admin_users_partial_for_htmx(client, login, admin):
    login(admin)
    resp = client.get("/admin/users/partial", headers={"HX-Request": "true"})
    assert resp.status == 200
    assert "User Management" in resp.text
    assert "<html" not in resp.text
