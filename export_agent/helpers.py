import datetime
import json
from enum import Enum
from pathlib import Path
from typing import Any

SUFFIX = "_sandbox"
EXPORT_ROOT = Path(__file__).parent.parent / "export"


def sb(name: str) -> str:
    if not name:
        return name
    return name if name.endswith(SUFFIX) else name + SUFFIX


def safe_get(obj: Any, *fields: str, default: Any = None) -> Any:
    current = obj
    for field in fields:
        current = getattr(current, field, None)
        if current is None:
            return default
    return current if current is not None else default


def default_serializer(obj: Any) -> Any:
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(data, indent=2, default=default_serializer),
        encoding="utf-8",
    )
