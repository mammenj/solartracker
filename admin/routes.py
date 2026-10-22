"""Admin routes: users and roles/permissions (Quart version)."""

from quart import request, render_template
from auth.deps import requires
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


async def admin_users():
    params = await get_admin_users_params()
    params["current_user_id"] = request.user["id"]

    # Check if htmx request (for partial loads via htmx)
    if request.headers.get("HX-Request"):
        return await render_template(
            "templates/admin_users.html",
            **params,
            version=config.app_version,
            db_name=config.db_file.name,
        )

    return await render_template(
        "templates/base.html",
        version=config.app_version,
        db_name=config.db_file.name,
        user=request.user,
        initial_tab="admin",
        **params,
    )


async def admin_users_partial():
    """Partial render for htmx tab navigation."""
    params = await get_admin_users_params()
    params["current_user_id"] = request.user["id"]
    return await render_template(
        "templates/admin_users.html",
        **params,
        version=config.app_version,
        db_name=config.db_file.name,
    )


def register_routes(app):
    """Register all admin routes with the Quart app."""
    # Users
    app.add_url_rule("/admin/users", view_func=requires("admin_users", "view")(admin_users), methods=["GET"])
    app.add_url_rule("/admin/users/partial", view_func=requires("admin_users", "view")(admin_users_partial), methods=["GET"])
    app.add_url_rule("/admin/users/new", view_func=requires("admin_users", "view")(admin_user_new), methods=["GET"])
    app.add_url_rule("/admin/users", view_func=requires("admin_users", "create")(admin_user_create), methods=["POST"])
    app.add_url_rule("/admin/users/<int:user_id>/edit", view_func=requires("admin_users", "update")(admin_user_edit), methods=["GET"])
    app.add_url_rule("/admin/users/<int:user_id>", view_func=requires("admin_users", "update")(admin_user_update), methods=["POST"])
    app.add_url_rule("/admin/users/<int:user_id>/delete", view_func=requires("admin_users", "delete")(admin_user_delete), methods=["POST"])

    # Roles & permissions
    app.add_url_rule("/admin/roles", view_func=requires("admin_policy", "view")(admin_roles), methods=["GET"])
    app.add_url_rule("/admin/roles/partial", view_func=requires("admin_policy", "view")(admin_roles_partial), methods=["GET"])
    app.add_url_rule("/admin/roles/new", view_func=requires("admin_policy", "view")(admin_role_new), methods=["GET"])
    app.add_url_rule("/admin/roles", view_func=requires("admin_policy", "update")(admin_role_create), methods=["POST"])
    app.add_url_rule("/admin/roles/<string:role>/edit", view_func=requires("admin_policy", "view")(admin_role_edit), methods=["GET"])
    app.add_url_rule("/admin/roles/<string:role>", view_func=requires("admin_policy", "update")(admin_role_update), methods=["POST"])
    app.add_url_rule("/admin/roles/<string:role>/delete", view_func=requires("admin_policy", "update")(admin_role_delete), methods=["POST"])