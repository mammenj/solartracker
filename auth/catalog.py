"""Catalogue of permissions the application knows about.

The catalogue describes *what exists* (it is tied to the routes in code). The
file ``auth/policy.csv`` decides *who may use it*.
"""

from __future__ import annotations

#: resource -> {action: human label}
PERMISSIONS: dict[str, dict[str, str]] = {
    "dashboard": {
        "view": "View dashboard",
        "chart": "View energy charts",
    },
    "entry": {
        "view": "View data entry",
        "write": "Add / edit readings",
    },
    "admin_users": {
        "view": "View users",
        "create": "Create users",
        "update": "Edit users",
        "delete": "Delete users",
    },
    "admin_policy": {
        "view": "View roles & permissions",
        "update": "Edit roles & permissions",
    },
}

#: Display order (and labels) for resources in the admin UI.
RESOURCE_LABELS: dict[str, str] = {
    "dashboard": "Dashboard",
    "entry": "Data Entry",
    "admin_users": "User Management",
    "admin_policy": "Roles & Permissions",
}

#: Permissions that imply the role reads/writes meter readings and therefore
#: needs its own database file.
READING_PERMISSIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("dashboard", "view"),
        ("dashboard", "chart"),
        ("entry", "view"),
        ("entry", "write"),
    }
)


#: Known landing pages -> the permission needed to open them. Used by the admin
#: UI to catch a role whose home page it could never reach.
HOME_PERMISSIONS: dict[str, tuple[str, str]] = {
    "/": ("dashboard", "view"),
    "/app/dashboard": ("dashboard", "view"),
    "/app/entry": ("entry", "view"),
    "/admin/users": ("admin_users", "view"),
    "/admin/roles": ("admin_policy", "view"),
}


def home_requires(home: str) -> tuple[str, str] | None:
    """Permission required to open ``home``, or None for unknown pages."""
    return HOME_PERMISSIONS.get(home)


def is_known_permission(resource: str, action: str) -> bool:
    """Return True when the catalogue defines this resource/action pair."""
    return action in PERMISSIONS.get(resource, {})


def permission_label(resource: str, action: str) -> str:
    """Human readable label for a permission (falls back to 'resource.action')."""
    return PERMISSIONS.get(resource, {}).get(action, f"{resource}.{action}")


def permission_groups() -> list[dict]:
    """Grouped catalogue, ready for rendering in a template."""
    groups = []
    for resource, actions in PERMISSIONS.items():
        groups.append(
            {
                "resource": resource,
                "label": RESOURCE_LABELS.get(resource, resource.replace("_", " ").title()),
                "permissions": [
                    {
                        "value": f"{resource}:{action}",
                        "action": action,
                        "label": label,
                    }
                    for action, label in actions.items()
                ],
            }
        )
    return groups


def needs_readings_db(permissions) -> bool:
    """True when any granted permission requires a readings database."""
    return bool(set(permissions) & READING_PERMISSIONS)
