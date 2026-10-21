"""Unit tests for the Casbin policy layer (auth/policy.py)."""

import pytest

from auth.policy import MODEL_PATH, Policy


def _policy(tmp_path, text: str = "") -> Policy:
    path = tmp_path / "policy.csv"
    path.write_text(text)
    return Policy(MODEL_PATH, path)


def test_role_permission_matrix(tmp_path):
    policy = _policy(
        tmp_path,
        "p, user, dashboard, view\n"
        "p, admin, admin_users, view\n"
        "p2, user, /app/dashboard\n"
        "p2, admin, /admin/users\n",
    )

    assert policy.can({"role": "user"}, "dashboard", "view") is True
    assert policy.can({"role": "user"}, "admin_users", "view") is False
    assert policy.can({"role": "admin"}, "admin_users", "view") is True
    assert policy.can({"role": "admin"}, "dashboard", "view") is False


def test_anonymous_user_has_no_permissions(tmp_path):
    policy = _policy(tmp_path, "p, user, dashboard, view\n")
    assert policy.can(None, "dashboard", "view") is False


def test_home_for_role(tmp_path):
    policy = _policy(
        tmp_path,
        "p2, user, /app/dashboard\n"
        "p2, admin, /admin/users\n",
    )

    assert policy.home_for({"role": "user"}) == "/app/dashboard"
    assert policy.home_for({"role": "admin"}) == "/admin/users"
    assert policy.home_for({"role": "unknown"}) == "/login"
    assert policy.home_for(None) == "/login"


def test_roles_and_role_permissions(tmp_path):
    policy = _policy(
        tmp_path,
        "p, user, dashboard, view\n"
        "p, user, entry, write\n"
        "p2, user, /app/dashboard\n"
        "p2, viewer, /app/dashboard\n",
    )

    assert policy.roles() == ["user", "viewer"]
    assert policy.role_permissions("user") == [
        ("dashboard", "view"),
        ("entry", "write"),
    ]
    assert policy.role_permissions("viewer") == []


def test_role_needs_db(tmp_path):
    policy = _policy(
        tmp_path,
        "p, user, dashboard, view\n"
        "p, viewer, dashboard, view\n"
        "p, admin, admin_users, view\n",
    )

    assert policy.role_needs_db("user") is True
    assert policy.role_needs_db("viewer") is True
    assert policy.role_needs_db("admin") is False


def test_upsert_role_writes_the_policy_file(tmp_path):
    policy = _policy(tmp_path)

    policy.upsert_role(
        "viewer", [("dashboard", "view"), ("entry", "view")], "/app/dashboard"
    )

    text = (tmp_path / "policy.csv").read_text()
    assert "p, viewer, dashboard, view" in text
    assert "p, viewer, entry, view" in text
    assert "p2, viewer, /app/dashboard" in text
    assert policy.can({"role": "viewer"}, "dashboard", "view") is True
    assert policy.home_for({"role": "viewer"}) == "/app/dashboard"


def test_upsert_role_replaces_existing_grants(tmp_path):
    policy = _policy(tmp_path, "p, viewer, dashboard, view\n")

    policy.upsert_role("viewer", [("entry", "write")], "/app/entry")

    assert policy.role_permissions("viewer") == [("entry", "write")]
    assert policy.can({"role": "viewer"}, "dashboard", "view") is False


def test_upsert_role_rejects_unknown_permission(tmp_path):
    policy = _policy(tmp_path)

    with pytest.raises(ValueError, match="Unknown permission"):
        policy.upsert_role("viewer", [("nope", "view")], "/app/dashboard")


@pytest.mark.parametrize("role", ["", "1viewer", "bad role", "bad/role"])
def test_upsert_role_rejects_invalid_names(tmp_path, role):
    policy = _policy(tmp_path)

    with pytest.raises(ValueError):
        policy.upsert_role(role, [], "/app/dashboard")


def test_upsert_role_normalizes_names_to_lowercase(tmp_path):
    policy = _policy(tmp_path)

    policy.upsert_role("Viewer", [], "/app/dashboard")

    assert policy.roles() == ["viewer"]


@pytest.mark.parametrize(
    "home",
    ["not-a-path", "//evil.example.com", "/app,comma", "/app dashboard", "/app/"],
)
def test_upsert_role_rejects_invalid_home(tmp_path, home):
    policy = _policy(tmp_path)

    with pytest.raises(ValueError, match="Home page"):
        policy.upsert_role("viewer", [], home)


def test_delete_role_removes_grants_and_home(tmp_path):
    policy = _policy(tmp_path)
    policy.upsert_role("viewer", [("dashboard", "view")], "/app/dashboard")

    policy.delete_role("viewer")

    assert "viewer" not in policy.roles()
    assert policy.can({"role": "viewer"}, "dashboard", "view") is False


def test_policy_reloads_edits_from_disk(tmp_path):
    policy = _policy(tmp_path, "p, viewer, dashboard, view\n")
    assert policy.can({"role": "viewer"}, "dashboard", "view") is True

    (tmp_path / "policy.csv").write_text("p, viewer, entry, write\n")
    policy.reload()

    assert policy.can({"role": "viewer"}, "dashboard", "view") is False
    assert policy.can({"role": "viewer"}, "entry", "write") is True
