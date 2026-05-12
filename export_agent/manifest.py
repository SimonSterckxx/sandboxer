import datetime
from typing import Any


def build_manifest(
    project_name: str,
    project_export_name: str,
    sources_count: int,
    dvs_count: int,
    generations: list[dict],
    start_time: datetime.datetime,
) -> dict:
    return {
        "exported_at": start_time.isoformat(),
        "completed_at": datetime.datetime.utcnow().isoformat(),
        "project": {
            "original_name": project_name,
            "exported_name": project_export_name,
            "source_count": sources_count,
            "dv_count": dvs_count,
        },
        "counts": {
            "sources": sources_count,
            "data_vaults": dvs_count,
            "generations": len(generations),
        },
        "generations": generations,
    }
