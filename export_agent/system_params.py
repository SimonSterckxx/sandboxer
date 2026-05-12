import datetime
import logging

from vaultspeed_sdk.exceptions.allowed_values import AllowedValuesException
from vaultspeed_sdk.system import System

from .helpers import safe_get

log = logging.getLogger(__name__)


def export_system_params(system: System) -> dict:
    params = []
    for p in system.parameters:
        try:
            params.append({
                "name": p.name,
                "value": safe_get(p, "value"),
                "type": safe_get(p, "type"),
                "description": safe_get(p, "description"),
            })
        except AllowedValuesException as e:
            log.warning("Skipping system parameter '%s': %s", safe_get(p, "name", default="?"), e)

    return {
        "exported_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "parameters": params,
    }
