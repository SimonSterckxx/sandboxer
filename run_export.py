import datetime
import logging
import os
import sys

from vaultspeed_sdk.client import UnauthorizedException
from vaultspeed_sdk.exceptions.data_not_found import DataNotFound
from vaultspeed_sdk.exceptions.forbidden_action import ForbiddenActionException

from export_agent.auth import authenticate
from export_agent.database_links import export_database_links
from export_agent.data_vault import export_data_vault
from export_agent.generations import export_generations
from export_agent.helpers import EXPORT_ROOT, sb, write_json
from export_agent.manifest import build_manifest
from export_agent.rbac import export_rbac
from export_agent.source import export_source
from export_agent.system_params import export_system_params

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("run_export")


def _export_project_metadata(project, name_to_link: dict) -> dict:
    db_link = None
    params = []
    for p in getattr(project, "parameters", []):
        params.append({"name": p.name, "value": getattr(p, "value", None)})

    return {
        "original_name": project.name,
        "name": sb(project.name),
        "description": getattr(project, "description", None),
        "parameters": params,
    }


def main() -> None:
    start_time = datetime.datetime.utcnow()

    # Authenticate
    try:
        _client, system = authenticate()
    except KeyError as e:
        log.error("Missing required environment variable: %s", e)
        sys.exit(1)
    except UnauthorizedException as e:
        log.error("Authentication failed: %s", e)
        sys.exit(1)

    # Resolve project
    project_name = os.environ.get("VS_PROJECT", "").strip()
    if not project_name:
        log.error("Missing required environment variable: VS_PROJECT")
        sys.exit(1)

    project = next((p for p in system.projects if p.name == project_name), None)
    if project is None:
        log.error("Project '%s' not found in the VaultSpeed instance.", project_name)
        sys.exit(1)

    log.info("Starting export of project '%s'.", project_name)

    # System-level exports
    write_json(EXPORT_ROOT / "system_params.json", export_system_params(system))

    db_links_payload, name_to_link = export_database_links(system)
    write_json(EXPORT_ROOT / "database_links.json", db_links_payload)

    # Project metadata
    proj_export_name = sb(project.name)
    proj_path = EXPORT_ROOT / "projects" / proj_export_name
    proj_data = _export_project_metadata(project, name_to_link)
    write_json(proj_path / "project.json", proj_data)

    # Sources
    sources_count = 0
    for source in getattr(project, "sources", []):
        try:
            export_source(source, proj_path)
            sources_count += 1
        except DataNotFound as e:
            log.warning("Source '%s' not found during export: %s", getattr(source, "name", "?"), e)
        except ForbiddenActionException as e:
            log.warning("Insufficient privilege for source '%s': %s", getattr(source, "name", "?"), e)

    # Data Vaults
    dvs_count = 0
    for dv in getattr(project, "data_vaults", []):
        try:
            export_data_vault(dv, proj_path)
            dvs_count += 1
        except DataNotFound as e:
            log.warning("DV '%s' not found during export: %s", getattr(dv, "name", "?"), e)
        except ForbiddenActionException as e:
            log.warning("Insufficient privilege for DV '%s': %s", getattr(dv, "name", "?"), e)

    # Code generations
    gen_summary = export_generations(system, EXPORT_ROOT)

    # RBAC
    write_json(EXPORT_ROOT / "rbac.json", export_rbac(system))

    # Manifest
    manifest = build_manifest(
        project_name=project.name,
        project_export_name=proj_export_name,
        sources_count=sources_count,
        dvs_count=dvs_count,
        generations=gen_summary,
        start_time=start_time,
    )
    write_json(EXPORT_ROOT / "manifest.json", manifest)

    log.info(
        "Export complete: %d source(s), %d DV(s), %d generation(s). Output: %s",
        sources_count,
        dvs_count,
        len(gen_summary),
        EXPORT_ROOT,
    )


if __name__ == "__main__":
    main()
