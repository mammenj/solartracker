"""Admin routes: users and roles/permissions."""

from bottle import request, template

from auth import requires
from admin.services import (
    admin_role_create,
    admin_role_delete,
    admin_role_edit,
    admin_role_new,
    admin_role_update,
    admin_roles,
    admin_roles_partial,
    admin_user_create,
    admin_user_delete,
    admin_user_edit,
    admin_user_new,
    admin_user_update,
    get_admin_users_params,
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
    # Users
    app.get("/admin/users")(requires("admin_users", "view")(admin_users))
    app.get("/admin/users/partial")(requires("admin_users", "view")(admin_users_partial))
    app.get("/admin/users/new")(requires("admin_users", "view")(admin_user_new))
    app.post("/admin/users")(requires("admin_users", "create")(admin_user_create))
    app.get("/admin/users/<user_id:int>/edit")(requires("admin_users", "update")(admin_user_edit))
    app.post("/admin/users/<user_id:int>")(requires("admin_users", "update")(admin_user_update))
    app.post("/admin/users/<user_id:int>/delete")(requires("admin_users", "delete")(admin_user_delete))

    # Roles & permissions
    app.get("/admin/roles")(requires("admin_policy", "view")(admin_roles))
    app.get("/admin/roles/partial")(requires("admin_policy", "view")(admin_roles_partial))
    app.get("/admin/roles/new")(requires("admin_policy", "view")(admin_role_new))
    app.post("/admin/roles")(requires("admin_policy", "update")(admin_role_create))
    app.get("/admin/roles/<role>/edit")(requires("admin_policy", "view")(admin_role_edit))
    app.post("/admin/roles/<role>")(requires("admin_policy", "update")(admin_role_update))
    app.post("/admin/roles/<role>/delete")(requires("admin_policy", "update")(admin_role_delete))
