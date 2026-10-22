"""Authentication dependencies and authorization decorators."""

import functools

from quart import redirect, request, make_response

from auth.db import (
    ensure_user_db,
    get_user_by_id,
    verify_session,
)
from auth.policy import DEFAULT_HOME, home_for
from libsolar_sqlite import MeterReadingStore


# Casbin is an in-memory policy lookup (microseconds), so it is called directly
# rather than offloaded to a thread.
def can(user: dict | None, resource: str, action: str) -> bool:
    """Check whether ``user`` may perform ``action`` on ``resource``."""
    from auth.policy import can as can_sync
    return can_sync(user, resource, action)


async def _authenticate() -> tuple[dict | None, str | None]:
    """Resolve the session user and attach ``user``/``store`` to the request.

    Returns ``(user, None)`` on success, or ``(None, redirect_target)`` when
    the request must be sent to the login page.
    """
    token = request.cookies.get("session")
    if not token:
        return None, "/login"

    user_id = verify_session(token)
    if not user_id:
        return None, "/login"

    user = await get_user_by_id(user_id)
    if not user or user["status"] != "approved":
        # The session is stale (deleted user or no longer approved); expire it.
        request.stale_session = True
        return None, "/login?error=not_approved"

    request.user = user
    request.store = MeterReadingStore(await ensure_user_db(user["db_file"]))
    return user, None


async def get_current_user() -> dict | None:
    """Get current authenticated user from session cookie."""
    token = request.cookies.get("session")
    if not token:
        return None
    user_id = verify_session(token)
    if not user_id:
        return None
    user = await get_user_by_id(user_id)
    if not user or user["status"] != "approved":
        return None
    return user


async def get_user_store() -> "MeterReadingStore":
    """Get the MeterReadingStore for the current authenticated user.

    ``requires()`` attaches the store while authenticating, so any handler
    reached through it can rely on ``request.store`` being present.
    """
    return request.store


async def _redirect(target: str):
    """Redirect that also behaves for htmx requests.

    htmx follows 3xx responses itself and swaps the final body into the
    target, which would paste a whole page into the tab area.  ``HX-Redirect``
    tells htmx to perform a real browser navigation instead.
    """
    if request.headers.get("HX-Request"):
        resp = await make_response("", 200)
        resp.headers["HX-Redirect"] = target
        return resp
    resp = redirect(target)
    if getattr(request, "stale_session", False):
        resp.delete_cookie("session")
    return resp


def requires(resource: str, action: str):
    """Decorator: require an approved session with ``resource``/``action`` rights.

    Authorization is declared at the route:

        @app.route("/admin/users")
        @requires("admin_users", "view")
        async def handler(): ...

    The actual rules (which role may do what, and the home page used when a
    request is denied) come from ``auth/policy.csv``.
    """

    def decorator(callback):
        @functools.wraps(callback)
        async def wrapper(*a, **kw):
            user, login_redirect = await _authenticate()
            if login_redirect is not None:
                return await _redirect(login_redirect)
            if not can(user, resource, action):
                target = home_for(user)
                # If the role's own landing page is forbidden (or the role has
                # no landing page at all), redirecting there would loop. Drop
                # the session and explain instead.
                if target == DEFAULT_HOME or target == request.path:
                    resp = await _redirect("/login?error=no_access")
                    resp.delete_cookie("session")
                    return resp
                return await _redirect(target)
            return await callback(*a, **kw)

        return wrapper

    return decorator