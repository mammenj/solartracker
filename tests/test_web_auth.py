"""HTTP-level tests for authentication and first-run setup."""


# ---------------------------------------------------------------------------
# Route guard
# ---------------------------------------------------------------------------
async def test_unauthenticated_request_redirects_to_login(client):
    resp = await client.get("/")
    assert resp.status == 303
    assert resp.location == "/login"


async def test_invalid_session_cookie_is_rejected(client):
    client.cookies["session"] = "1:2:not-a-real-signature"
    resp = await client.get("/")
    assert resp.status == 303
    assert resp.location == "/login"


async def test_session_for_unknown_user_is_rejected(client):
    from auth.db import create_session

    client.cookies["session"] = create_session(9999)
    assert (await client.get("/")).status == 303


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
async def test_login_page_renders_when_users_exist(client, admin):
    resp = await client.get("/login")
    assert resp.status == 200
    assert "Sign in to continue" in resp.text


async def test_login_with_valid_credentials_sets_session_cookie(client, admin):
    resp = await client.post("/login", {"username": "admin", "password": "admin12345"})
    assert resp.status == 303
    # The landing page is declared per role in auth/policy.csv.
    assert resp.location == "/admin/users"
    assert "session" in client.cookies


async def test_login_with_wrong_password_shows_error(client, admin):
    resp = await client.post("/login", {"username": "admin", "password": "wrong-password"})
    assert resp.status == 200
    assert "Invalid username or password" in resp.text
    assert "session" not in client.cookies


async def test_login_with_unknown_username_shows_error(client, admin):
    resp = await client.post("/login", {"username": "nobody", "password": "password123"})
    assert resp.status == 200
    assert "Invalid username or password" in resp.text


async def test_unapproved_user_cannot_log_in(client, make_user):
    await make_user("pending1", "password123", "Pending", "user", "pending1.db", "pending")
    resp = await client.post("/login", {"username": "pending1", "password": "password123"})
    assert resp.status == 200
    assert "not approved" in resp.text
    assert "session" not in client.cookies


async def test_logout_clears_session(client, admin):
    await client.post("/login", {"username": "admin", "password": "admin12345"})
    resp = await client.post("/logout")
    assert resp.status == 303
    assert resp.location == "/login"
    assert "session" not in client.cookies
    assert (await client.get("/")).status == 303


# ---------------------------------------------------------------------------
# First-run setup
# ---------------------------------------------------------------------------
async def test_login_redirects_to_setup_when_no_users_exist(client):
    resp = await client.get("/login")
    assert resp.status == 303
    assert resp.location == "/setup"


async def test_setup_page_renders_when_no_users_exist(client):
    resp = await client.get("/setup")
    assert resp.status == 200
    assert "First-time setup" in resp.text


async def test_setup_redirects_to_login_once_a_user_exists(client, admin):
    resp = await client.get("/setup")
    assert resp.status == 303
    assert resp.location == "/login"


async def test_setup_validates_input(client):
    resp = await client.post("/setup", {"username": "", "password": "short", "full_name": ""})
    assert resp.status == 200
    assert "Username required" in resp.text
    assert "Password must be at least 8 characters" in resp.text
    assert "Full name required" in resp.text


async def test_setup_creates_an_admin_account(client, test_config):
    await client.post("/setup", {"username": "root", "password": "password123", "full_name": "Root"})

    from auth.db_quart import get_user

    root = await get_user("root")
    assert root is not None
    assert root["role"] == "admin"
    assert root["status"] == "approved"
    # A usable database file is recorded so authenticated requests don't fail.
    assert root["db_file"]
    assert root["db_file"] == test_config.db_file.name


async def test_setup_post_redirects_to_home(client):
    resp = await client.post(
        "/setup", {"username": "root", "password": "password123", "full_name": "Root"}
    )
    assert resp.status == 303
    assert resp.location == "/admin/users"
    assert "session" in client.cookies


async def test_setup_admin_can_use_the_app_immediately(client):
    await client.post("/setup", {"username": "root", "password": "password123", "full_name": "Root"})
    assert (await client.get("/admin/users")).status == 200