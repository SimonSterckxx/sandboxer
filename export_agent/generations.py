import logging
from pathlib import Path
from typing import Any

from vaultspeed_sdk.exceptions.data_not_found import DataNotFound
from vaultspeed_sdk.exceptions.internal_server_error import InternalServerError
from vaultspeed_sdk.exceptions.task import TaskException
from vaultspeed_sdk.system import System

from .helpers import safe_get

log = logging.getLogger(__name__)


def export_generations(system: System, export_root: Path) -> list[dict]:
    summary = []

    try:
        all_gens = system.generations()
    except Exception as e:
        log.error("Could not retrieve generation list: %s", e)
        return summary

    for gen in all_gens:
        gen_type_str = safe_get(gen, "gen_type", "value") or str(safe_get(gen, "gen_type", default="UNKNOWN"))
        download_path = export_root / "generations" / gen_type_str

        try:
            gen.download_files_to(path=download_path, keep_zip=False)
        except TaskException as e:
            log.error("Failed to download generation '%s': %s", safe_get(gen, "filename"), e)
        except DataNotFound as e:
            log.warning("Generation files not found for '%s': %s", safe_get(gen, "filename"), e)
        except InternalServerError:
            log.debug("InternalServerError downloading generation '%s' — empty FMC flow, skipping.", safe_get(gen, "filename"))
        except Exception as e:
            log.error("Unexpected error downloading generation '%s': %s", safe_get(gen, "filename"), e)

        summary.append({
            "gen_type": gen_type_str,
            "filename": safe_get(gen, "filename"),
            "bv_identifier": safe_get(gen, "bv_identifier"),
            "can_autodeploy": safe_get(gen, "can_autodeploy"),
            "generation_time": safe_get(gen, "generation_time"),
        })

    log.info("Exported %d generation record(s).", len(summary))
    return summary
