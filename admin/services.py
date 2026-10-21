"""Admin services for user and role management."""

from math import ceil

from bottle import request, template, redirect, response

from auth.catalog import (
    home_requires,
    is_known_permission,
    needs_readings_db,
    permission_groups,
    permission_label,
)
from auth.db import (
    STATUSES,
    count_users_by_role,
    count_users_with_role,
    create_user,
    delete_user,
    get_user,
    get_user_by_id,
    list_users,
    update_user,
)
from auth.policy import get_policy
from config import load_config

config = load_config()


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
    try:
        page = max(1, int(request.params.get("page", "1")))
    except (ValueError, TypeError):
        page = 1
    sort = request.params.get("sort", "username")
    order = request.params.get("order", "asc")
    users, total = list_users(page, 10, sort, order)
    total_pages = max(1, ceil(total / 10)) if total else 1
    page = min(page, total_pages)

    headers = sortable_headers(
        sort,
        order,
        [
            ("username", "Username"),
            ("full_name", "Full Name"),
            ("role", "Role"),
            ("status", "Status"),
            ("created_at", "Created"),
        ],
    )

    return {
        "users": users,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "sort": sort,
        "order": order,
        "headers": headers,
    }


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
def _role_options() -> list[dict]:
    """Roles for the user form, annotated with whether they need a database."""
    policy = get_policy()
    counts = count_users_by_role()
    return [
        {
            "name": role,
            "needs_db": policy.role_needs_db(role),
            "user_count": counts.get(role, 0),
        }
        for role in policy.roles()
    ]


def _user_form_context(user, errors):
    options = _role_options()
    names = [option["name"] for option in options]
    if user:
        selected_role = user["role"]
    elif "admin" in names:
        selected_role = "admin"
    else:
        selected_role = names[0] if names else ""

    return {
        "user": user,
        "errors": errors,
        "roles": options,
        "selected_role": selected_role,
        "needs_db_roles": [
            option["name"] for option in options if option["needs_db"]
        ],
        "version": config.app_version,
        "db_name": config.db_file.name,
    }


def admin_user_new():
    return template("templates/admin_user_form.html", **_user_form_context(None, []))


def admin_user_create():
    username = request.forms.get("username", "").strip()
    password = request.forms.get("password", "")
    full_name = request.forms.get("full_name", "").strip()
    role = request.forms.get("role", "user")
    status = request.forms.get("status", "pending")
    db_file = request.forms.get("db_file", "").strip()

    policy = get_policy()
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
    if role not in policy.roles():
        errors.append("Invalid role")
    if status not in STATUSES:
        errors.append("Invalid status")
    if not errors and policy.role_needs_db(role) and not db_file:
        errors.append("Database file required")

    if errors:
        return template(
            "templates/admin_user_form.html", **_user_form_context(None, errors)
        )

    # Only roles that read meter data carry a database file.
    db_value = db_file if policy.role_needs_db(role) else ""
    try:
        create_user(username, password, full_name, role, db_value, status)
    except Exception as e:
        return template(
            "templates/admin_user_form.html", **_user_form_context(None, [str(e)])
        )

    return redirect("/admin/users")


def admin_user_edit(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        return redirect("/admin/users")
    return template(
        "templates/admin_user_form.html", **_user_form_context(user, [])
    )


def admin_user_update(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        return redirect("/admin/users")

    full_name = request.forms.get("full_name", "").strip()
    role = request.forms.get("role", "user")
    status = request.forms.get("status", "pending")
    db_file = request.forms.get("db_file", "").strip()

    policy = get_policy()
    errors = []
    if not full_name:
        errors.append("Full name required")
    if role not in policy.roles():
        errors.append("Invalid role")
    if status not in STATUSES:
        errors.append("Invalid status")
    if user_id == request.user["id"]:
        if role != request.user["role"]:
            errors.append("You cannot change your own role")
        if status != "approved":
            errors.append("You cannot disable your own account")
    if not errors and policy.role_needs_db(role) and not db_file:
        errors.append("Database file required")

    if errors:
        return template(
            "templates/admin_user_form.html",
            **_user_form_context(user, errors),
        )

    update_kwargs = {"full_name": full_name, "role": role, "status": status}
    # Only roles that read meter data carry a database file; leave an existing
    # value alone when moving to a role that does not need one.
    if policy.role_needs_db(role):
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


# ---------------------------------------------------------------------------
# Roles & permissions
# ---------------------------------------------------------------------------
def _roles_context() -> dict:
    policy = get_policy()
    counts = count_users_by_role()
    roles = []
    for name in policy.roles():
        permissions = policy.role_permissions(name)
        roles.append(
            {
                "name": name,
                "home": policy.home_for_role(name),
                "permissions": [
                    {
                        "resource": resource,
                        "action": action,
                        "label": permission_label(resource, action),
                    }
                    for resource, action in permissions
                ],
                "user_count": counts.get(name, 0),
                "needs_db": needs_readings_db(permissions),
            }
        )
    return {"roles": roles}


def admin_roles():
    ctx = _roles_context()
    ctx.update(version=config.app_version, db_name=config.db_file.name)

    if request.headers.get("HX-Request"):
        return template("templates/admin_roles.html", **ctx)

    return template(
        "templates/base.html",
        initial_tab="admin_roles",
        user=request.user,
        **ctx,
    )


def admin_roles_partial():
    """Partial render for htmx tab navigation."""
    ctx = _roles_context()
    return template("templates/admin_roles.html", **ctx)


def _role_permissions_from_form() -> list[tuple[str, str]]:
    values = request.forms.getall("permissions") or []
    grants = []
    for value in values:
        resource, sep, action = value.partition(":")
        if sep:
            grants.append((resource, action))
    return grants


def _validate_grants(grants) -> list[str]:
    errors = []
    for resource, action in grants:
        if not is_known_permission(resource, action):
            errors.append(f"Unknown permission: {resource}.{action}")
    return errors


def _validate_home(home: str, grants) -> list[str]:
    """Reject a home page the role would not be allowed to open."""
    required = home_requires(home)
    if required and required not in set(grants):
        resource, action = required
        return [
            f"Home page {home} requires the "
            f"'{permission_label(resource, action)}' permission."
        ]
    return []


def _role_form_context(
    *,
    role: str | None = None,
    role_name: str = "",
    home: str = "/app/dashboard",
    selected=None,
    errors=None,
) -> dict:
    return {
        "role": role,
        "role_name": role_name or role or "",
        "home": home,
        "groups": permission_groups(),
        "selected": set(selected or ()),
        "errors": errors or [],
        "version": config.app_version,
        "db_name": config.db_file.name,
    }


def admin_role_new():
    return template("templates/admin_role_form.html", **_role_form_context())


def admin_role_create():
    policy = get_policy()
    role = request.forms.get("role", "").strip().lower()
    home = request.forms.get("home", "").strip() or "/app/dashboard"
    grants = _role_permissions_from_form()
    selected = {f"{resource}:{action}" for resource, action in grants}

    errors = []
    if not role:
        errors.append("Role name required")
    elif role in policy.roles():
        errors.append("Role already exists")
    errors.extend(_validate_grants(grants))
    if not home.startswith("/"):
        errors.append("Home page must start with '/'")
    else:
        errors.extend(_validate_home(home, grants))

    if errors:
        return template(
            "templates/admin_role_form.html",
            **_role_form_context(
                role_name=role, home=home, selected=selected, errors=errors
            ),
        )

    try:
        policy.upsert_role(role, grants, home)
    except ValueError as e:
        return template(
            "templates/admin_role_form.html",
            **_role_form_context(
                role_name=role, home=home, selected=selected, errors=[str(e)]
            ),
        )
    return redirect("/admin/roles")


def admin_role_edit(role: str):
    policy = get_policy()
    if role not in policy.roles():
        return redirect("/admin/roles")
    return template(
        "templates/admin_role_form.html",
        **_role_form_context(
            role=role,
            home=policy.home_for_role(role),
            selected={f"{r}:{a}" for r, a in policy.role_permissions(role)},
        ),
    )


def admin_role_update(role: str):
    policy = get_policy()
    if role not in policy.roles():
        return redirect("/admin/roles")

    home = request.forms.get("home", "").strip() or "/app/dashboard"
    grants = _role_permissions_from_form()
    selected = {f"{resource}:{action}" for resource, action in grants}

    errors = _validate_grants(grants)
    if not home.startswith("/"):
        errors.append("Home page must start with '/'")
    else:
        errors.extend(_validate_home(home, grants))
    if role == request.user["role"] and not {
        ("admin_policy", "view"),
        ("admin_policy", "update"),
    }.issubset(set(grants)):
        errors.append(
            "You cannot remove your own ability to manage roles & permissions."
        )

    if errors:
        return template(
            "templates/admin_role_form.html",
            **_role_form_context(
                role=role, home=home, selected=selected, errors=errors
            ),
        )

    try:
        policy.upsert_role(role, grants, home)
    except ValueError as e:
        return template(
            "templates/admin_role_form.html",
            **_role_form_context(
                role=role, home=home, selected=selected, errors=[str(e)]
            ),
        )
    return redirect("/admin/roles")


def admin_role_delete(role: str):
    if role == request.user["role"]:
        response.status = 400
        return "Cannot delete the role you are currently using"
    if count_users_with_role(role) > 0:
        response.status = 400
        return "Cannot delete a role that still has users"
    get_policy().delete_role(role)
    return redirect("/admin/roles")
