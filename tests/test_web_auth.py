"""HTTP-level tests for authentication and first-run setup."""


# ---------------------------------------------------------------------------
# Route guard
# ---------------------------------------------------------------------------
def test_unauthenticated_request_redirects_to_login(client):
    resp = client.get("/")
    assert resp.status == 303
    assert resp.location == "/login"


def test_invalid_session_cookie_is_rejected(client):
    client.cookies["session"] = "1:2:not-a-real-signature"
    resp = client.get("/")
    assert resp.status == 303
    assert resp.location == "/login"


def test_session_for_unknown_user_is_rejected(client):
    from auth.db import create_session

    client.cookies["session"] = create_session(9999)
    assert client.get("/").status == 303


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def test_login_page_renders_when_users_exist(client, admin):
    resp = client.get("/login")
    assert resp.status == 200
    assert "Sign in to continue" in resp.text


def test_login_with_valid_credentials_sets_session_cookie(client, admin):
    resp = client.post("/login", {"username": "admin", "password": "admin12345"})
    assert resp.status == 303
    assert resp.location == "/app/dashboard"
    assert "session" in client.cookies


def test_login_with_wrong_password_shows_error(client, admin):
    resp = client.post("/login", {"username": "admin", "password": "wrong-password"})
    assert resp.status == 200
    assert "Invalid username or password" in resp.text
    assert "session" not in client.cookies


def test_login_with_unknown_username_shows_error(client, admin):
    resp = client.post("/login", {"username": "nobody", "password": "password123"})
    assert resp.status == 200
    assert "Invalid username or password" in resp.text


def test_unapproved_user_cannot_log_in(client, make_user):
    make_user("pending1", "password123", "Pending", "user", "pending1.db", "pending")
    resp = client.post("/login", {"username": "pending1", "password": "password123"})
    assert resp.status == 200
    assert "not approved" in resp.text
    assert "session" not in client.cookies


def test_logout_clears_session(client, admin):
    client.post("/login", {"username": "admin", "password": "admin12345"})
    resp = client.post("/logout")
    assert resp.status == 303
    assert resp.location == "/login"
    assert "session" not in client.cookies
    assert client.get("/").status == 303


# ---------------------------------------------------------------------------
# First-run setup
# ---------------------------------------------------------------------------
def test_login_redirects_to_setup_when_no_users_exist(client):
    resp = client.get("/login")
    assert resp.status == 303
    assert resp.location == "/setup"


def test_setup_page_renders_when_no_users_exist(client):
    resp = client.get("/setup")
    assert resp.status == 200
    assert "First-time setup" in resp.text


def test_setup_redirects_to_login_once_a_user_exists(client, admin):
    resp = client.get("/setup")
    assert resp.status == 303
    assert resp.location == "/login"


def test_setup_validates_input(client):
    resp = client.post("/setup", {"username": "", "password": "short", "full_name": ""})
    assert resp.status == 200
    assert "Username required" in resp.text
    assert "Password must be at least 8 characters" in resp.text
    assert "Full name required" in resp.text


def test_setup_creates_an_admin_account(client, test_config):
    client.post("/setup", {"username": "root", "password": "password123", "full_name": "Root"})

    from auth.db import get_user

    root = get_user("root")
    assert root is not None
    assert root["role"] == "admin"
    assert root["status"] == "approved"
    # A usable database file is recorded so authenticated requests don't fail.
    assert root["db_file"]
    assert root["db_file"] == test_config.db_file.name


def test_setup_post_redirects_to_dashboard(client):
    resp = client.post(
        "/setup", {"username": "root", "password": "password123", "full_name": "Root"}
    )
    assert resp.status == 303
    assert resp.location == "/app/dashboard"
    assert "session" in client.cookies


def test_setup_admin_can_use_the_app_immediately(client):
    client.post("/setup", {"username": "root", "password": "password123", "full_name": "Root"})
    assert client.get("/admin/users").status == 200
