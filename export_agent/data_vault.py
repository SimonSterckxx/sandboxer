import logging
from pathlib import Path
from typing import Any

from vaultspeed_sdk.exceptions.allowed_values import AllowedValuesException
from vaultspeed_sdk.exceptions.data_not_found import DataNotFound
from vaultspeed_sdk.exceptions.forbidden_action import ForbiddenActionException
from vaultspeed_sdk.exceptions.internal_server_error import InternalServerError

from .business_vault import export_bv_releases
from .helpers import safe_get, sb, write_json

log = logging.getLogger(__name__)


def export_data_vault(dv: Any, proj_path: Path) -> dict:
    dv_export_name = sb(dv.name)
    dv_path = proj_path / "data_vaults" / dv_export_name

    params = []
    for p in safe_get(dv, "parameters", default=[]):
        try:
            params.append({"name": p.name, "value": safe_get(p, "value")})
        except AllowedValuesException as e:
            log.warning("Skipping DV param '%s.%s': %s", dv.name, safe_get(p, "name", default="?"), e)

    fmc_flows = []
    for flow in safe_get(dv, "fmc_flows", default=[]):
        try:
            fmc_flows.append(_serialize_fmc_flow(flow))
        except InternalServerError:
            log.debug("InternalServerError reading FMC flow '%s' — likely empty, skipping.", safe_get(flow, "name"))

    data = {
        "original_name": dv.name,
        "original_code": safe_get(dv, "code"),
        "name": dv_export_name,
        "code": sb(safe_get(dv, "code", default="")),
        "database_type": safe_get(dv, "database_type"),
        "parameters": params,
        "fmc_flows": fmc_flows,
    }

    write_json(dv_path / "dv.json", data)
    _export_dv_releases(dv, dv_path)
    log.info("Exported DV '%s' → '%s'.", dv.name, dv_export_name)
    return data


def _serialize_fmc_flow(flow: Any) -> dict:
    name = safe_get(flow, "name", default="")
    description = safe_get(flow, "description", default="")
    return {
        "original_name": name,
        "original_description": description,
        "name": sb(name),
        "description": sb(description),
        "flow_type": safe_get(flow, "flow_type"),
        "load_type": safe_get(flow, "load_type"),
        "schedule_interval": safe_get(flow, "schedule_interval"),
        "concurrency": safe_get(flow, "concurrency"),
        "dv_connection_name": safe_get(flow, "dv_connection_name"),
        "src_connection_name": safe_get(flow, "src_connection_name"),
        "group_tasks": safe_get(flow, "group_tasks"),
        "start_date": safe_get(flow, "start_date"),
    }


def _export_dv_releases(dv: Any, dv_path: Path) -> None:
    releases = list(safe_get(dv, "releases", default=[]))
    releases.sort(key=lambda r: safe_get(r, "date") or "")

    for rel in releases:
        rel_name = safe_get(rel, "name", default="unknown")
        rel_path = dv_path / "releases" / rel_name
        try:
            data = _export_dv_release(rel, rel_path)
            write_json(rel_path / "release.json", data)
        except ForbiddenActionException as e:
            log.warning("Cannot read DV release '%s': %s", rel_name, e)
        except DataNotFound as e:
            log.warning("DV release '%s' not found: %s", rel_name, e)


def _export_dv_release(dv_rel: Any, rel_path: Path) -> dict:
    grouped_hubs = {}
    for group in safe_get(dv_rel, "grouped_hubs", default=[]):
        grouped_hubs[group.name] = _serialize_hub_group(group)

    ungrouped_hubs = [
        {"hub_name": hub.name}
        for hub in safe_get(dv_rel, "ungrouped_hubs", default=[])
    ]

    links = [{"name": l.name, "category": "standard"} for l in safe_get(dv_rel, "links", default=[])]
    links += [{"name": l.name, "category": "many_to_many"} for l in safe_get(dv_rel, "many_to_many_links", default=[])]
    links += [{"name": l.name, "category": "non_historical"} for l in safe_get(dv_rel, "non_historical_links", default=[])]

    data_types = {}
    for dt_name, dt in safe_get(dv_rel, "data_types", default={}).items():
        data_types[dt_name] = {
            "max_data_length": safe_get(dt, "max_data_length"),
            "null_value": safe_get(dt, "null_value"),
            "unknown_value": safe_get(dt, "unknown_value"),
        }

    data_type_mappings = {}
    for dm_name, dm in safe_get(dv_rel, "data_type_mappings", default={}).items():
        data_type_mappings[dm_name] = {
            "data_type_target": safe_get(dm, "data_type_target", "name"),
            "data_length_target": safe_get(dm, "data_length_target"),
        }

    special_values = {}
    for sv_name, sv in safe_get(dv_rel, "special_values", default={}).items():
        special_values[sv_name] = {
            "null_value": safe_get(sv, "null_value"),
            "unknown_value": safe_get(sv, "unknown_value"),
        }

    result = {
        "name": safe_get(dv_rel, "name"),
        "number": safe_get(dv_rel, "number"),
        "comment": safe_get(dv_rel, "comment"),
        "date": safe_get(dv_rel, "date"),
        "prototype_flag": safe_get(dv_rel, "prototype_flag"),
        "locked": safe_get(dv_rel, "locked"),
        "grouped_hubs": grouped_hubs,
        "ungrouped_hubs": ungrouped_hubs,
        "links": links,
        "data_types": data_types,
        "data_type_mappings": data_type_mappings,
        "special_values": special_values,
    }

    export_bv_releases(dv_rel, rel_path / "bv")
    return result


def _serialize_hub_group(group: Any) -> dict:
    elements = []
    for e in safe_get(group, "elements", default=[]):
        elements.append({
            "hub_name": safe_get(e, "hub_name"),
            "source_name": safe_get(e, "source_name"),
        })
    return {
        "abbreviated_name": safe_get(group, "abbreviated_name"),
        "short_name": safe_get(group, "short_name"),
        "business_key_concat": safe_get(group, "business_key_concat", default=False),
        "elements": elements,
    }
