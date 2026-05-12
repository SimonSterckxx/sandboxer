import logging
from pathlib import Path
from typing import Any

from vaultspeed_sdk.business_vault.template_target_attribute import TemplateTargetExistingAttribute
from vaultspeed_sdk.exceptions.data_not_found import DataNotFound
from vaultspeed_sdk.exceptions.forbidden_action import ForbiddenActionException

from .helpers import safe_get, write_json

log = logging.getLogger(__name__)


def export_bv_releases(dv_rel: Any, bv_base_path: Path) -> None:
    for bv_rel in safe_get(dv_rel, "business_vault_releases", default=[]):
        bv_name = safe_get(bv_rel, "name", default="unknown")
        bv_path = bv_base_path / bv_name
        try:
            data = export_bv_release(bv_rel, bv_path)
            write_json(bv_path / "bv_release.json", data)
        except ForbiddenActionException as e:
            log.warning("Cannot read BV release '%s': %s", bv_name, e)
        except DataNotFound as e:
            log.warning("BV release '%s' not found: %s", bv_name, e)


def export_bv_release(bv_rel: Any, bv_path: Path) -> dict:
    business_views = {}
    for bv in safe_get(bv_rel, "business_views", default=[]):
        business_views[bv.name] = _serialize_business_view(bv)

    pits = {}
    for pit in safe_get(bv_rel, "pits", default=[]):
        pits[pit.name] = _serialize_pit(pit)

    bridges = {}
    for bridge in safe_get(bv_rel, "bridges", default=[]):
        bridges[bridge.name] = _serialize_bridge(bridge)

    templates = {}
    for tmpl in safe_get(bv_rel, "templates", default=[]):
        try:
            templates[tmpl.name] = _serialize_template(tmpl)
        except DataNotFound as e:
            log.warning("Skipping template '%s': %s", safe_get(tmpl, "name", default="?"), e)

    return {
        "name": safe_get(bv_rel, "name"),
        "comment": safe_get(bv_rel, "comment"),
        "locked": safe_get(bv_rel, "locked"),
        "business_views": business_views,
        "pits": pits,
        "bridges": bridges,
        "signatures": _serialize_signatures(bv_rel),
        "templates": templates,
    }


def _serialize_business_view(bv: Any) -> dict:
    attributes = {}
    for attr in safe_get(bv, "attributes", default=[]):
        attributes[attr.name] = {
            "business_name": safe_get(attr, "business_name"),
            "generate": safe_get(attr, "generate", default=True),
        }
    return {
        "business_name": safe_get(bv, "business_name"),
        "generate": safe_get(bv, "generate", default=True),
        "attributes": attributes,
    }


def _serialize_pit(pit: Any) -> dict:
    return {
        "snapshot_frequency": safe_get(pit, "snapshot_frequency"),
        "frequency_type": safe_get(pit, "frequency_type"),
        "pit_type": safe_get(pit, "pit_type"),
        "timestamp_type": safe_get(pit, "timestamp_type"),
        "dv_object_names": [o.name for o in safe_get(pit, "dv_objects", default=[])],
    }


def _serialize_bridge(bridge: Any) -> dict:
    return {
        "create_bridge_hk": safe_get(bridge, "create_bridge_hk"),
        "objects": [o.name for o in safe_get(bridge, "objects", default=[])],
        "objects_with_bks": [o.name for o in safe_get(bridge, "objects_with_bks", default=[])],
    }


def _serialize_signatures(bv_rel: Any) -> dict:
    layers = [
        {"name": sl.name, "order": safe_get(sl, "order")}
        for sl in safe_get(bv_rel, "signature_layers", default=[])
    ]
    objects = [
        {"name": so.name}
        for so in safe_get(bv_rel, "signature_objects", default=[])
    ]
    attributes = [
        {"name": sa.name}
        for sa in safe_get(bv_rel, "signature_attributes", default=[])
    ]
    return {"layers": layers, "objects": objects, "attributes": attributes}


def _serialize_template(template: Any) -> dict:
    dependencies = [
        {
            "name": safe_get(dep, "name"),
            "linked": safe_get(dep, "linked"),
        }
        for dep in safe_get(template, "dependencies", default=[])
    ]

    target_attributes = []
    for ta in safe_get(template, "target_attributes", default=[]):
        target_attributes.append({
            "name": safe_get(ta, "name"),
            "kind": "existing" if isinstance(ta, TemplateTargetExistingAttribute) else "custom",
            "attribute_type_name": safe_get(ta, "attribute_type", "name"),
        })

    return {
        "description": safe_get(template, "description"),
        "prefix": safe_get(template, "prefix"),
        "storage_type": safe_get(template, "storage_type"),
        "load_type": safe_get(template, "load_type"),
        "base_type": safe_get(template, "base_type"),
        "template_etl": safe_get(template, "template_etl"),
        "template_ddl": safe_get(template, "template_ddl"),
        "dependencies": dependencies,
        "target_attributes": target_attributes,
    }
