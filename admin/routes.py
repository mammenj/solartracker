"""Admin routes: /admin/users/*, /admin/users/partial"""

from bottle import request, redirect, template
from auth import require_auth
from admin.services import (
    admin_user_new,
    admin_user_create,
    admin_user_edit,
    admin_user_update,
    admin_user_delete,
    get_admin_users_params,
    sortable_headers,
)
from config import load_config

config = load_config()


def admin_users():
    params = get_admin_users_params()

    # Check if htmx request (for partial loads via htmx)
    if request.headers.get("HX-Request"):
        return template(
            "templates/admin_users.html",
            **params,
            version=config.app_version,
            db_name=config.db_file.name,
        )

    return template(
        "templates/base.html",
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        initial_tab="admin",
        **params,
    )


def admin_users_partial():
    """Partial render for htmx tab navigation."""
    params = get_admin_users_params()
    return template(
        "templates/admin_users.html",
        **params,
        version=config.app_version,
        db_name=config.db_file.name,
    )


def register_routes(app):
    """Register all admin routes with the Bottle app."""
    from auth import require_auth
    app.get("/admin/users")(require_auth(["admin"])(admin_users))
    app.get("/admin/users/partial")(require_auth(["admin"])(admin_users_partial))
    app.get("/admin/users/new")(require_auth(["admin"])(admin_user_new))
    app.post("/admin/users")(require_auth(["admin"])(admin_user_create))
    app.get("/admin/users/<user_id:int>/edit")(require_auth(["admin"])(admin_user_edit))
    app.post("/admin/users/<user_id:int>")(require_auth(["admin"])(admin_user_update))
    app.post("/admin/users/<user_id:int>/delete")(require_auth(["admin"])(admin_user_delete))