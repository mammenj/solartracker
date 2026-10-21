"""Authentication dependencies and authorization decorators."""

import functools

from bottle import redirect, request, response

from auth.db import (
    ensure_user_db,
    get_user_by_id,
    verify_session,
)
from auth.policy import DEFAULT_HOME, can, home_for
from libsolar_sqlite import MeterReadingStore


def _authenticate() -> tuple[dict | None, str | None]:
    """Resolve the session user and attach ``user``/``store`` to the request.

    Returns ``(user, None)`` on success, or ``(None, redirect_target)`` when
    the request must be sent to the login page.
    """
    token = request.get_cookie("session")
    if not token:
        return None, "/login"

    user_id = verify_session(token)
    if not user_id:
        return None, "/login"

    user = get_user_by_id(user_id)
    if not user or user["status"] != "approved":
        response.delete_cookie("session")
        return None, "/login?error=not_approved"

    request.user = user
    request.store = MeterReadingStore(ensure_user_db(user["db_file"]))
    return user, None


def get_current_user() -> dict | None:
    """Get current authenticated user from session cookie."""
    token = request.get_cookie("session")
    if not token:
        return None
    user_id = verify_session(token)
    if not user_id:
        return None
    user = get_user_by_id(user_id)
    if not user or user["status"] != "approved":
        return None
    return user


def get_user_store() -> "MeterReadingStore":
    """Get the MeterReadingStore for the current authenticated user."""
    if not hasattr(request, "store"):
        # Fallback for legacy/compat - uses default DB
        from config import load_config
        config = load_config()
        request.store = MeterReadingStore(config.db_file)
    return request.store


def _redirect(target: str):
    """Redirect that also behaves for htmx requests.

    htmx follows 3xx responses itself and swaps the final body into the
    target, which would paste a whole page into the tab area.  ``HX-Redirect``
    tells htmx to perform a real browser navigation instead.
    """
    if request.headers.get("HX-Request"):
        response.set_header("HX-Redirect", target)
        return ""
    return redirect(target)


def requires(resource: str, action: str):
    """Decorator: require an approved session with ``resource``/``action`` rights.

    Authorization is declared at the route:

        app.get("/admin/users")(requires("admin_users", "view")(handler))

    The actual rules (which role may do what, and the home page used when a
    request is denied) come from ``auth/policy.csv``.
    """

    def decorator(callback):
        @functools.wraps(callback)
        def wrapper(*a, **kw):
            user, login_redirect = _authenticate()
            if login_redirect is not None:
                return _redirect(login_redirect)
            if not can(user, resource, action):
                target = home_for(user)
                # If the role's own landing page is forbidden (or the role has
                # no landing page at all), redirecting there would loop. Drop
                # the session and explain instead.
                if target == DEFAULT_HOME or target == request.path:
                    response.delete_cookie("session")
                    return _redirect("/login?error=no_access")
                return _redirect(target)
            return callback(*a, **kw)

        return wrapper

    return decorator
