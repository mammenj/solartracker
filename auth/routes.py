"""Authentication routes: login, logout, setup."""

from bottle import request, response, redirect, template
from auth.db import (
    init_auth_db,
    create_user,
    get_user,
    verify_password,
    create_session,
    verify_session,
    count_users,
    get_user_by_id,
)
from auth.policy import home_for
from config import load_config

config = load_config()

# Initialize auth DB on module load
init_auth_db()


def setup_page():
    """First-run setup: create initial admin user if no users exist."""
    if count_users() > 0:
        return redirect("/login")
    return template("templates/setup.html", errors=[], version=config.app_version)


def setup_post():
    """Process first-run setup form."""
    if count_users() > 0:
        return redirect("/login")

    username = request.forms.get("username", "").strip()
    password = request.forms.get("password", "")
    full_name = request.forms.get("full_name", "").strip()

    errors = []
    if not username:
        errors.append("Username required")
    if get_user(username):
        errors.append("Username already exists")
    if not password:
        errors.append("Password required")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if not full_name:
        errors.append("Full name required")

    if errors:
        return template("templates/setup.html", errors=errors, version=config.app_version)

    try:
        user_id = create_user(
            username, password, full_name, "admin", config.db_file.name, "approved"
        )
    except Exception as e:
        return template("templates/setup.html", errors=[str(e)], version=config.app_version)

    # NOTE: redirect() raises Bottle's HTTPResponse, so it must stay outside the
    # try/except above or the redirect would be swallowed and the form re-rendered.
    token = create_session(user_id)
    response.set_cookie("session", token, httponly=True, samesite="Lax", max_age=24*3600, path="/")
    return redirect(home_for(get_user_by_id(user_id)))


def login_page():
    """Login page - redirects authenticated users to their home page or setup."""
    error = request.params.get("error")
    token = request.get_cookie("session")
    if token:
        user_id = verify_session(token)
        if user_id:
            user = get_user_by_id(user_id)
            if user and user["status"] == "approved":
                target = home_for(user)
                # A role missing from the policy has no home; redirecting to
                # /login would loop forever, so clear the session instead.
                if target != "/login":
                    return redirect(target)
                response.delete_cookie("session")
                error = "no_access"

    # Redirect to setup if no users exist
    if count_users() == 0:
        return redirect("/setup")

    messages = {
        "not_approved": "Account not approved. Contact an administrator.",
        "no_access": "Your account cannot open its landing page. Contact an administrator.",
    }
    from config import load_config
    config = load_config()
    return template(
        "templates/login.html",
        error=messages.get(error, error),
        version=config.app_version,
    )


def login_post():
    """Process login form."""
    username = request.forms.get("username", "").strip()
    password = request.forms.get("password", "")
    user = get_user(username)
    if not user or not verify_password(password, user["password_hash"]):
        from config import load_config
        config = load_config()
        return template("templates/login.html", error="Invalid username or password", version=config.app_version)
    if user["status"] != "approved":
        from config import load_config
        config = load_config()
        return template("templates/login.html", error="Account not approved. Contact admin.", version=config.app_version)
    token = create_session(user["id"])
    response.set_cookie("session", token, httponly=True, samesite="Lax", max_age=24*3600, path="/")
    return redirect(home_for(user))


def logout():
    """Logout - clear session cookie."""
    response.delete_cookie("session", path="/")
    return redirect("/login")


def register_routes(app):
    """Register all auth routes with the Bottle app."""
    app.get("/setup")(setup_page)
    app.post("/setup")(setup_post)
    app.get("/login")(login_page)
    app.post("/login")(login_post)
    app.post("/logout")(logout)