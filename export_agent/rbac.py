import logging

from vaultspeed_sdk.exceptions.forbidden_action import ForbiddenActionException
from vaultspeed_sdk.system import System

from .helpers import safe_get

log = logging.getLogger(__name__)


def export_rbac(system: System) -> dict:
    try:
        users = []
        for user in system.get_users():
            users.append({
                "email": safe_get(user, "email"),
                "first_name": safe_get(user, "first_name"),
                "last_name": safe_get(user, "last_name"),
                "enabled": safe_get(user, "enabled", default=True),
                "roles": [r.name for r in safe_get(user, "roles", default=[])],
            })

        roles = []
        for role in safe_get(system, "roles", default=[]):
            privileges = []
            for p in safe_get(role, "privileges", default=[]):
                privileges.append({
                    "action": safe_get(p, "action", "enum") or safe_get(p, "action"),
                    "screen": safe_get(p, "screen", "enum") or safe_get(p, "screen"),
                })
            roles.append({
                "name": role.name,
                "code": safe_get(role, "code"),
                "description": safe_get(role, "description"),
                "privileges": privileges,
            })

        log.info("Exported %d user(s) and %d role(s).", len(users), len(roles))
        return {"users": users, "roles": roles}

    except ForbiddenActionException:
        log.warning("Insufficient privileges to export RBAC — skipping.")
        return {"skipped": True, "reason": "insufficient_privileges"}
