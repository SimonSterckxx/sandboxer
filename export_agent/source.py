import logging
from pathlib import Path
from typing import Any

from vaultspeed_sdk.exceptions.allowed_values import AllowedValuesException
from vaultspeed_sdk.exceptions.data_not_found import DataNotFound
from vaultspeed_sdk.exceptions.forbidden_action import ForbiddenActionException
from vaultspeed_sdk.exceptions.release_issue import ReleaseIssue
from vaultspeed_sdk.source.object import SourceObjectSplit

from .helpers import safe_get, sb, write_json

log = logging.getLogger(__name__)


def export_source(source: Any, proj_path: Path) -> dict:
    src_export_name = sb(source.name)
    src_path = proj_path / "sources" / src_export_name

    db_link = safe_get(source, "database_link")

    params = []
    for p in safe_get(source, "parameters", default=[]):
        try:
            params.append({"name": p.name, "value": safe_get(p, "value")})
        except AllowedValuesException as e:
            log.warning("Skipping source param '%s.%s': %s", source.name, safe_get(p, "name", default="?"), e)

    data = {
        "original_name": source.name,
        "original_short_name": safe_get(source, "short_name"),
        "original_bk_name": safe_get(source, "bk_name"),
        "original_record_name": safe_get(source, "record_name"),
        "name": src_export_name,
        "short_name": sb(safe_get(source, "short_name", default="")),
        "bk_name": sb(safe_get(source, "bk_name", default="")),
        "record_name": sb(safe_get(source, "record_name", default="")),
        "physical_schema": safe_get(source, "physical_schema"),
        "cdc_type": safe_get(source, "cdc_type"),
        "build_flag": safe_get(source, "build_flag", default=False),
        "database_link": db_link.name if db_link else None,
        "parameters": params,
        "object_exclusions": [
            {"pattern": safe_get(e, "pattern"), "reason": safe_get(e, "reason")}
            for e in safe_get(source, "object_exclusions", default=[])
        ],
        "attribute_exclusions": [
            {"pattern": safe_get(e, "pattern"), "reason": safe_get(e, "reason")}
            for e in safe_get(source, "attribute_exclusions", default=[])
        ],
        "name_removal_patterns": [
            {"pattern": safe_get(p, "pattern"), "reason": safe_get(p, "reason")}
            for p in safe_get(source, "name_removal_patterns", default=[])
        ],
    }

    write_json(src_path / "source.json", data)
    _export_source_releases(source, src_path)
    log.info("Exported source '%s' → '%s'.", source.name, src_export_name)
    return data


def _export_source_releases(source: Any, src_path: Path) -> None:
    releases = list(safe_get(source, "releases", default=[]))
    releases.sort(key=lambda r: float(safe_get(r, "number", default=0)))

    for rel in releases:
        rel_path = src_path / "releases" / str(safe_get(rel, "number", default="0"))
        try:
            data = _export_source_release(rel, rel_path)
            write_json(rel_path / "release.json", data)
        except ForbiddenActionException as e:
            log.warning("Cannot read release %s of source '%s': %s", safe_get(rel, "number"), source.name, e)


def _export_source_release(src_rel: Any, rel_path: Path) -> dict:
    prev = safe_get(src_rel, "prev_release_info")

    objects = {}
    for obj in safe_get(src_rel, "objects", default=[]):
        try:
            objects[obj.name] = _serialize_source_object(obj)
        except ReleaseIssue:
            check = safe_get(obj, "check_result")
            log.warning("ReleaseIssue on object '%s': %s", safe_get(obj, "name", default="?"), check)
            serialized = _serialize_source_object(obj)
            serialized["valid"] = False
            objects[safe_get(obj, "name", default="?")] = serialized

    hubs = {}
    for hub in safe_get(src_rel, "hubs", default=[]):
        hubs[hub.name] = {"hub_type": safe_get(hub, "hub_type")}

    sats = {}
    for sat in safe_get(src_rel, "sats", default=[]):
        splits = {}
        for split in safe_get(sat, "splits", default=[]):
            splits[split.name] = {
                "type": safe_get(split, "type"),
                "attributes": [a.name for a in safe_get(split, "attributes", default=[])],
            }
        sats[sat.name] = {"splits": splits}

    return {
        "number": safe_get(src_rel, "number"),
        "comment": safe_get(src_rel, "comment"),
        "saved": safe_get(src_rel, "saved"),
        "editable": safe_get(src_rel, "editable"),
        "locked": safe_get(src_rel, "locked"),
        "available_as_base": safe_get(src_rel, "available_as_base"),
        "prev_release": {
            "number": safe_get(prev, "number"),
            "comment": safe_get(prev, "comment"),
        } if prev else None,
        "objects": objects,
        "hubs": hubs,
        "sats": sats,
    }


def _serialize_source_object(obj: Any) -> dict:
    is_split = isinstance(obj, SourceObjectSplit)
    result = {
        "object_type": safe_get(obj, "object_type"),
        "cdc_type": safe_get(obj, "cdc_type"),
        "multi_active": safe_get(obj, "multi_active"),
        "is_split": is_split,
        "attributes": {
            attr.name: _serialize_source_attribute(attr)
            for attr in safe_get(obj, "attributes", default=[])
        },
        "relationships": _fetch_relationships(obj),
    }
    if is_split:
        result.update({
            "parent_table_identifier": safe_get(obj, "parent_table_identifier"),
            "auto_sync_constraints": safe_get(obj, "auto_sync_constraints"),
            "auto_sync_referencing_constraints": safe_get(obj, "auto_sync_referencing_constraints"),
            "auto_sync_attributes": safe_get(obj, "auto_sync_attributes"),
            "deduplicate_data_on_load": safe_get(obj, "deduplicate_data_on_load"),
        })
    return result


def _fetch_relationships(obj: Any) -> list:
    try:
        return [_serialize_relationship(r) for r in safe_get(obj, "relationships", default=[])]
    except DataNotFound as e:
        log.warning("No relationships found for object '%s': %s", safe_get(obj, "name", default="?"), e)
        return []


def _serialize_source_attribute(attr: Any) -> dict:
    return {
        "business_key": safe_get(attr, "business_key", default=False),
        "universal_identifier": safe_get(attr, "universal_identifier", default=False),
        "subsequence_attribute": safe_get(attr, "subsequence_attribute", default=False),
        "non_historic": safe_get(attr, "non_historic", default=False),
        "abbreviated_name": safe_get(attr, "abbreviated_name"),
        "primary_key": safe_get(attr, "primary_key", default=False),
        "data_type": safe_get(attr, "data_type"),
        "data_length": safe_get(attr, "data_length"),
    }


def _serialize_relationship(rel: Any) -> dict:
    attrs = list(safe_get(rel, "attributes", default=[]))
    return {
        "name": safe_get(rel, "name"),
        "driving_key": safe_get(rel, "driving_key", default=False),
        "attributes": [
            {
                "attribute_name": safe_get(a, "attribute_name"),
                "ref_attribute_name": safe_get(a, "ref_attribute_name"),
            }
            for a in attrs
        ],
    }
