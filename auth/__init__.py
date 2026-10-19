"""Auth package initialization."""

from auth.deps import (
    require_auth,
    get_user_store,
    get_current_user,
)
from auth.routes import register_routes
from auth.db import (
    init_auth_db,
    create_user,
    get_user,
    get_user_by_id,
    verify_password,
    create_session,
    verify_session,
    list_users,
    update_user,
    delete_user,
    count_users,
    ensure_user_db,
)

__all__ = [
    "require_auth",
    "get_user_store",
    "get_current_user",
    "register_routes",
    "init_auth_db",
    "create_user",
    "get_user",
    "get_user_by_id",
    "verify_password",
    "create_session",
    "verify_session",
    "list_users",
    "update_user",
    "delete_user",
    "count_users",
    "ensure_user_db",
]