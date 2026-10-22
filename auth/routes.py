"""Authentication routes: login, logout, setup (Quart/async version)."""

from quart import request, redirect, render_template, make_response
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


async def setup_page():
    """First-run setup: create initial admin user if no users exist."""
    if await count_users() > 0:
        return redirect("/login")
    return await render_template("templates/setup.html", errors=[], version=config.app_version)


async def setup_post():
    """Process first-run setup form."""
    if await count_users() > 0:
        return redirect("/login")

    form = await request.form
    username = form.get("username", "").strip()
    password = form.get("password", "")
    full_name = form.get("full_name", "").strip()

    errors = []
    if not username:
        errors.append("Username required")
    if await get_user(username):
        errors.append("Username already exists")
    if not password:
        errors.append("Password required")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if not full_name:
        errors.append("Full name required")

    if errors:
        return await render_template("templates/setup.html", errors=errors, version=config.app_version)

    try:
        user_id = await create_user(
            username, password, full_name, "admin", config.db_file.name, "approved"
        )
    except Exception as e:
        return await render_template("templates/setup.html", errors=[str(e)], version=config.app_version)

    # NOTE: redirect() raises Quart's HTTPResponse, so it must stay outside the
    # try/except above or the redirect would be swallowed and the form re-rendered.
    token = create_session(user_id)
    resp = await make_response(redirect(home_for(await get_user_by_id(user_id))))
    resp.set_cookie("session", token, httponly=True, samesite="Lax", max_age=24*3600, path="/")
    return resp


async def login_page():
    """Login page - redirects authenticated users to their home page or setup."""
    error = request.args.get("error")
    token = request.cookies.get("session")
    if token:
        user_id = verify_session(token)
        if user_id:
            user = await get_user_by_id(user_id)
            if user and user["status"] == "approved":
                target = home_for(user)
                # A role missing from the policy has no home; redirecting to
                # /login would loop forever, so clear the session instead.
                if target != "/login":
                    return redirect(target)
                resp = await make_response(redirect("/login"))
                resp.delete_cookie("session")
                return resp

    # Redirect to setup if no users exist
    if await count_users() == 0:
        return redirect("/setup")

    messages = {
        "not_approved": "Account not approved. Contact an administrator.",
        "no_access": "Your account cannot open its landing page. Contact an administrator.",
    }
    return await render_template(
        "templates/login.html",
        error=messages.get(error, error),
        version=config.app_version,
    )


async def login_post():
    """Process login form."""
    form = await request.form
    username = form.get("username", "").strip()
    password = form.get("password", "")
    user = await get_user(username)
    if not user or not verify_password(password, user["password_hash"]):
        return await render_template("templates/login.html", error="Invalid username or password", version=config.app_version)
    if user["status"] != "approved":
        return await render_template("templates/login.html", error="Account not approved. Contact admin.", version=config.app_version)
    token = create_session(user["id"])
    resp = await make_response(redirect(home_for(user)))
    resp.set_cookie("session", token, httponly=True, samesite="Lax", max_age=24*3600, path="/")
    return resp


async def logout():
    """Logout - clear session cookie."""
    resp = await make_response(redirect("/login"))
    resp.delete_cookie("session", path="/")
    return resp


def register_routes(app):
    """Register all auth routes with the Quart app."""
    app.add_url_rule("/setup", view_func=setup_page, methods=["GET"])
    app.add_url_rule("/setup", view_func=setup_post, methods=["POST"])
    app.add_url_rule("/login", view_func=login_page, methods=["GET"])
    app.add_url_rule("/login", view_func=login_post, methods=["POST"])
    app.add_url_rule("/logout", view_func=logout, methods=["POST"])