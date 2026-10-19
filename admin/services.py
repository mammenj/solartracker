"""Admin services for user management and utilities."""

from math import ceil
from bottle import request, template, redirect, response
from auth.db import list_users, get_user_by_id, update_user, delete_user, create_user, get_user
from auth import require_auth


def sortable_headers(sort: str, order: str, fields: list[tuple[str, str]]) -> list[dict]:
    """
    Build sortable column-header metadata for htmx-clickable <th> elements.
    """
    headers = []
    for key, label in fields:
        active = key == sort
        if active:
            next_order = "asc" if order == "desc" else "desc"
        else:
            # Date-type columns default to descending (newest first),
            # numeric columns to ascending.
            next_order = "desc" if key == "date" or key == "start" else "asc"
        headers.append(
            {
                "key": key,
                "label": label,
                "active": active,
                "arrow": ("↓" if order == "desc" else "↑") if active else "",
                "next_order": next_order,
            }
        )
    return headers


def get_admin_users_params():
    """Get parameters for admin users list with paging and sorting."""
    from math import ceil
    try:
        page = max(1, int(request.params.get("page", "1")))
    except (ValueError, TypeError):
        page = 1
    sort = request.params.get("sort", "username")
    order = request.params.get("order", "asc")
    users, total = list_users(page, 10, sort, order)
    total_pages = max(1, ceil(total / 10)) if total else 1
    page = min(page, total_pages)

    headers = sortable_headers(sort, order, [
        ("username", "Username"),
        ("full_name", "Full Name"),
        ("role", "Role"),
        ("status", "Status"),
        ("created_at", "Created"),
    ])

    return {
        "users": users,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "sort": sort,
        "order": order,
        "headers": headers,
    }


def admin_user_new():
    from config import load_config
    config = load_config()
    return template("templates/admin_user_form.html", user=None, errors=[], version=config.app_version, db_name=config.db_file.name)


def admin_user_create():
    from config import load_config
    config = load_config()
    username = request.forms.get("username", "").strip()
    password = request.forms.get("password", "")
    full_name = request.forms.get("full_name", "").strip()
    role = request.forms.get("role", "user")
    status = request.forms.get("status", "pending")
    db_file = request.forms.get("db_file", "").strip()

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
    if role not in ("admin", "user"):
        errors.append("Invalid role")
    if status not in ("pending", "approved", "disabled"):
        errors.append("Invalid status")
    if role == "user" and not db_file:
        errors.append("Database file required")

    if errors:
        return template("templates/admin_user_form.html", user=None, errors=errors, version=config.app_version, db_name=config.db_file.name)

    try:
        create_user(username, password, full_name, role, db_file or "", status)
    except Exception as e:
        return template("templates/admin_user_form.html", user=None, errors=[str(e)], version=config.app_version, db_name=config.db_file.name)

    return redirect("/admin/users")


def admin_user_edit(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        return redirect("/admin/users")
    from config import load_config
    config = load_config()
    return template("templates/admin_user_form.html", user=user, errors=[], version=config.app_version, db_name=config.db_file.name)


def admin_user_update(user_id: int):
    from config import load_config
    config = load_config()
    user = get_user_by_id(user_id)
    if not user:
        return redirect("/admin/users")

    full_name = request.forms.get("full_name", "").strip()
    role = request.forms.get("role", "user")
    status = request.forms.get("status", "pending")
    db_file = request.forms.get("db_file", "").strip()

    errors = []
    if not full_name:
        errors.append("Full name required")
    if role not in ("admin", "user"):
        errors.append("Invalid role")
    if status not in ("pending", "approved", "disabled"):
        errors.append("Invalid status")
    if role == "user" and not db_file:
        errors.append("Database file required")

    if errors:
        return template("templates/admin_user_form.html", user=user, errors=errors, version=config.app_version, db_name=config.db_file.name)

    # Only pass db_file for user role
    update_kwargs = {"full_name": full_name, "role": role, "status": status}
    if role == "user":
        update_kwargs["db_file"] = db_file
    update_user(user_id, **update_kwargs)
    return redirect("/admin/users")


def admin_user_delete(user_id: int):
    """Delete a user. Prevents deleting self."""
    current_user_id = request.user["id"]
    if user_id == current_user_id:
        response.status = 400
        return "Cannot delete yourself"
    delete_user(user_id)
    return redirect("/admin/users")