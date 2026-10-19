"""Authentication dependencies and decorators."""

import functools
from bottle import request, response, redirect
from auth.db import (
    verify_session,
    get_user_by_id,
    verify_password,
    create_session,
    count_users,
    ensure_user_db,
)
from libsolar_sqlite import MeterReadingStore
from config import load_config

config = load_config()


def get_current_user() -> dict | None:
    """Get current authenticated user from session cookie."""
    token = request.get_cookie("session")
    if not token:
        return None
    # Note: verify_session is imported from auth but we need the user_id
    # We'll use the same pattern as require_auth
    from auth import verify_session
    user_id = verify_session(token)
    if not user_id:
        return None
    from auth import get_user_by_id
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


def require_auth(roles: list[str] | None = None):
    """Decorator: validate session, check role, inject user + store into request."""
    def decorator(callback):
        @functools.wraps(callback)
        def wrapper(*a, **kw):
            token = request.get_cookie("session")
            if not token:
                return redirect("/login")
            from auth import verify_session
            user_id = verify_session(token)
            if not user_id:
                return redirect("/login")
            from auth import get_user_by_id
            user = get_user_by_id(user_id)
            if not user or user["status"] != "approved":
                response.delete_cookie("session")
                return redirect("/login?error=not_approved")
            if roles and user["role"] not in roles:
                response.status = 403
                return "Forbidden: insufficient role"
            # Attach user and their store to request
            request.user = user
            request.store = MeterReadingStore(ensure_user_db(user["db_file"]))
            return callback(*a, **kw)
        return wrapper
    return decorator