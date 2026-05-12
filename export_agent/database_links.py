import logging
from typing import Any

from vaultspeed_sdk.database_link import DatabaseLinkTypes
from vaultspeed_sdk.system import System

from .helpers import safe_get

log = logging.getLogger(__name__)


def export_database_links(system: System) -> tuple[dict, dict[str, Any]]:
    links = []
    name_to_link: dict[str, Any] = {}

    for link in system.database_links:
        record = {
            "name": link.name,
            "link_type": safe_get(link, "link_type"),
            "database_type": safe_get(link, "database_type"),
            "url": None,
        }
        if safe_get(link, "link_type") == DatabaseLinkTypes.CLOUD:
            record["url"] = safe_get(link, "url")

        links.append(record)
        name_to_link[link.name] = link

    log.info("Exported %d database link(s).", len(links))
    return {"links": links}, name_to_link
