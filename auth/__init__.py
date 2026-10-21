"""Auth package initialization."""

from auth.deps import (
    requires,
    get_user_store,
    get_current_user,
)
from auth.routes import register_routes
from auth.policy import (
    can,
    home_for,
    reload_policy,
    roles,
)
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
    count_users_by_role,
    count_users_with_role,
    ensure_user_db,
)

__all__ = [
    "requires",
    "get_user_store",
    "get_current_user",
    "can",
    "home_for",
    "reload_policy",
    "roles",
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
    "count_users_by_role",
    "count_users_with_role",
    "ensure_user_db",
]
