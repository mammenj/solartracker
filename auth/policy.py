"""Declarative authorization backed by Casbin.

The policy is not hard-coded here: it lives in two files next to this module.

* ``auth/model.conf`` - the Casbin model (the shape of the policy).
* ``auth/policy.csv`` - the editable policy: which role may perform which
  action, and where each role's "home" page is.

Change ``policy.csv`` by hand, or through **Admin -> Roles & Permissions**
(which writes the same file atomically and reloads it).
"""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path

import casbin

from auth.catalog import is_known_permission, needs_readings_db

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.conf"
POLICY_PATH = BASE_DIR / "policy.csv"

#: Fallback redirect when a role has no landing page in ``policy.csv``.
DEFAULT_HOME = "/login"

ROLE_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

#: A safe in-app path: one leading slash and no empty segments, so it cannot
#: become a protocol-relative open redirect (``//host``). Keeping it simple
#: also means the path can be written to the CSV policy safely.
HOME_RE = re.compile(r"^/(?:[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*)?$")

POLICY_HEADER = """\
# Solar Tracker authorization policy (Casbin).
#
# Edit this file to change who may do what. Admin -> Roles & Permissions
# writes this same file and reloads it automatically.
#
#   p, <role>, <resource>, <action>   grant a permission to a role
#   p2, <role>, <home-path>           landing page for that role
#
# Roles are free-form here; assign them to users on Admin -> Users.
"""


class Policy:
    """Wrapper around a Casbin enforcer plus role landing pages."""

    def __init__(
        self,
        model_path: Path | str | None = None,
        policy_path: Path | str | None = None,
    ) -> None:
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.policy_path = Path(policy_path) if policy_path else POLICY_PATH
        self._enforcer: casbin.Enforcer | None = None
        self._homes: dict[str, str] = {}
        self._lock = threading.RLock()
        #: Memoised ``(role, resource, action) -> bool`` decisions. Casbin's
        #: ``enforce`` evaluates the matcher expression in Python and costs
        #: ~100us per call, while a page render asks the same handful of
        #: questions repeatedly. Cleared on every (re)load, which is the single
        #: point where the underlying grants can change.
        self._can_cache: dict[tuple[str, str, str], bool] = {}
        self.reload()

    # -- loading / saving --------------------------------------------------
    def reload(self) -> None:
        """(Re)load model + policy from disk."""
        with self._lock:
            self._enforcer = casbin.Enforcer(
                str(self.model_path), str(self.policy_path)
            )
            self._homes = {
                role: home for role, home in self._enforcer.get_named_policy("p2")
            }
            # Grants may have changed; drop every memoised decision.
            self._can_cache.clear()

    def _save(self) -> None:
        """Write the current policy back to ``policy.csv`` atomically."""
        lines = [POLICY_HEADER.rstrip(), ""]

        grants = sorted(self._enforcer.get_policy())
        if grants:
            lines.append("# Permission grants")
            lines.extend(
                f"p, {role}, {resource}, {action}"
                for role, resource, action in grants
            )
            lines.append("")

        homes = sorted(self._enforcer.get_named_policy("p2"))
        if homes:
            lines.append("# Landing pages")
            lines.extend(f"p2, {role}, {home}" for role, home in homes)

        text = "\n".join(lines).rstrip() + "\n"
        tmp = self.policy_path.with_name(self.policy_path.name + ".tmp")
        tmp.write_text(text)
        os.replace(tmp, self.policy_path)
        self.reload()

    # -- queries -----------------------------------------------------------
    def can(self, user: dict | None, resource: str, action: str) -> bool:
        """Return True when ``user``'s role may perform ``action`` on ``resource``.

        Results are memoised per ``(role, resource, action)`` because Casbin's
        ``enforce`` is comparatively expensive and a single page render asks the
        same questions many times. The cache is cleared on every reload.
        """
        if not user:
            return False
        key = (user["role"], resource, action)
        cached = self._can_cache.get(key)
        if cached is not None:
            return cached
        decision = bool(self._enforcer.enforce(key[0], resource, action))
        self._can_cache[key] = decision
        return decision

    def home_for(self, user: dict | None) -> str:
        """Return the landing page declared for ``user``'s role."""
        if not user:
            return DEFAULT_HOME
        return self._homes.get(user["role"], DEFAULT_HOME)

    def home_for_role(self, role: str) -> str:
        return self._homes.get(role, DEFAULT_HOME)

    def roles(self) -> list[str]:
        """Every role that appears in the policy, sorted."""
        names = set(self._homes)
        names |= {role for role, _resource, _action in self._enforcer.get_policy()}
        return sorted(names)

    def role_permissions(self, role: str) -> list[tuple[str, str]]:
        """All (resource, action) grants for ``role``."""
        return sorted(
            (resource, action)
            for grant_role, resource, action in self._enforcer.get_policy()
            if grant_role == role
        )

    def role_needs_db(self, role: str) -> bool:
        """True when the role reads or writes meter readings."""
        return needs_readings_db(self.role_permissions(role))

    # -- mutations ---------------------------------------------------------
    def upsert_role(self, role: str, permissions, home: str) -> None:
        """Create/update a role: replace its grants and landing page."""
        role = (role or "").strip().lower()
        if not ROLE_NAME_RE.match(role):
            raise ValueError(
                "Role name must start with a letter and use only a-z, 0-9, '_' or '-'."
            )

        grants = set()
        for resource, action in permissions:
            if not is_known_permission(resource, action):
                raise ValueError(f"Unknown permission: {resource}.{action}")
            grants.add((resource, action))

        home = (home or "").strip() or DEFAULT_HOME
        if not HOME_RE.match(home):
            raise ValueError(
                "Home page must be a plain path such as '/app/dashboard'."
            )

        with self._lock:
            self._enforcer.remove_filtered_policy(0, role)
            self._enforcer.remove_filtered_named_policy("p2", 0, role)
            for resource, action in sorted(grants):
                self._enforcer.add_policy(role, resource, action)
            self._enforcer.add_named_policy("p2", role, home)
            self._save()

    def delete_role(self, role: str) -> None:
        """Remove a role and all of its grants."""
        with self._lock:
            self._enforcer.remove_filtered_policy(0, role)
            self._enforcer.remove_filtered_named_policy("p2", 0, role)
            self._save()


# Process-wide singleton. The policy files are static, so one enforcer serves
# every request; ``reload_policy()`` picks up edits at runtime.
_policy: Policy | None = None


def get_policy() -> Policy:
    global _policy
    if _policy is None:
        _policy = Policy()
    return _policy


def reload_policy() -> None:
    """Reload the policy files into the process-wide enforcer."""
    get_policy().reload()


def can(user: dict | None, resource: str, action: str) -> bool:
    return get_policy().can(user, resource, action)


def home_for(user: dict | None) -> str:
    return get_policy().home_for(user)


def roles() -> list[str]:
    return get_policy().roles()
